---
titulo: NAP — Punto de Acceso Nacional de transportes
fecha: 2026-11-16
ambito: transporte
estado: publicado
---

# NAP — Punto de Acceso Nacional de transportes (MITMA)

**Sí tiene API, y está abierta a cualquiera con clave.** Durante varias sesiones este documento decía
que el gateway no aceptaba la clave por header y que solo se podía consultar por la web. **Era falso.**
El problema era el nombre de la cabecera.

## El error que costó tres intentos

Se probaron ocho formas de enviar la clave, todas con `401 Api Key was not provided`:

```
Authorization · X-Api-Key · X-API-KEY · apikey · Api-Key
X-CKAN-API-Key · X-Auth-Token · token        ← ninguna funciona
```

Y la ruta que se probaba era `/api/3/action/package_list`, que es el patrón **CKAN** y aquí **no existe**.

Las dos cosas correctas:

```bash
curl -H "ApiKey: <tu_clave>" https://nap.transportes.gob.es/api/Fichero/GetList
```

- La cabecera se llama **`ApiKey`** — sin prefijo `X-`, sin guion, con mayúsculas.
- La ruta es **`/api/Fichero/GetList`**, no un CKAN.

Lo encontró el código de `Ntizar/nap-dashboard`, que ya lo tenía resuelto. Lección: antes de concluir «no
hay acceso», mirar si un proyecto propio ya lo resolvió.

## Endpoints verificados

| Método | Ruta | Qué devuelve | Tamaño |
|---|---|---|---|
| `GET` | `/api/Fichero/GetList` | catálogo completo de conjuntos | **10,5 MB** |
| `POST` | `/api/Fichero/Filter` | catálogo filtrado (cuerpo JSON) | — |
| `GET` | `/api/Fichero/downloadLink/{id}` | **URL firmada de S3**, texto plano | ~300 B |
| `GET` | `/api/Region` | CCAA, provincias y municipios | 640 KB |

- La URL de `downloadLink` **caduca en 900 segundos** (`X-Amz-Expires=900`): se pide, se descarga y se
  tira. No se guarda.
- **`200` con 0 bytes**: el NAP devuelve respuestas vacías en ráfaga. Reintentar con 3 s de espera; no es
  un error de autenticación.

## Qué hay dentro

**169 conjuntos de datos, 550 operadores distintos**, medido el 2026-11-16:

| Tipo de transporte | Conjuntos |
|---|---:|
| Autobús | 148 |
| Ferroviario | 27 |
| Marítimo | 3 |
| Aéreo | 1 |

| Formato | Ficheros |
|---|---:|
| **GTFS-ZIP** (horarios completos) | 169 |
| GTFS RT (tiempo real) | 86 |
| SIRI | 67 |
| NeTEx | 30 |
| Documento PDF | 18 |

Cada fichero declara `numeroParadas`, `numeroViajes`, `tamanio`, `validado` y las fechas `desde`/`hasta`.
Los conjuntos más grandes:

| Paradas | Viajes | MB | Conjunto |
|---:|---:|---:|---|
| **41.450** | 209.561 | 94,5 | Autobuses y trenes de Cataluña (completa) |
| 28.001 | 183.118 | 58,9 | Autobuses y trenes de Cataluña (simplificada) |
| 27.218 | 191.981 | 150,9 | Autobuses Xunta de Galicia |
| 11.567 | 33.908 | 7,3 | ALSA autobuses |
| 8.408 | 58.470 | 76,4 | Interurbanos de la Comunidad de Madrid |
| 4.935 | 86.843 | 21,1 | Autobús urbano de Madrid (CRTM) |
| 1.167 | 129.827 | 15,6 | **Cercanías Renfe** |
| 1.050 | 120 | 1,5 | **Metro de Madrid** |
| 1.006 | 6.510 | 0,7 | **RENFE Media, Larga Distancia y AVE** |

## Horarios y frecuencias: dos métodos, no uno

Un GTFS declara las frecuencias de dos maneras y **no todos usan la misma**:

1. **`frequencies.txt`** — servicios por frecuencia («cada 6 minutos de 7:00 a 10:00»). Lo trae **Metro de
   Madrid**: 12 de sus 13 líneas lo declaran.
2. **Horario fijo en `stop_times.txt`** — cada viaje con su hora. Lo traen **Cercanías y AVE**: **no hay
   `frequencies.txt`** en sus ficheros.

Para el segundo caso la frecuencia se calcula contando **salidas reales por hora** (primeras paradas del
viaje). Pero hay una trampa: **en largo recorrido un «headway» no significa nada**. Un AVE no pasa cada
tres minutos porque salgan tres trenes a la misma hora, y publicar «AVE cada 3 min» es un dato falso.

Lo honesto en esos casos es **salidas al día**, y ahí hay una tercera trampa.

### Un GTFS no describe un día: describe todos

`trips.txt` incluye **todos los patrones de servicio**: laborables, sábados, festivos, verano, Navidad.
Sumarlos no da «salidas de un día», da la suma de todos los calendarios. El primer cálculo daba
**C1 con 26.847 salidas diarias y 1.816 a la hora**, que es imposible: son las 24 h de todos los días
del año a la vez.

Hay que filtrar por los `service_id` activos en **una fecha concreta** (`calendar.txt` + las excepciones
de `calendar_dates.txt`). Con fecha de servicio 2026-11-19:

| Línea | Salidas ese día | Pico | Rutas |
|---|---:|---:|---:|
| C1 | 981 | 71/h | — |
| C2 | 597 | 40/h | — |
| C3 | 487 | 31/h | — |
| R3 | 477 | 31/h | — |
| C5 | 391 | 32/h | — |

Y en largo recorrido: **Regional 898 · AVE 259 · AVANT 255 · Intercity 158 · AVLO 37 · Euromed 15**.
De 1.283 a 259 en el AVE: la diferencia era el calendario, no el tren.

## Trampa del formato

**`stop_sequence` no siempre empieza por `1`.** Los GTFS de Renfe numeran `01`, `02`, `03`. Comparar
`== "1"` no casa ninguna fila y la frecuencia sale a cero **sin ningún error**: el fallo es silencioso.
Para la hora de salida de un viaje es más fiable el **mínimo de sus paradas** que cualquier convención.

**Los CSV vienen con relleno de ancho fijo.** En el GTFS de Cercanías, `routes.txt` da
`route_id = '10T0001C1  '` (dos espacios) mientras `trips.txt` da `'10T0001C1'`. Sin `.strip()`,
**269 de 277 rutas quedan huérfanas**, el nombre no casa y la línea sale como `10T0018C5` en vez de `C1`.
El síntoma es silencioso. La pista: `route_text_color` con sesenta espacios en la cabecera.

## Cuarta trampa: el headway de una línea con ramas

Agrupar por nombre de línea y calcular el headway da un dato falso cuando esa línea tiene **varias rutas**.
C1 tiene **34 ramas** (Príncipe Pío, Aeropuerto-T4, Villalba…). Sumar sus 71 salidas de la hora punta da
`60/71 = 0,8 min`, o sea «un tren cada 48 segundos», que no existe en ningún andén.

**Regla:** el headway solo se publica cuando la línea tiene **una sola ruta**. Si agrupa varias, se
publican salidas y se anota cuántas ramas suman. Aplicado: **30 headways anulados** (24 en Cercanías,
6 en Renfe) y ninguno en Metro de Madrid, donde cada línea es una ruta y el dato sí es real
(línea 2: 6,7 min).

## Cómo se usa aquí

```bash
python scripts/nap.py --catalogo                        # 169 conjuntos + recibo
python scripts/nap.py --lista --tipo Ferroviario        # los 27 ferroviarios
python scripts/nap.py --gtfs 1134 --etiqueta metro-madrid
```

Salida: `datos/nap_paradas_<etiqueta>.geojson` (paradas con coordenadas) y
`datos/nap_<etiqueta>_recibo.json` (líneas, frecuencias, método empleado).

La clave vive en `.env` como `NAP_API_KEY`. Nunca en el repositorio.
