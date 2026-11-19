# Project brief: OpenInfraES

Generado 2026-11-19 desde el árbol de trabajo (`a998d25`). Público: dev nuevo / quien audite el repo.
Alcance: el producto (visor) y el pipeline de datos. Fuera: el detalle de cada fuente oficial (está en
`docs/FUENTES.md`) y el histórico de auditorías (`docs/AUDITORIA.md`).

## Resumen

OpenInfraES es una **base de datos de infraestructura española y el mapa que la indexa**. No hay
backend: un repositorio con `datos/` (GeoJSON, CSV y agregados), 39 scripts de Python que descargan de
los organismos y escriben cada dato con su recibo de procedencia, un `index.html` de 2.588 líneas que
pinta 53 capas bajo demanda con Leaflet sobre cartografía del IGN, y GitHub Pages que publica el
resultado en cada push a `main`. El valor no está en el mapa: está en que cada capa declara organismo,
fecha de dato, fecha de descarga y licencia, y en que un arnés (`validar.py` + `cifras.py`) impide
publicar un dato que no cuadre.

Medidas de hoy: 189 ficheros versionados · 275 MB · 73 GeoJSON · 30 recibos · 53 capas en el visor ·
74 entradas en el catálogo · 9 grupos temáticos · 39 scripts.

## Supuestos y preguntas abiertas

- **Supuesto:** el navegador sólo consume `datos/` estático; las descargas de los organismos las hacen
  los scripts en local o en el workflow, no el visitante. Base: `refresco.yml` ejecuta `scripts/*.py` y
  commitea `datos/`; el visor sólo hace `fetch` de rutas relativas (`index.html:1849`).
- **Abierto:** `ign` se consume en vivo (WMTS público, sin clave) pero no hay script que descargue
  teselas: es dependencia en tiempo de lectura, no de build.
- **Abierto:** ¿`docs/` se publica en Pages o es sólo documentación del repo? No hay enlace desde el
  visor a `docs/`.

## Vocabulario

| Término | Significado |
|---|---|
| capa | Una entrada del array `CAPAS` del visor; 53 hoy, agrupadas en 9 grupos |
| recibo | `datos/<capa>_recibo.json`: features, vértices antes/después, fecha de descarga |
| catálogo | `datos/catalogo.json`: 74 entradas con licencia como objeto (`si`/`no`/`pendiente`) |
| procedencia | `datos/fuentes.json`: por capa, organismo, editor, licencia, fechas, URL, método |
| cadena | productor → publica → descarga, con tres fechas separadas (`cadenas.py`) |
| gate | Puerta que impide publicar: `validar.py` (cuadres) y `cifras.py --check` (tabla del README) |

## Actores (C4 nivel 1)

| id | Nombre | Qué hace con el sistema | Evidencia |
|---|---|---|---|
| lector | Lector del mapa | Enciende capas, busca, abre fichas, enlaza una vista | `index.html:925` (CAPAS), `index.html:1502` (ficha) |

## Sistemas externos (C4 nivel 1)

| id | Nombre | Por qué habla con él | Dirección | Evidencia |
|---|---|---|---|---|
| osm | OpenStreetMap (Overpass) | Red 220/400 kV, agua, transporte comunitario (ODbL) | entrada | `scripts/descargar.py`, `scripts/osm_agua.py` |
| ign | IGN · WMTS | Cartografía base del mapa, sin clave | entrada | `README.md:155-160` |
| miteco | MITECO | Embalses, plantas, residuos, demarcaciones | entrada | `scripts/irewater.py`, `datos/fuentes.json` |
| energia | REE · ESIOS · ENTSO-E · OMIE | Demanda, mix, precio, previsión | entrada | `scripts/ree_vivo.py`, `scripts/entsoe.py`, `scripts/omie.py` |
| transporte | MITMA · NAP · Renfe/Adif · DGT | Carreteras, puertos, trenes, cámaras y paneles | entrada | `scripts/hermes.py`, `scripts/nap.py`, `scripts/gtfsrt.py`, `scripts/dgt_rt.py` |
| riesgo | CSN · EMSC · AEMET | Sismos y avisos meteorológicos | entrada | `scripts/sismos.py`, `scripts/aemet_geo.py` |
| github | GitHub · Pages y Actions | Publica el sitio y ejecuta el refresco | salida | `.github/workflows/refresco.yml` |

## Contenedores (C4 nivel 2)

| id | Nombre | Tipo | Tecnología | Responsabilidad | Evidencia |
|---|---|---|---|---|---|
| visor | Visor del mapa | app estática | HTML+JS, Leaflet, IGN WMTS | Pinta 53 capas bajo demanda, fichas, leyenda, buscador, API de consola | `index.html` |
| conectores | Conectores | jobs batch | Python 3.12 (stdlib + requests) | Un script por organismo: descarga, normaliza, escribe `datos/` y su recibo | `scripts/*.py` (39) |
| almacen | Datos | store | GeoJSON, CSV, JSON | 73 GeoJSON, 30 recibos, `fuentes.json`, `catalogo.json`, series vivas | `datos/` |
| gates | Arnés de datos | CI | Python + GitHub Actions | Valida cuadres y cifras; bloquea la publicación | `scripts/validar.py`, `scripts/cifras.py`, `.github/workflows/` |

## Componentes (C4 nivel 3)

### visor
| id | Nombre | Responsabilidad | Evidencia |
|---|---|---|---|
| cfg-capas | CAPAS (declaración) | Las 53 capas: grupo, fichero, estilo, `zoomMin`, filtros | `index.html:925` |
| motor-capas | Motor de capas | `ponerCapa()`: un solo camino para checkbox, vistas, enlace y API; `cargar()` hace un `fetch` por sesión | `index.html:1922`, `index.html:1804` |
| render | Render del mapa | `pintarPuntos()` y `L.geoJSON`, con atenuación por `zoomMin` | `index.html:1736`, `index.html:1883` |
| ficha | Ficha del elemento | Métricas destacadas, atributos humanizados, procedencia, «qué hay a 30 km» | `index.html:1638`, `index.html:1502` |
| leyenda | Leyenda | Rampas de color y tamaño por capa | `index.html:1314` |
| procedencia-ui | Panel de fuentes | Tabla de procedencia y catálogo dentro del visor | `index.html:2080`, `index.html:2151` |
| api-visual | API de consola | `window.OpenInfraES`: abrir, estados, bench | `index.html:2457` |
| ciclo-capa | Ciclo de una capa | Máquina de estados de carga de una capa | `index.html:1912`, `index.html:1927` |

### conectores
| id | Nombre | Responsabilidad | Evidencia |
|---|---|---|---|
| conectores-fuente | Conectores por fuente | Descarga y normaliza cada organismo | `scripts/descargar.py`, `scripts/hermes.py`, `scripts/entsoe.py` |
| normaliza | normaliza.py | Provincia y CCAA **por código oficial**, nunca por nombre | `scripts/normaliza.py` |
| simplificar | simplificar.py | Douglas-Peucker con recibo de vértices antes/después | `scripts/simplificar.py` |
| agregados | agregar.py | CSV reutilizables por tensión, tecnología y CCAA | `scripts/agregar.py` |
| procedencia | Procedencia y catálogo | Escribe `fuentes.json`, `catalogo.json` y las cadenas | `scripts/fuentes_visor.py`, `scripts/catalogo.py`, `scripts/cadenas.py` |
| snapshot | snapshot.py | Archiva una foto diaria de los datos vivos | `scripts/snapshot.py` |

### gates
| id | Nombre | Responsabilidad | Evidencia |
|---|---|---|---|
| validador | validar.py | Recibos, conteos declarados y fuentes presentes | `scripts/validar.py:35` |
| cifras | cifras.py | Reescribe y comprueba la tabla de capas del README | `scripts/cifras.py:168` |
| workflows | GitHub Actions | Refresco cada 30 min y validación en cada push | `.github/workflows/refresco.yml`, `.github/workflows/validar.yml` |

## Relaciones

| Desde | Hacia | Qué transporta | Protocolo | Evidencia |
|---|---|---|---|---|
| lector | visor | abre el mapa | navegador | `index.html` |
| conectores | osm / miteco / energia / transporte / riesgo | descarga del organismo | HTTPS, CSV/JSON/GeoJSON/ArcGIS REST | `scripts/*.py` |
| conectores | almacen | GeoJSON, CSV, recibos, series | ficheros | `datos/` |
| almacen | visor | capas y metadatos | `fetch` relativo, una vez por sesión | `index.html:1849`, `index.html:2080` |
| visor | ign | teselas de fondo | WMTS público | `README.md:155-160` |
| gates | almacen | lee recibos y conteos | ficheros | `scripts/validar.py:35` |
| workflows | conectores | ejecuta las capas vivas | `python scripts/*.py` | `.github/workflows/refresco.yml` |
| workflows | github | commit y push del refresco | git | `.github/workflows/refresco.yml` |
| github | visor | sirve `index.html` y `datos/` | HTTPS estático | `README.md:3` |

## Modelo de datos

- `datos/<capa>.geojson` (73): features con `properties` normalizadas; `datos/simplificado/` (18 MB)
  para las geometrías que pesan, `datos/oficial/` (26 MB) para las que vienen ya vectorizadas.
- `datos/<capa>_recibo.json` (30): `features`, `vertices`, `vertices_origen`, `descargado`, tolerancia.
- `datos/fuentes.json` (74 capas): `fuente`, `editor`, `licencia`, `actualizado`, `descargado`,
  `features`, `url`, `metodo`.
- `datos/catalogo.json` (74): licencia como objeto con `estado`, resumen por jerarquía y `kb_total`.
- CSV agregados: tensión, operador, tecnología, CCAA.

## Máquinas de estado

Carga de una capa en el visor: `apagada -> cargando -> cargada | fallo -> (reintento) cargando`.
`fallo` marca `__cargada = false` para poder reintentar al volver a encenderla (`index.html:1912`).

## Flujos clave

### Encender una capa
Disparador: clic en el checkbox, una vista temática, un enlace permanente o la API.
1. lector marca la capa; el control llama a `ponerCapa(id, on)` (`index.html:1922`)
2. `ponerCapa` llama a `cargar(c)` (`index.html:1804`, `index.html:1928`)
3. `cargar` hace `fetch` del GeoJSON **una vez por sesión** con `?v=VER_DATOS` (`index.html:1849`)
4. los features se guardan en `datos[id]` (índice del buscador) y se pintan (`index.html:1736`)
5. se recalcula la leyenda y el contador (`index.html:1314`, `index.html:1935`)
Resultado: capa visible; por debajo de `zoomMin` se **atenúa**, no se retira.

### Abrir la ficha de un elemento
Disparador: clic en un símbolo del mapa.
1. el handler llama a `abrirFicha(properties, capa, latlng)` (`index.html:1638`, `index.html:1903`)
2. se pintan métricas destacadas, atributos humanizados y procedencia (`index.html:1502`)
3. la procedencia sale de `fuentes.json`, pedido al arrancar (`index.html:2080`)
4. se buscan elementos de otras capas ya cargadas a menos de 30 km, pinchables
Resultado: ficha con procedencia declarada y salto a vecinos.

### Refresco de datos vivos
Disparador: cron cada 30 minutos en `refresco.yml`.
1. el runner instala `requests` y escribe en `.env` sólo las claves que existan como secret
2. ejecuta `ree_vivo.py`, `omie.py`, `entsoe.py --mix`, `aemet_geo.py`, `dgt_rt.py` con
   `continue-on-error`: una fuente caída no rompe el refresco (`.github/workflows/refresco.yml`)
3. `fuentes_visor.py`, `catalogo.py`, `cifras.py` y `snapshot.py` regeneran metadatos y serie
4. `validar.py` decide si el dato se publica (`scripts/validar.py:35`)
5. el bot commitea `datos/`, `README.md` y `docs/BIBLIOTECA.md` y hace push
Resultado: la capa anterior se sustituye; su fecha (`descargado`) delata si quedó vieja.

## Despliegue

GitHub Pages desde la raíz del repo (`.nojekyll` presente), `push` a `main` = en vivo, sin build.
Los datos vivos los regenera Actions y los commitea el propio bot.

## Hallazgos de la exploración (no forman parte del modelo)

- `.github/workflows/validar.yml`: el paso «Validar cuadres de datos» tiene dos comandos en la misma
  clave `run:` sin `|`, así que YAML lo pliega en una línea y `python scripts/validar.py` acaba siendo
  **argumento** de `cifras.py --check`. El segundo gate no se ejecuta en push. **Inferido del fichero,
  no ejecutado en Actions.**
- `scripts/validar.py` lleva cifras declaradas a mano (`4929`, `1752`, `3176`); si el dato crece, el
  validador se pone rojo por diseño, pero el número vive en dos sitios (script y README).

## No cubierto

- El detalle de cada organismo (licencias, límites, errores literales): `docs/FUENTES.md` y `docs/apis.md`.
- `datos/dgt` (98 MB), `datos/nap_catalogo.json` (11 MB) y `datos/hermes` (9 MB) no se han abierto.
- El histórico de auditorías y sus problemas P1-P8: `docs/AUDITORIA.md`.
