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

## 5. Qué pediría primero, por orden de valor

1. **ENTSO-E** — es el único que da generación y previsión **por unidad**. Token por formulario, 10 min.
2. **ESIOS** — precios y servicios de ajuste con el detalle que no da apidatos. Un correo.
3. **AEMET** — para cruzar previsión meteorológica con producción renovable.

Los tres son gratuitos. Ninguno se pide con tarjeta.
