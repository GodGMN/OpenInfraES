---
titulo: DGT — NAP de Tráfico y Movilidad
fecha: 2026-11-16
ambito: transporte
estado: publicado
---

# DGT — Punto de Acceso Nacional de Tráfico y Movilidad

## Primero: no es el NAP de transportes

Hay **dos** puntos de acceso nacional y es fácil confundirlos:

| | URL | De qué va | Conjuntos |
|---|---|---|---:|
| NAP de **transportes** (MITMA) | `nap.transportes.gob.es/api` | horarios y tiempo real de **operadores de transporte público** | 169 |
| NAP de **tráfico** (DGT) | `nap.dgt.es` | **carreteras**: cámaras, incidencias, paneles, recarga eléctrica | **37** |

En el NAP de transportes **la DGT no aparece**: cero conjuntos. No es un fallo de búsqueda; es que aquel
catálogo son operadores de bus y tren.

## Lo que publica la DGT

37 conjuntos, entre ellos:

| Conjunto | Qué es |
|---|---|
| **Cámaras DGT DATEX2 v3.7** | 1.977 cámaras en carretera |
| **Puntos de recarga eléctrica para vehículos** | 12.144 puntos |
| Incidencias DGT DATEX2 v3.7 | incidencias en tiempo real |
| Paneles DGT tiempo real / localizaciones | paneles de mensaje variable |
| Mapa de tráfico · Mapa de movilidad | cartografía base |
| Estado de ocupación de parkings en ayuntamientos | plazas libres |
| Conos conectados · Localización de conos | obras y pruebas deportivas |
| Camino de Santiago, puntos y tramos de riesgo | seguridad vial |
| Tráfico calle 30 (cámaras) | Madrid |

## Cómo se obtiene

**La API CKAN responde `403`.** `nap.dgt.es/api/3/action/package_list` está capada aunque la web sea
pública. Así que los recursos se piden por la **URL DATEX II directa** que cada dataset publica en su
página:

```
GET https://nap.dgt.es/datex2/v3/dgt/DevicePublication/camaras_datex2_v37.xml
GET https://nap.dgt.es/datex2/v3/miterd/EnergyInfrastructureTablePublication/electrolineras.xml
```

Formato: **DATEX II v3 en XML** (el estándar europeo de información de tráfico), con namespaces.

```bash
python scripts/dgt.py --camaras          # 3,7 MB  -> 1.977 puntos
python scripts/dgt.py --electrolineras   # 84 MB   -> 12.144 puntos
```

## Trampas

- **El XML de electrolineras pesa 84 MB.** Cargarlo con `ET.parse()` se come la memoria; hay que usar
  `iterparse` y hacer `el.clear()` tras cada sitio.
- **El nombre del punto de recarga está en `label`, no en `name`.** Buscar `name` devuelve vacío en todos
  y el mapa queda con 12.144 puntos sin etiqueta, sin ningún error. Tampoco hay `addressLine`: la
  ubicación útil es `postcode`.
- **La API CKAN da 403** con cualquier User-Agent. No concluir «la DGT no publica»: la web y los ficheros
  DATEX sí responden.
- **El conteo parcial engaña.** Un barrido de los primeros 60.000 elementos del XML veía **748** sitios;
  el fichero completo tiene **12.144**. Nunca dar por bueno un número sacado de un parseo truncado.

## Lo que sale

### Cámaras (1.977)

Cada una con `carretera`, `provincia`, `kilómetro`, `tipo` y `actualizado`:

```
A-62  · BURGOS   · km 25.3
A-62  · PALENCIA · km 57.9
```

43 provincias con cobertura.

### Puntos de recarga (12.144)

Cada uno con nº de conectores y **potencia máxima**:

| Dato | Valor |
|---|---:|
| Puntos | 12.144 |
| Con potencia declarada | 12.144 (100 %) |
| Potencia máxima | **1.000 kW** |
| Potencia mediana | **22,2 kW** |

La mediana de 22 kW es el dato que ordena el debate sobre la red de recarga: la mayoría son puntos lentos
o semilentos, no cargadores rápidos. Y el máximo de 1.000 kW convive con ellos en el mismo mapa.


## Tráfico en tiempo real (sí, hay)

El NAP de la DGT publica **feeds en vivo**, sin clave, en DATEX II. Cada petición devuelve el
estado del instante:

| Feed | URL | Tamaño |
|---|---|---:|
| **Incidencias** | `nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml` | 5,8 MB |
| **Paneles de mensaje variable** | `nap.dgt.es/datex2/v3/dgt/VmsPublication/datex2_v37.xml` | 3,7 MB |

```bash
python scripts/dgt_rt.py --incidencias            # usa la copia local
python scripts/dgt_rt.py --incidencias --refrescar # baja el estado actual
```

### Lo que sale (medido 2026-11-16)

**1.350 incidencias activas**, con carretera, kilómetro, provincia, municipio, sentido, carril y fechas:

| Tipo | Incidencias |
|---|---:|
| Gestión de calzada o carril | 798 |
| Otras (nombre genérico) | 411 |
| Tráfico anormal | 48 |
| Obstrucción | 35 |
| Gestión de velocidad | 33 |
| Condición no meteorológica | 15 |
| Medioambiental | 5 |

Y por subtipo: **corte de carril 320 · corte de calzada 141 · paso alternativo 130 · tráfico lento 48**.
Gravedad: **121 de gravedad alta**, 50 media y 1.179 sin declarar.

### Trampa: el tipo NO es el primer hijo

`situationRecord` empieza con `situationRecordCreationTime`, `probabilityOfOccurrence`, `source`… Coger
«el primer hijo que no sea de sistema» devuelve `situationRecordCreationReference` como tipo, y las 1.350
incidencias salen clasificadas así. El tipo real está en los hijos que **acaban en `*Type`**
(`roadOrCarriagewayOrLaneManagementType`, `abnormalTrafficType`, `obstructionType`…), y su **texto** es el
subtipo. La gravedad viene aparte, en `severity`, y **falta en el 87 %** de los registros: no rellenarla
con «baja», dejar vacío.

Los subtipos llegan en inglés porque DATEX II es un estándar europeo: `laneClosures`, `carriagewayClosures`,
`singleAlternateLineTraffic`. Traducirlos en el parser es tentador, pero entonces el dato deja de ser
comparable con el de cualquier otro país.


## Paneles de mensaje variable: lo que dice la carretera ahora

1.019 paneles con mensaje y posición. **El texto y la ubicación están en dos ficheros distintos** y hay que
cruzarlos:

| Fichero | Qué trae | Clave |
|---|---|---|
| `VmsPublication/datex2_v37.xml` | el mensaje | `vmsControllerReference@id` |
| `DevicePublication/vms_datex2_v37.xml` | lat/lon, carretera, provincia | `device@id` |

El mismo número en los dos (`167938`). Sin el cruce hay posiciones sin mensaje o mensajes sin mapa.

```bash
python scripts/dgt_rt.py --paneles
```

### Lo que dicen los paneles (2026-11-18)

| Mensaje | Paneles |
|---|---:|
| MODERE LA VELOCIDAD | 102 |
| CON LLUVIA MODERE VELOCIDAD | 99 |
| CON LLUVIA MODERE LA VELOCIDAD · CON CHOIVA MODERE A VELOCIDADE | 94 |
| VELOCIDAD CONTROLADA POR RADAR | 77 |
| SOL BAJO MODERE VELOCIDAD | 31 |

- **Son bilingües** (castellano y gallego/catalán en la misma línea): es el mismo panel mostrando dos
  idiomas alternos, no dos mensajes.
- **El texto viene con saltos de línea y relleno de ancho fijo** de la matriz del panel
  (`'MODERE
     LA
 VELOCIDAD'`). Hay que colapsar los espacios o el popup sale escalonado.
- **Se repiten por índice de mensaje**: un controlador puede tener dos mensajes alternos
  (`messageIndex 1` y `2`), por eso el mismo panel puede aparecer con dos textos.

Capa **«Paneles de mensaje variable»** en DGT · Tráfico. En la lista y en la ficha se muestra el
**mensaje**, no la carretera: un panel vale por lo que dice.

## Capas en el visor

Grupo **DGT · Tráfico**:

- **Cámaras de tráfico (DGT)** — 1.977 puntos, visibles desde zoom 8.
- **Puntos de recarga eléctrica** — 12.144 puntos, desde zoom 7.

Registradas en `datos/fuentes.json` con organismo **DGT** para que el panel ⓘ Fuentes diga de dónde
salen y con qué licencia.

## Pendiente de la DGT

- **Incidencias DATEX2** (cortes, obras, retenciones) — el conjunto más vivo del catálogo.
- **Paneles de mensaje variable en tiempo real**: lo que dicen los paneles de la carretera ahora mismo.
- **Ocupación de parkings**: cruce interesante con movilidad urbana.
