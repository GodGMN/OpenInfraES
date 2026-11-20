<!-- GENERADO por c4-modelo-arquitectura/scripts/exportar-mapa.mjs desde communications/architecture-explorer/model.js.
     NO EDITAR A MANO: se regenera. Cambia model.js (y reglas.md) y vuelve a ejecutar. -->

# Arquitectura de OpenInfraES

> Base de datos de infraestructura española y el mapa que la indexa. Sin backend: scripts que descargan de los organismos, un almacén de datos con su recibo de procedencia, un visor estático y dos puertas que impiden publicar un dato que no cuadre. Empieza por «Conectores» y sigue el flujo «Refresco de datos vivos».

Mapa para agentes. La versión navegable (para personas) es `communications/architecture-explorer/index.html`:
doble clic, sin servidor.

## De un vistazo

| Qué | Cuánto |
|---|---:|
| Contexto (personas, sistemas, externos) | 9 |
| Contenedores y almacenes | 4 |
| Componentes | 17 |
| Elementos de código | 5 |
| Estados de ciclo de vida | 4 |
| Relaciones | 36 |
| Flujos documentados | 3 |

## Contexto

| Elemento | Tipo | Qué hace | Dónde |
|---|---|---|---|
| **Lector del mapa** | person | consulta la infraestructura | — |
| **OpenInfraES** | system | infraestructura de España en datos | README.md:1 |
| **OpenStreetMap** | ext | red, agua, transporte | https://overpass-api.de |
| **IGN · WMTS** | ext | teselas base sin clave | https://www.ign.es |
| **MITECO** | ext | embalses y plantas | https://www.miteco.gob.es |
| **REE · ESIOS · OMIE** | ext | demanda, mix, precio | https://www.ree.es |
| **MITMA · NAP · Renfe** | ext | trenes, puertos, DGT | https://nap.transportes.gob.es |
| **CSN · EMSC · AEMET** | ext | sismos y avisos | https://www.igme.es |
| **GitHub · Pages** | ext | publica y ejecuta el CI | https://ntizar.github.io/OpenInfraES/ |

## Contenedores

| id | Contenedor | Tecnología | Responsabilidad | Dónde |
|---|---|---|---|---|
| `visor` | **Visor del mapa** | HTML, JavaScript, Leaflet | index.html y 53 capas | index.html |
| `conectores` | **Conectores** | Python 3.12, requests | 39 scripts, uno por fuente | scripts/ |
| `almacen` | **Datos** | GeoJSON, CSV, JSON | 73 geojson + 30 recibos | datos/ |
| `gates` | **Arnés de datos** | Python, GitHub Actions | valida antes de publicar | scripts/validar.py |

## Componentes

### Visor del mapa — `index.html`

| id | Componente | Responsabilidad | Código |
|---|---|---|---|
| `cfg-capas` | **CAPAS (declaración)** | Array que define cada capa: grupo, fichero, estilo, zoomMin, filtro y campos de la ficha. Añadir una capa es añadir una entrada aquí. | index.html:1028 |
| `motor-capas` | **Motor de capas** | Un solo camino para encender una capa: checkbox, vistas temáticas, enlace permanente y API llaman a ponerCapa(). cargar() hace un fetch por sesión. | index.html:2061 |
| `render` | **Render del mapa** | Dibuja puntos (sólo los de la vista) y geometrías con L.geoJSON, con trazo oscuro en polígonos y atenuación por debajo de zoomMin. | index.html:1875 |
| `ficha` | **Ficha del elemento** | Panel de un elemento: métricas destacadas, atributos humanizados, procedencia con licencia y fecha, y qué hay a menos de 30 km. | index.html:1777 |
| `leyenda` | **Leyenda** | Recalcula la leyenda al cambiar capas; para capas con escala pinta la rampa con sus extremos en vez de una lista. | index.html:1431 |
| `procedencia-ui` | **Panel de fuentes** | Lee fuentes.json y catalogo.json al arrancar y los pinta como tabla de procedencia dentro del visor. | index.html:2233 |
| `api-visual` | **API de consola** | window.OpenInfraES: abrir(capa, i, zoom), estados(), fuentes() y bench() para medir el arrastre. Lo usa el arnés y las capturas. | index.html:2614 |
| `ciclo-capa` | **Ciclo de una capa** | Estados por los que pasa una capa en el visor. Un fallo de red deja __cargada en false para poder reintentar al volver a encenderla. | index.html:2051 |

### Conectores — `scripts/`

| id | Componente | Responsabilidad | Código |
|---|---|---|---|
| `conectores-fuente` | **Conectores por fuente** | Un script por organismo (descargar, hermes, nap, gtfsrt, dgt_rt, entsoe, omie, ree_vivo, sismos, irewater…). Escribe su recibo de descarga. | scripts/descargar.py |
| `normaliza` | **normaliza.py** | Provincia y comunidad autónoma siempre por código oficial, nunca por nombre: el nombre cambia y el cruce por texto pierde datos en silencio. | scripts/normaliza.py |
| `simplificar` | **simplificar.py** | Simplifica geometrías para el visor y deja un recibo con vértices antes y después (94.000 vértices cuestan un frame por arrastre). | scripts/simplificar.py |
| `agregados` | **agregar.py** | Convierte los GeoJSON de red y plantas en CSV por tensión, operador, tecnología y comunidad autónoma. | scripts/agregar.py |
| `procedencia` | **Procedencia** | fuentes_visor.py, catalogo.py y cadenas.py: generan fuentes.json y catalogo.json desde los recibos reales, separando fecha de dato, publicación y descarga. | scripts/fuentes_visor.py |
| `snapshot` | **snapshot.py** | Archiva una foto diaria de los datos vivos para poder responder «¿cómo ha evolucionado esto?». | scripts/snapshot.py |

### Arnés de datos — `scripts/validar.py`

| id | Componente | Responsabilidad | Código |
|---|---|---|---|
| `validador` | **validar.py** | Comprueba GeoJSON mínimos, cuadres de los agregados y conteos declarados. Termina en RESULTADO: VERDE o ROJO. | scripts/validar.py:35 |
| `cifras` | **cifras.py** | Reescribe la tabla de capas del README entre marcas y con --check falla si la prosa se ha desfasado del dato. | scripts/cifras.py:168 |
| `workflows` | **GitHub Actions** | refresco.yml relanza las capas vivas cada 30 minutos y commitea; validar.yml valida en cada push a main. | .github/workflows/refresco.yml |

## Código que conviene conocer

| id | Elemento | Qué hace | Código |
|---|---|---|---|
| `fn-ponercapa` | `ponerCapa()` | Sincroniza checkbox, mapa, leyenda y contador; en lote lo hace una vez al final. | index.html:2061 |
| `fn-cargar` | `cargar()` | fetch del GeoJSON con versión, guarda features en datos[id] y llama a pintarPuntos. | index.html:1943 |
| `fn-abrirficha` | `abrirFicha()` | Construye la ficha del elemento y busca vecinos en capas ya cargadas. | index.html:1777 |
| `fn-validar` | `main() · validar` | Cuadres de agregados y conteos declarados; rc=1 si algo no cuadra. | scripts/validar.py:35 |
| `fn-cifras` | `main() · cifras` | Con --check compara la tabla publicada con lo medido y falla si difieren. | scripts/cifras.py:168 |

## Ciclos de vida

**Ciclo de una capa**

- `apagada` (inicial) → `ponerCapa on` → `cargando`
- `cargando` → `fetch ok` → `cargada`, `fetch falla` → `fallo`
- `cargada` → `ponerCapa off` → `apagada`
- `fallo` → `reintento` → `cargando`

## Flujos

### Encender una capa

- **Actor:** Lector del mapa
- **Dispara:** Clic en el checkbox de la capa, una vista temática o la API de consola.
- **Antes:** La capa está declarada en CAPAS y su fichero existe en datos/.
- **Después:** Capa pintada, leyenda y contador actualizados; el fichero se ha pedido una sola vez.

1. Lector del mapa → Motor de capas: ponerCapa(id, true)
2. Motor de capas → Ciclo de una capa: a cargando
3. Motor de capas → Datos: GET fichero?v=VER
4. Datos → Motor de capas: features _(respuesta)_
5. Motor de capas → Render del mapa: pintaPuntos / L.geoJSON
6. Motor de capas → Leyenda: actualizarLeyenda()
7. Motor de capas → Ciclo de una capa: a cargada

### Abrir la ficha de un elemento

- **Actor:** Lector del mapa
- **Dispara:** Clic en un símbolo del mapa.
- **Antes:** La capa del elemento está encendida y cargada.
- **Después:** Ficha con métricas, atributos, procedencia con licencia y fecha, y vecinos pinchables.

1. Lector del mapa → Render del mapa: clic en el símbolo
2. Render del mapa → Ficha del elemento: abrirFicha(properties)
3. Ficha del elemento → Panel de fuentes: ¿de qué capa sale?
4. Panel de fuentes → Datos: lee fuentes.json
5. Datos → Panel de fuentes: organismo, licencia, fecha _(respuesta)_
6. Ficha del elemento → Render del mapa: busca a 30 km
7. Render del mapa → Ficha del elemento: vecinos pinchables _(respuesta)_

### Refresco de datos vivos

- **Dispara:** Cron de GitHub Actions cada 30 minutos.
- **Antes:** Las claves que necesiten las fuentes están como secret; si falta una, ese paso se salta.
- **Después:** datos/ regenerado y commiteado por el bot; la fecha del recibo dice de cuándo es.

1. GitHub Actions → Conectores por fuente: cron */30 * * * *
2. Conectores por fuente → REE · ESIOS · OMIE: ree_vivo · omie · entsoe
3. REE · ESIOS · OMIE → Conectores por fuente: JSON _(respuesta)_
4. Conectores por fuente → normaliza.py: normaliza campos
5. normaliza.py → Datos: escribe + recibo
6. GitHub Actions → validar.py: python validar.py
7. validar.py → Datos: lee recibos y conteos
8. validar.py → GitHub Actions: VERDE _(respuesta)_
9. GitHub Actions → GitHub · Pages: commit datos/
10. GitHub · Pages → Visor del mapa: sirve la web nueva

## Dependencias externas

| Desde | Hacia | Qué se intercambia |
|---|---|---|
| Conectores | OpenStreetMap | Overpass |
| Conectores | MITECO | agua y plantas |
| Conectores | REE · ESIOS · OMIE | demanda y mix |
| Conectores | MITMA · NAP · Renfe | NAP y GTFS-RT |
| Conectores | CSN · EMSC · AEMET | sismos y avisos |
| Visor del mapa | IGN · WMTS | pide teselas |
| GitHub Actions | GitHub · Pages | commit y push |

## Reglas para tocar este proyecto

### Invariantes (de `GUIA.md` y de los gates del repo)

- **Los GeoJSON no se editan a mano.** Se regeneran con su script. Un dato mal se corrige en la
  fuente o en `scripts/<fuente>.py`, nunca en `datos/`.
- **Cada capa tiene su recibo** (`datos/<capa>_recibo.json`). Sin recibo, `validar.py` falla.
- **Nada inventado ni estimado sin marcar**: lo calculado (haversine, caudal modelado, trazado
  incompleto) se declara en el propio dato y en la ficha.
- **Licencia por capa.** OSM es ODbL; IGN/SCNE, MITMA y MITECO son CC BY 4.0; REE y OMIE tienen
  condiciones propias. Mezclar ODbL con CC BY en un derivado obliga a ODbL para el conjunto.
- **Toda cifra publicada lleva fecha de dato y fecha de descarga**: no son lo mismo.
- **Provincia y CCAA por código oficial**, nunca por nombre (`scripts/normaliza.py`).
- **Credenciales solo en `.env`** (ignorado por git). Nunca en commits, docs ni chat.
- **Los `.geojson` de `datos/` no se sirven con caché eterna**: el visor pide `?v=VER_DATOS`.

### Cómo se añade una capa (6 pasos, en este orden)

1. Script propio en `scripts/<fuente>.py`: descarga, normaliza y escribe su `_recibo.json`.
2. Si trae geometría: añadirla a `scripts/simplificar.py` con su tolerancia.
3. Declarar la fuente en `scripts/fuentes_visor.py` y la cadena en `scripts/cadenas.py`.
4. Añadir la entrada al array `CAPAS` de `index.html` (con `zoomMin` si a escala nacional no aporta).
5. Pasar los gates (abajo).
6. Commit en castellano describiendo la capa y su fuente.

### Verificar antes de dar algo por bueno

```bash
python scripts/cifras.py --check     # la tabla del README cuadra con el dato medido
python scripts/validar.py            # debe terminar en: RESULTADO: VERDE
python -m py_compile scripts/<lo_que_toques>.py
node --check <js>                    # si tocas JS suelto
```

En el navegador: `OpenInfraES.estados()` dice qué capa está cargada y con cuántos features; `bench()`
mide el arrastre. Antes de decir «va más fluido», medir.

### Trampas conocidas

- **`.github/workflows/validar.yml` no ejecuta `validar.py`**: el paso tiene dos comandos en el mismo
  `run:` sin `|`, YAML lo pliega en una línea y `python scripts/validar.py` acaba siendo argumento de
  `cifras.py` (que lo ignora). En cada push solo corre el gate de cifras. *(Pendiente de corregir.)*
- `scripts/validar.py` lleva conteos escritos a mano (`4929`, `1752`, `3176`) que también están en el
  README: si el dato crece, hay que tocar los dos sitios.
- `index.html` es un único fichero de ~2.600 líneas: el estado de una capa (`__cargada`) y el camino
  único `ponerCapa()` son la parte delicada. No añadir un segundo camino para encender capas.
- El repo pesa ~275 MB: no clonar ni copiar en bucle; no abrir `datos/dgt` (98 MB) con un editor.

---
Generado desde `communications/architecture-explorer/model.js` · repo https://github.com/Ntizar/OpenInfraES.
