---
titulo: APIs oficiales — estado verificado
fecha: 2026-11-16
ambito: espana
estado: publicado
---

# APIs oficiales: qué responde hoy y qué no

Cada línea de esta tabla se probó con una petición real el **16-11-2026**. Los errores están citados
literalmente: un `400` a secas no sirve para depurar.

Las fichas completas de cada organismo —qué publica, licencia, frecuencia y qué capa alimenta— están
en [`FUENTES.md`](FUENTES.md). Aquí, solo el estado técnico y las trampas.

## 1. Responde sin clave

| Organismo | Endpoint | Devuelve |
|---|---|---|
| **REE** | `apidatos.ree.es/es/datos/generacion/estructura-generacion?...&time_trunc=day` | 14 tecnologías |
| **REE** | `apidatos.ree.es/es/datos/balance/balance-electrico?...&time_trunc=day` | balance del día |
| **REE** | `apidatos.ree.es/es/datos/demanda/evolucion?...&time_trunc=day` | demanda |
| **MITECO** | `sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/` | 11.528 estaciones |
| **MITMA** | `mapas.fomento.gob.es/arcgis/rest/services/Hermes/<servicio>/MapServer/<capa>/query?...&f=geojson` | carreteras, puertos, terminales |
| **IGN** | `ign.es/wmts/ign-base?...` | teselas de cartografía |
| **Renfe** | `gtfsrt.renfe.com/vehicle_positions.pb` | 418 trenes |
| **Renfe** | `data.renfe.com/api/3/action/package_show?id=estaciones-cercanias-<núcleo>` | estaciones por núcleo |
| **EMSC-CSEM** | `seismicportal.eu/fdsnws/event/1/query?format=json&...` | 80 sismos en 7 días |
| **IGN / BTN** | `atlas.eltercioviejo.com/datos/manifest.json` | 42 capas vectorizadas |

## 2. Responde con clave

| Organismo | Endpoint | Sin clave | Con clave |
|---|---|---|---|
| **ESIOS (REE)** | `api.esios.ree.es/indicators/<id>` | **403** | 1.982 indicadores; previsión en 460 y 541 |
| **AEMET** | `opendata.aemet.es/opendata/api/avisos_cap/...` | **404** | sin verificar (falta alta) |
| **ENTSO-E** | `web-api.tp.entsoe.eu/api?documentType=A75...` | **401** | sin verificar (falta alta) |
| **NAP (MITMA)** | `nap.transportes.gob.es/api/3/action/package_list` | **401** | **404** (ver [`nap.md`](nap.md)) |

## 3. Roto o limitado, con el error exacto

| Intento | Error | Consecuencia |
|---|---|---|
| REE `time_trunc=hour` en cualquier widget | `400` «Los datos solicitados no están disponibles» | la API pública **solo** sirve agregados diarios |
| REE `demanda/demanda-tiempo-real` | `400` | no hay tiempo real por API |
| REE `geo_limit=ccaa` | `500` | no hay generación por comunidad autónoma |
| REE `generacion/potencia-instalada` | `500` | sin potencia instalada por la API |
| MITMA `resultRecordCount=1000` | HTML de error | paginar de 500 en 500 |
| MITMA capa 0 de aeropuertos | `Failed to execute query` | usar las capas 1 y 2 |
| Overpass sin `User-Agent` | `406 Not Acceptable` | cabecera obligatoria |
| Overpass en hora punta | `502` / `504` | backoff y espejos |
| MITECO con `urllib` | `SSLEOFError` | descargar con `curl` |
| IGN WMTS sin `Accept: image/*` | `200` con **0 bytes** | cabecera y `Referer` obligatorios |

## 4. Trampas de formato que cuestan una hora cada una

**REE es JSON:API y los datos no están donde parecen.** `data.attributes.values` solo trae título y
`last-update`. Las series están en **`included[]`**:

```json
{"data": {"attributes": {"title": "...", "last-update": "..."}},
 "included": [{"attributes": {"title": "Eólica", "values": [{"value": 311168.0}]}}]}
```

**El MITECO usa coma decimal y claves con espacios**: `"Latitud": "39,211417"`,
`"Longitud (WGS84)": "-1,539167"`, `"Precio Gasoleo A": "1,752"`.

**Renfe no rellena `route_id`**: la ruta va en la etiqueta (`C1-23551` → `C1`).

**EMSC usa `-1` como profundidad** para «superficie o desconocida».

**El Atlas da el `fichero` relativo a `/datos/`**, no a la raíz: concatenarlo mal deja 17 capas en 404.
Y algunas capas **mezclan geometrías**: `red-electrica` son 657 polígonos de subestación y 2 tendidos;
hay que mirar `categoria`, no el tipo de la primera feature.

## 5. Un 200 no es una prueba

El INE y el MITECO sirven **páginas de error con código 200**. La verificación de este repositorio
compara el **título** de la página devuelta, no solo el código. Y para los GeoJSON cuenta features: un
fichero de 0 bytes con 200 es un fallo silencioso, no un éxito.

## 6. Qué pedir, por orden de valor

1. **ENTSO-E** (formulario, gratis) — único con generación y previsión **por unidad**.
2. **AEMET** (registro, gratis) — cierra el bloque de riesgo meteorológico.
3. **NAP** — aclarar el header; 179 conjuntos de transporte público esperando.

Ninguno cuesta dinero. Los dos primeros son un formulario.
