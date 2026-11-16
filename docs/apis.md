---
titulo: Catálogo de APIs de energía (verificado)
fecha: 2026-11-16
ambito: transversal
estado: revision
---

# APIs de energía: qué hay, qué pide clave y qué está roto

Todo lo de esta tabla se probó con una petición real el **16-11-2026**. Donde dice «verificado», hay
respuesta guardada; donde dice «roto», el error literal está anotado.

## 1. Red Eléctrica — `apidatos.ree.es` (sin clave)

Es el backend de la web REData. JSON:API, sin autenticación, CORS abierto.

| Qué | Endpoint | Estado |
|---|---|---|
| Generación por tecnología | `/es/datos/generacion/estructura-generacion` | **funciona** con `time_trunc=day` |
| Balance eléctrico | `/es/datos/balance/balance-electrico` | **funciona** con `day` |
| Demanda | `/es/datos/demanda/evolucion` | **funciona** con `day` |
| Demanda en tiempo real | `/es/datos/demanda/demanda-tiempo-real` | **roto**: 400 «no disponibles» |
| Cualquier `time_trunc=hour` | — | **roto**: 400 en todos los widgets |
| Por CCAA (`geo_limit=ccaa`) | — | **roto**: 500 |
| Intercambios | `/es/datos/intercambios/todas-fronteras-fisicos` | 400 en la prueba |
| Mercados / PVPC | `/es/datos/mercados/precios-mercados-tiempo-real` | 400 «no disponibles» |
| Calidad de servicio | `/es/datos/transporte/*` | 400 |

**Trampa del formato, y cuesta una hora:** los valores **no** están en `data.attributes.values`.
Ese objeto solo trae título y `last-update`. Las series vienen en la lista **`included[]`**, un objeto
por tecnología con sus `values[{value, percentage, datetime}]`.

```bash
curl "https://apidatos.ree.es/es/datos/generacion/estructura-generacion\
?start_date=2026-11-15T00:00&end_date=2026-11-15T23:59&time_trunc=day"
# → data.attributes: {title, last-update}   ← vacío de datos
# → included[12]: {title:"Eólica", values:[{value:311168.0,...}]}
```

**Conclusión:** la API pública sirve **agregados diarios nacionales**. Ni tiempo real, ni por planta,
ni por comunidad. Se usa en `scripts/ree_estado.py`.

## 2. Lo que sí da el detalle: hace falta clave gratuita

| API | Clave | Qué da que no da REE | Estado sin clave |
|---|---|---|---|
| **ESIOS** (`api.esios.ree.es`) | token gratis pidiéndolo a `consultasios@ree.es` | ~2.000 indicadores: precios, por central, restricciones, servicios de ajuste | **403 Forbidden** |
| **ENTSO-E Transparency** (`web-api.tp.entsoe.eu`) | token por formulario | **generación por unidad**, **previsión day-ahead por unidad y por tipo**, flujos, capacidad | **401** |
| **AEMET OpenData** | token gratis (registro) | observación y previsión horaria por estación: viento, radiación, temperatura | 401 sin clave |
| **Renewables.ninja** | token | simulación de producción eólica/solar por punto | — |

**La respuesta corta a «¿podemos saber cuánto se produce en cada sitio?»:** con la API pública **no**.
Con **ENTSO-E** sí, por unidad de generación (`Actual Generation per Generation Unit`). Con **ESIOS**,
por central, según el indicador.

**Y «¿cuánto está previsto?»**: apidatos no tiene previsión. ENTSO-E sí: *Day-ahead Generation
Forecast* por tipo y por unidad, y *Day-ahead Load Forecast*.

## 3. «¿Hay API para la tensión?»

**No hay ninguna API pública de tensión por nudo o por subestación.** Ni REE la publica, ni ESIOS la
sirve como serie georreferenciada. Lo que existe:

- `transporte/*` en apidatos: **calidad de servicio** (ENS, tiempo de interrupción, km de línea,
  índice de disponibilidad). Es fiabilidad, no tensión.
- La tensión en kV **por línea** sí la tenemos, pero como atributo estático del dato de OSM
  (`voltage=400000`), no como medida en vivo.
- Los valores de tensión que REE enseña en su sala de control están en la web, sin endpoint.

Si necesitas tensión real por nudo, no hay atajo: se pide a REE o se mide.

## 4. Sin clave y útiles de verdad

| API | Qué da | Verificado |
|---|---|---|
| **Open-Meteo Flood** | caudal de río modelado (GloFAS), pasado y pronóstico | sí, en uso |
| **Open-Meteo Forecast** | viento a 100 m, radiación, temperatura por punto | sí |
| **PVGIS** (JRC) | producción solar estimada por coordenada y orientación | sí |
| **OMIE** | precios del mercado diario e intradiario (ficheros) | sí |
| **Energy-Charts** (`api.energy-charts.info`) | generación y precios por país europeo | sí |
| **GIE AGSI+** | almacenamiento de gas europeo por instalación | sí |
| **datos.gob.es** | catálogo CKAN: miles de datasets, muchos con API | sí |
| **OpenStreetMap / Overpass** | infraestructura georreferenciada | sí, en uso |


## 6. ESIOS con token — lo que sí da (probado)

Con token personal (guardado en `.env`, **nunca en el repo**), `api.esios.ree.es` responde y el
catálogo tiene **1.982 indicadores**. Lo que sale:

| Pregunta | Respuesta | Indicador |
|---|---|---|
| ¿Hay previsión? | **sí**, demanda y eólica peninsulares | **460** (diaria), **541** (eólica) |
| ¿Hay generación por central? | **no**; solo «demanda en barras de central» | 1192 |
| ¿Hay tensión de red en kV? | **no**. Los «niveles de tensión» son **tarifarios** (E0, E1, E2… peajes) | 1200-1205 |
| ¿Hay caudal o aforo? | **no** | — |

La consulta usa la cabecera `x-api-key` y devuelve cuartos de hora:

```bash
curl -H "x-api-key: $ESIOS_TOKEN"   "https://api.esios.ree.es/indicators/460?start_date=2026-11-15T00:00&end_date=2026-11-16T23:59"
```

**Conclusión:** ESIOS resuelve la previsión (`scripts/esios_prevision.py`). Para **por planta** sigue
haciendo falta ENTSO-E. Para **tensión por nudo no hay nada**, ni con token.

## 7. Renfe GTFS-Realtime — trenes en vivo, sin clave

Tres feeds abiertos en `https://gtfsrt.renfe.com/`:

| Fichero | Contenido | Medido |
|---|---|---|
| `vehicle_positions.pb` | posición de cada tren | **418 trenes** |
| `trip_updates.pb` | retrasos y cambios de hora | 30 KB |
| `alerts.pb` | incidencias de servicio | **98 alertas** |

Formato **GTFS-Realtime** (Protocol Buffers), no JSON. Se lee con `gtfs-realtime-bindings`:

```python
from google.transit import gtfs_realtime_pb2 as pb
feed = pb.FeedMessage(); feed.ParseFromString(open("vehicle_positions.pb","rb").read())
```

Dos trampas medidas: **`route_id` viene vacío** (la ruta está en la etiqueta, `C1-23551` → `C1`), y las
alertas tienen `header_text` vacío aunque `description_text` sí trae el aviso.

`scripts/trenes.py` descarga los tres y genera `datos/trenes.geojson`. Es una **instantánea**: el feed
cambia cada minuto y el visor no se refresca solo.

## 8. IDEE — el catálogo de todo lo geográfico de España

**<https://www.idee.es>** es la Infraestructura de Datos Espaciales de España (CNIG). No es una API de
datos: es un **catálogo de metadatos** con un CSW (Catalogue Service for the Web) y el registro de
servicios INSPIRE.

| Qué ofrece | Cómo |
|---|---|
| Catálogo CSW de fichas de datos | `https://www.idee.es/csw-codsi-idee/srv/spa/csw` (GetCapabilities responde) |
| Servicios WMS/WMTS/WFS por tema | enlazados desde cada ficha |
| Teselas de cartografía base | **son las del IGN que ya usa el visor** (`ign.es/wmts/ign-base`) |
| Visor IDEE | para descubrir capas a mano |

Lo que aporta de verdad a Prometeo: **es el índice** para encontrar la capa oficial de cualquier cosa
(hidrografía, riesgo, ocupación del suelo, límites) y saber qué organismo la publica. El CSW exige un
`GetRecords` con XML bien formado; en la prueba devolvió respuesta vacía con un filtro `AnyText`, así
que la vía práctica es el visor y las fichas, no automatizar el CSW.

## 9. AEMET — requiere clave, sin ella no hay avisos

`opendata.aemet.es` devuelve **404 HTML** en todos los endpoints sin token, incluido
`avisos_cap/ultimoelaborado/espana`. El alta es gratuita (registro con email) y da una clave por
usuario. Sin ella, las alertas meteorológicas no se pueden automatizar: habría que leer el HTML de
avisos, y eso sí se rompe solo.

Pedirla es el paso pendiente para tener **alertas AEMET** en el mapa.


## 10. NAP de transporte y data.renfe.com

**NAP** (`nap.transportes.gob.es`) es el punto de acceso nacional de datos de transporte: GTFS,
DATEX II, aparcamientos, bicicleta pública. **Su API exige clave**: el catálogo CKAN responde
literalmente `Api Key was not provided` (401). Se pide por registro en el propio portal.

**data.renfe.com sí es abierto** y es CKAN puro, sin clave:

```bash
curl "https://data.renfe.com/api/3/action/package_list"
curl "https://data.renfe.com/api/3/action/package_show?id=estaciones-cercanias-madrid"
```

Publica un paquete `estaciones-cercanias-<núcleo>` por núcleo, cada uno con un CSV de lat/lon.
`scripts/estaciones_cercanias.py` los unifica:

| Núcleo | Estaciones |
|---|---:|
| Madrid | 93 |
| Valencia | 66 |
| Bilbao | 44 |
| Asturias | 43 |
| Sevilla | 33 |
| San Sebastián | 30 |
| Santander | 27 |
| Murcia-Alicante | 26 |
| Málaga | 23 |
| Cádiz | 14 |
| Zaragoza | 6 |
| **Total** | **405** |

Trampas medidas: el separador del CSV cambia (`;` o `,`) según el fichero, y los paquetes usan
`utf-8-sig` (con BOM). Sin eso, la primera columna se llama `﻿Nombre` y no encuentra el campo.

**Sobre «sin sobrecargar la web»:** las 405 estaciones se descargan en 90 KB y solo al encender la
capa. Con `zoomMin: 8` tampoco se dibujan a escala nacional.


## 11. Riesgo y emergencias (verificado)

| Fuente | Qué da | Clave | Estado |
|---|---|---|---|
| **EMSC-CSEM** (`seismicportal.eu/fdsnws`) | terremotos con magnitud, profundidad y región | **no** | **funciona**: 80 sismos en 7 días |
| **NASA FIRMS** | focos de calor por satélite (CSV) | no (público) | responde, hoy sin focos (noviembre) |
| **GDACS** | alertas de catástrofes | no | feed público |
| **EFFIS** | áreas quemadas | no | servicio europeo |
| **AEMET** | avisos meteorológicos CAP | **sí** | 404 sin token |

`scripts/sismos.py` usa EMSC con un bbox que cubre Península, Baleares y Canarias:

```bash
curl "https://www.seismicportal.eu/fdsnws/event/1/query?format=json&limit=600&minlatitude=27&maxlatitude=44.5&minlongitude=-19.5&maxlongitude=5&starttime=2026-11-09"
```

Detalle del dato: `profundidad = -1` significa **superficie o desconocida**, no «un km por encima».

## 12. SCNE — la atribución que faltaba

**<https://www.scne.es>** es el Sistema Cartográfico Nacional (Ley 14/2010): el marco que coordina
IGN, CNIG, IDEE y las CCAA. No es una API: es la **fuente de la fuente**.

Importa por un detalle legal: buena parte de lo que sirve el Atlas Estratégico (red eléctrica,
subestaciones) es **obra derivada de la BTN Continua del IGN**, y su atribución correcta es
`CC-BY 4.0 scne.es`. Citarlo bien no es cortesía, es la licencia.

Productos suyos que nos tocan: **CartoCiudad** (callejero), **IGR-RT** (red de transporte) y la
toponimia oficial normalizada.

## 13. Radar España — el mapa de fuentes que ya funciona

**<https://xn--radarespaa-19a.es>** es un proyecto ciudadano que reúne transporte y emergencias en
tiempo real. No es fuente, es **índice**: su pie de página enumera exactamente qué se puede usar hoy.

Fuentes que confirma y que merecen una visita:

| Fuente | Qué aporta |
|---|---|
| **TMB** (Transports Metropolitans de Barcelona) | posiciones de metro y bus |
| **CRTM** (Madrid) | metro y bus de la Comunidad |
| **TRAM Barcelona** | tranvía |
| **AUVASA** (Valladolid) | bus urbano |
| **EMT Málaga**, **ALSA**, **Ouigo** | bus y tren (Ouigo solo horarios) |
| **DGT** | incidencias de tráfico y obras |
| **Adif** | red ferroviaria (aunque **no publica estado ni incidencias** en formato reutilizable) |
| **Protección Civil / 112 / CCAA** | cortes de luz y planes de emergencia activados |

Su propio aviso es la lección: **Adif no publica en formato reutilizable** el estado de la red ni las
circulaciones de mercancías, e **Iryo no publica posición ni retrasos**. Lo que existe se declara, y
lo que no, también.

## 14. Qué pediría primero, por orden de valor

1. **ENTSO-E** — sigue siendo el único que da generación y previsión **por unidad**. 10 minutos.
2. **AEMET** — el único bloqueo que queda para alertas meteorológicas. Registro gratuito.
3. **IDEE** — no necesita clave: es para descubrir qué capa oficial existe antes de inventarla.

Los tres son gratuitos. Ninguno se pide con tarjeta.
