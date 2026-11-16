# OpenInfraES — infraestructura eléctrica de España, en datos

Repositorio de datos y visor de la **red de transporte eléctrica y del parque de generación español**,
construido con fuentes abiertas y listo para reutilizar en otros proyectos (mapas, modelos, análisis
territorial).

> Hecho con ❤️ por David Antizar · datos © colaboradores de OpenStreetMap (ODbL) y REE/ELECTRA

## Qué hay dentro

| Fichero | Contenido |
|---|---|
| `datos/lineas_hv.geojson` | **4.929 tramos** de línea de 220 y 400 kV (geometría completa) |
| `datos/plantas.geojson` | **5.797 instalaciones** de generación ≥ 0,5 MW con coordenadas y tecnología |
| `datos/agregado_lineas.csv` | km y tramos por tensión y tipo (aérea / subterránea / submarina) |
| `datos/agregado_lineas_operador.csv` | tramos y km por operador declarado |
| `datos/agregado_plantas_tecnologia.csv` | plantas y MW por tecnología |
| `datos/agregado_plantas_ccaa.csv` | plantas y MW por comunidad autónoma |
| `datos/agregado_plantas_ccaa_tecnologia.csv` | el cruce de los dos anteriores |
| `mapa.html` | visor propio con cartografía **IGN** y capas conmutables |
| `datos/gasoductos.geojson` | **678 tramos** de gasoducto (`man_made=pipeline`, `substance=gas`) |
| `datos/desaladoras.geojson` | plantas desaladoras (`desalination=yes`) |
| `datos/presas.geojson` | **4.464** presas y azudes (`waterway=dam`) |
| `datos/conteos_osm_20261116.json` | foto completa de OSM en España (líneas, subestaciones, plantas) con fecha y endpoint |

## Cartografía: IGN, no Leaflet

El visor usa **Leaflet** como motor (es la librería que dibuja capas y popups) pero la cartografía de
fondo es siempre del **IGN**, servida por su **WMTS público**, sin clave ni registro:

```
https://www.ign.es/wmts/ign-base?request=GetTile&service=WMTS&version=1.0.0
  &layer=IGNBaseTodo&style=default&tilematrixset=GoogleMapsCompatible
  &tilematrix={z}&tilerow={y}&tilecol={x}&format=image/png
```

Capas disponibles en el selector:

| Capa | Qué es |
|---|---|
| `IGNBaseTodo` | mapa base oficial (por defecto) |
| `IGNBase-gris` | mapa base en gris, para que los datos resalten |
| `IGNBaseOrto` | ortofoto PNOA |
| `IGNBaseTodo-nofondo` | solo topónimos y límites |
| OSM | alternativa colaborativa |

**Pitfall medido:** el WMTS del IGN devuelve **HTTP 200 con cuerpo vacío** si la petición no lleva
`Accept: image/*` y `Referer`. Con `curl` "pelado" parece roto y no lo está; desde el navegador
funciona siempre.

## Capas del visor

| Capa | Fuente | Elementos |
|---|---|---|
| 400 kV / 220 kV | OSM normalizado | 1.752 + 3.176 tramos |
| Centrales hidráulicas | REE/ELECTRA (hidro y bombeo) | 1.387 |
| Generación de gas (CCGT/fuel) | REE/ELECTRA | 49 |
| Resto del parque | REE/ELECTRA | resto |
| Gasoductos | OSM | 678 |
| Desaladoras | OSM | pendiente: el tag `desalination=yes` no se usa en España (0 resultados); en curso por nombre |
| Presas y embalses | OSM | 4.464 |

## Capas del Atlas Estratégico (verificadas, CC-BY-4.0)

Fuente: **Atlas Estratégico de España** (El Tercer Viejo, <https://atlas.eltercioviejo.com>), release
**2026.11.183**, archivo documental en <https://github.com/ArturoVazquez/atlas-archivo>. Cada capa
declara versión, fecha de verificación y fuentes. Descarga: `scripts/atlas.py`.

| Capa | Elementos | Verificado a |
|---|---:|---|
| `red-electrica` | 659 | 2026-08-07 |
| `agua-embalsada` | 402 | 2026-11-10 |
| `desaladoras` | **28** | 2026-08-31 |
| `refinerias` | 10 | 2026-08-09 |
| `nuclear` | 7 | 2026-09-22 |
| `gas-regasificacion` | 7 | 2026-09-22 |
| `hidrogeno-produccion` | 7 | 2026-09-22 |
| `gas-interconexiones` | 6 | — |
| `gas-almacenamiento` | 5 | — |
| `electricidad-interconexiones` | 5 | 2026-08-06 |
| `conducciones-combustible` | 2 | 2026-08-13 |

Capas descargables pero **no versionadas** (peso): `parques-eolicos` (1.382), `plantas-solares` (1.330),
`generacion-electrica-provincia` (52), `almacenamiento-petrolifero` (133),
`residuos-radiactivos` (14), `hidrogeno-red` (10). Están en `.gitignore` y se bajan con
`python scripts/atlas.py`.

**Por qué manda el Atlas en desaladoras:** OSM devuelve 40 con nombres genéricos y duplicados; el Atlas
da **28 con nombre, municipio y estado de verificación**. Aquí se usa el Atlas y OSM queda como
respaldo geográfico.

**Atribución:** obra derivada de NGBE Continua (CC-BY 4.0, ign.es), ABAQUA/Govern de les Illes Balears,
BOE y boletines autonómicos.

## La foto completa de OSM (16-11-2026)

Consulta directa a Overpass (`area ISO3166-1=ES`), con backoff porque el servicio estaba saturado:

| Objeto OSM | Elementos | Desglose |
|---|---:|---|
| `power=line` (todas las tensiones) | **24.578** | 24.578 ways |
| `power=substation` | **12.649** | 1.089 nodos + 11.479 ways + 81 relaciones |
| `power=plant` | **5.297** | 3.881 ways + 1.416 relaciones |

Contraste útil: el dataset normalizado trae **5.797 plantas** frente a las **5.297** de OSM puro — la
diferencia es el cruce con el registro administrativo ELECTRA/RAIPEE. Y de las 24.578 líneas de OSM,
solo **4.929** son de 220/400 kV: el resto es distribución, que este repositorio no cubre.

Referencia externa: OSM Wiki *Power networks/Spain* da **130.765 km** de líneas mapeadas y **104.108 MW**
(OpenInfraMap, agosto 2026), con 45.804 km de circuito de REE en 132/220/400 kV.

## Las cifras

**Red de transporte** (4.929 tramos, longitud calculada sobre la geometría):

| Tensión | Tipo | Tramos | km |
|---|---|---:|---:|
| 400 kV | aérea | 1.729 | 15.236 |
| 400 kV | submarina | 7 | 590 |
| 400 kV | subterránea | 16 | 23 |
| 220 kV | aérea | 3.058 | 15.855 |
| 220 kV | submarina | 20 | 703 |
| 220 kV | subterránea | 98 | 127 |
| **Total** | | **4.929** | **32.537** |

**Generación** (5.797 plantas, **126.327 MW**):

| Tecnología | Plantas | MW |
|---|---:|---:|
| Eólica | 1.144 | 31.325 |
| Solar FV | 2.292 | 27.171 |
| Ciclo combinado | 29 | 24.562 |
| Hidráulica | 1.378 | 16.757 |
| Cogeneración | 859 | 7.164 |
| Nuclear | 5 | 7.117 |
| Fuel-gas | 20 | 4.337 |
| Bombeo | 9 | 3.425 |
| Solar térmica | 51 | 2.302 |
| Carbón | 3 | 1.820 |
| Otras | 7 | 345 |

**Por comunidad**: Andalucía 19.917 MW · Castilla y León 15.013 · Castilla-La Mancha 14.385 ·
Extremadura 12.018 · Aragón 11.916 · Cataluña 11.810 · Galicia 9.592 · C. Valenciana 8.154.

## Cómo se regenera

```bash
python scripts/descargar.py     # baja los GeoJSON de la fuente (con fecha en el nombre)
python scripts/agregar.py       # agrega y VERIFICA los conteos de la fuente
python scripts/validar.py       # arnés del repo: ficheros, cabeceras, cuadres
```

`agregar.py` **falla** si los conteos no cuadran con los declarados por la fuente
(4.929 / 1.752 de 400 kV / 3.176 de 220 kV / 5.797 plantas). No genera CSV a medias.

## Ver el mapa

```bash
python -m http.server 8000   # y abrir http://localhost:8000/mapa.html
```

(El mapa carga los GeoJSON por `fetch`, así que necesita servidor local: `file://` no vale.)

## Calidad del dato: lo que hay que saber antes de usarlo

1. **La mitad de los tramos no declara operador** (2.431 de 4.929). Los que sí: Red Eléctrica
   2.437 tramos / 25.182 km. El resto de nombres son ruido de OSM (plantas, Adif, RTE francés).
2. **Longitud física ≠ longitud de circuito.** Aquí se mide la línea una vez, aunque tenga dos
   circuitos. REE publica km de **circuito** (45.804 km en 132/220/400 kV, dato 2025): no son
   comparables directamente.
3. **Solo transporte.** 220 y 400 kV. La distribución (132 kV y menos) es la mayor parte del km real
   del país y aquí no está.
4. **Haversine sobre WGS84**: error despreciable a esta escala, pero no es una medición topográfica.
5. **Las plantas vienen de dos registros cruzados** (REE ArcGIS y ELECTRA/RAIPEE), con un 47% de
   coincidencia por nombre según la fuente. La capacidad puede diferir de la administrativa.
6. **Cobertura irregular**: excelente en 400 kV, buena en 220 kV, incompleta en nudos menores.

## Fuentes y atribución

- **OpenStreetMap** (vía el dataset normalizado `ningunaparte/spain-power-plants`, ODbL): geometrías de
  línea y subestaciones, `osm_id` conservado para trazar cada tramo hasta el objeto original.
- **Red Eléctrica de España** (ArcGIS FeatureServer) y **ELECTRA/RAIPEE (MITECO)**: parque de generación.
- **OpenInfraMap** (<https://openinframap.org>): visualización de referencia del mismo dato OSM.
- Estadísticas de contraste: OSM Wiki *Power networks/Spain* (130.765 km de líneas totales mapeadas,
  104.108 MW de generación según OpenInfraMap, agosto 2026).

**Licencia de los datos derivados: ODbL 1.0** (herencia de OSM). Si se publica un mapa o un producto,
hay que atribuir a OpenStreetMap y compartir igual.

## Para qué se hizo

- Base para Prometeo (`Ntizar/Prometeo`): la red de transporte como eje del análisis energético.
- Punto de partida de mapas propios sin depender de servicios externos.
- Datos listos para cruzar con generación renovable, nudos de evacuación y planes de desarrollo.

## Estado

Primera extracción: **16-11-2026**. La fuente se actualiza periódicamente; el nombre de los ficheros
lleva la fecha del extracto. Overpass API (la vía directa a OSM) estaba saturada durante la creación
de este repositorio — el pipeline alternativo está en `scripts/descargar.py`.
