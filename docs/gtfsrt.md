---
titulo: GTFS-Realtime — vehículos en vivo
fecha: 2026-11-16
ambito: transporte
estado: publicado
---

# GTFS-Realtime — vehículos en vivo

## Qué es y por qué no sale del NAP

Un feed GTFS-RT es un **protobuf** que se consulta en bucle: cada petición devuelve la foto del
instante, no un fichero que se descarga una vez. Los campos que trae son `vehicle` (posición), `trip_update`
(retrasos por parada) y `alert` (avisos de servicio).

**El NAP de transportes no publica la URL de sus 86 feeds RT.** Comprobado:

| Prueba | Resultado |
|---|---|
| Catálogo `Fichero/GetList` (tipo 10 = GTFS RT) | los lista con `tamanio: 0`, sin URL ni metadatos |
| `Fichero/downloadLink/{id}` | **«Archivo no encontrado»** (funciona para GTFS-ZIP, no para RT) |
| `Fichero/download/{id}` | 500 |
| `GetFichero`, `rtlink`, `GtfsRt`, `Realtime`, `SIRI/GetList` | 404 |

El NAP entrega los feeds RT a agregadores por un canal aparte. **No hay endpoint público de descarga.**
Así que se usan las URLs directas de cada operador, que es lo que hace este script.

## Feeds verificados

| Operador | URL | Estado |
|---|---|---|
| **Renfe** | `https://gtfsrt.renfe.com/vehicle_positions.pb` | **abierto** |
| Renfe | `https://gtfsrt.renfe.com/trip_updates.pb` | abierto (retrasos) |
| Renfe | `https://gtfsrt.renfe.com/alerts.pb` | abierto (avisos) |
| TMB | `api.tmb.cat/v1/transit/gtfs-realtime/vehiclepositions` | **401** |
| EMT Madrid | — | requiere clave |
| EMT Valencia | `emtvalencia.es/GTFS-RT/...` | 404 |

```bash
python scripts/gtfsrt.py            # vehículos de los feeds abiertos
python scripts/gtfsrt.py --detalle  # añade retrasos y avisos
```

## Lo que sale (medido, 2026-11-16)

**403 vehículos de Renfe en 30 líneas**, con posición, rumbo, velocidad y última actualización:

| Línea | Vehículos |
|---|---:|
| C1 | 91 |
| C2 | 57 |
| C3 | 39 |
| C5 | 36 |
| R1 | 25 |
| R4 | 19 |
| R2S | 14 |

Y del `trip_updates`: **80 avisos de servicio** y retrasos por viaje.

## Trampas

- **`route_id` viene vacío en Renfe.** La línea está en la etiqueta del vehículo
  (`C1-23551-PLATF.(1)`): hay que partir por el guion para sacar `C1`. Sin eso, la capa sale sin línea y
  no se puede agrupar por ella.
- **`header_text` de las alertas viene vacío** aunque `description_text` sí trae el texto: leer solo el
  primero descarta los 80 avisos.
- **`VehiclePosition.delay` no existe en todas las versiones del protobuf.** Acceder directo lanza
  `Protocol message VehiclePosition has no "delay" field` y mata el bucle entero. Comprobar con
  `HasField` en `try`.
- **Renfe devuelve `200` con 0 bytes** en ráfaga (igual que el NAP): reintentar con espera o se descarta
  un feed que está bien.
- **Un feed RT no se cachea.** Guardarlo y volver a leerlo da una foto vieja: hay que refrescarlo, y por
  eso va como capa de carga bajo demanda.

## Capa en el visor

`datos/gtfsrt_vehiculos.geojson` — todas las capas de todos los operadores, con `operador` y `linea` en
las propiedades. Se mantiene también `datos/trenes.geojson` para la capa que ya existía.

## Pendiente

- **Añadir operadores** cuando haya clave: TMB, EMT Madrid, EMT Valencia, Bilbobus, Euskotren. El registro
  `FEEDS` de `scripts/gtfsrt.py` ya tiene el hueco y el estado de cada uno.
- **Retrasos por línea** con nombre legible (hoy el `trip_id` de Renfe no es la línea).

## El swagger del NAP confirma el límite

`nap.transportes.gob.es/api/swagger/v1/swagger.json` está **abierto** (35 endpoints, NSwag). Los que
podrían servir un feed RT:

| Endpoint | Qué hace al pedirle un GTFS-RT |
|---|---|
| `GET /api/Fichero/download/{id}` | **500** «An error occurred while processing your request» |
| `GET /api/Fichero/downloadLink/{id}` | **200** con el texto `Archivo no encontrado` |
| `GET /api/Fichero/{conjuntoDatoId}` | 200, pero el fichero llega con `tamanio: 0`, `metadatos: []` |

Es decir: el NAP **cataloga** el feed (existe, tiene `ficheroId`, se lista por tipo 10) pero **no lo
sirve**. No es un fallo de cabecera ni de ruta: no hay binario detrás. Los 86 feeds se entregan a
agregadores por un canal que no está en la API pública.

Lo que sí da el swagger y no usábamos: `GetListByFileType/{id}`, `GetListByOrganizacion/{id}`,
`GetListByRegion/{id}`, `historico/{conjuntoDatoId}` (versiones anteriores de cada conjunto) y
`downloadLinkAvisos`.
