---
titulo: NAP de transporte — estado real y cómo se usa
fecha: 2026-11-16
ambito: espana
estado: publicado
---

# NAP de transporte — qué hay, qué no, y cómo se usa sin sobrecargar

**<https://nap.transportes.gob.es>** es el Punto de Acceso Nacional de datos del transporte
(obligación europea de concentrar la oferta de transporte de viajeros en un punto único por país).

## Qué contiene

Su propio portal lo dice en la portada:

| Modo | Conjuntos de datos |
|---|---:|
| Autobús | **148** |
| Ferroviario | **27** |
| Marítimo | **3** |
| Aéreo | **1** |
| **Total** | **179** |

Cada conjunto es un GTFS (o similar) de un operador: servicios regulares de autobús de Aragón,
AISA en Madrid, Montferri… El NAP no es un servicio de consulta en vivo: es un **catálogo de
descargas**.

## La API con clave: probado y no funciona por header

Con una clave de usuario del NAP (`NAP_API_KEY` en `.env`, nunca en el repo) se probaron **nueve
formas** de autenticación contra el catálogo CKAN (`/api/3/action/package_list`):

| Forma | HTTP | Respuesta |
|---|---|---|
| `Authorization: <clave>` | 401 | `Api Key was not provided.` |
| `X-Api-Key` | 401 | `Api Key was not provided.` |
| `X-API-KEY` | 401 | `Api Key was not provided.` |
| `Api-Key` | 401 | `Api Key was not provided.` |
| `X-CKAN-API-Key` | 401 | `Api Key was not provided.` |
| `X-Auth-Token` | 401 | `Api Key was not provided.` |
| `token` | 401 | `Api Key was not provided.` |
| `?api_key=` | 401 | `Api Key was not provided.` |
| **`apikey`** | **404** | *(sin cuerpo)* |

Dos pistas que valen: **sin clave el gateway responde 401** («Api Key was not provided», mensaje
de CKAN) y **con el header `apikey` responde 404** en *todas* las rutas, incluidas las que existen
con otros headers. Es decir: el gateway reconoce ese nombre de header, pero enruta a otro sitio y
la petición no llega al catálogo.

El resto de rutas probadas devuelven lo mismo: `/api/v3/api-docs`, `/api/openapi.json`,
`/api/v1/datasets`, `/api/datasets`, `/api/3/action/package_search` (GET y POST).

`/api` sirve una **Swagger UI**, pero su spec también está detrás del gateway. Sin el spec ni el
header correcto, no hay forma razonable de adivinarlo: hace falta que el NAP documente cómo se
envía la clave.

## Dónde está el acceso (y por qué no lo encuentras)

No hay un botón de «obtener clave de API» porque **el NAP no está pensado para consultarse por API**.
En `nap.transportes.gob.es/entidades-colaboradoras` solo hay una lista de entidades adheridas; las
rutas de registro (`/registro`, `/alta`, `/signup`) devuelven **404** y el portal es una SPA sin API
de consulta documentada.

La lectura correcta es: el NAP es el punto donde los **operadores publican** sus datos (por eso se
habla de «entidades colaboradoras»), y el ciudadano los consulta **por la web**, no por un endpoint.
La clave que tienes no abre el catálogo por ninguna de las nueve formas probadas.

Para usarlo de verdad haría falta **contacto con el NAP/MITMA** y que documenten el header. Mientras
tanto, los datos de transporte se obtienen de cada operador: Renfe (GTFS-RT y estaciones), y los
catálogos autonómicos y municipales.

## Lo que sí funciona: el catálogo nacional abierto

Los mismos datos (y más) están en **datos.gob.es**, que es CKAN abierto y no pide nada:

```bash
curl "https://datos.gob.es/apidata/catalog/dataset/title/autobus?_format=json&_pageSize=8"
```

Devuelve conjuntos reales: paradas y tiempos del autobús urbano de Zaragoza, oferta planificada de
la red interurbana de Madrid, servicios de Castilla-La Mancha… Cada uno enlaza a su catálogo de
origen (Comunidad de Madrid, Zaragoza, Castilla-La Mancha), que es donde está el fichero.

## Cómo se usa en este repo: bajo demanda, sin cargar nada

`scripts/nap.py` no descarga nada si no se le pide:

```bash
python scripts/nap.py --estado              # sondea el NAP con la clave y dice qué responde
python scripts/nap.py --buscar "autobus"    # busca en datos.gob.es (abierto)
python scripts/nap.py --dataset <url>       # inspecciona UN conjunto concreto
```

Regla que se aplica al visor: **ninguna capa del NAP se carga sola**. Los 179 conjuntos son
demasiado volumen para servirlos desde un `http.server` local, y el usuario lo pidió explícito: no
sobrecargar hasta que la web esté en un servidor. Cuando se monte, la vía es la misma que ya usa el
visor con todo lo demás: la capa se descarga **cuando se enciende**, nunca al abrir.

## Qué haría falta para integrarlo de verdad

1. **La documentación del header** del gateway (o un ejemplo de llamada del propio NAP).
2. O bien descargar los GTFS a mano desde el portal y servirlos como ficheros estáticos: para 179
   conjuntos eso es un pipeline de descarga, no una consulta.
3. Para el visor, lo útil no son los 179 GTFS sino **paradas y líneas** de los núcleos grandes; eso
   ya está cubierto con data.renfe.com para Cercanías (405 estaciones) y con datos.gob.es para
   autobús urbano.

## Advertencia de licencia

El NAP publica bajo condiciones propias por conjunto. **No se copia nada al repositorio**: se
enlaza. Y las capas de OSM del visor siguen siendo ODbL (comparte igual), así que no se pueden
mezclar alegremente con datos del NAP en un mismo producto derivado.
