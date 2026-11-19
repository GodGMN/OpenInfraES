# I-ReWater HUB · recursos hídricos, agua regenerada y regadío

El visor público [`i-rewater-hub.com`](https://i-rewater-hub.com) sirve sus capas desde un **catálogo
WebGIS abierto**, sin clave. Es del proyecto **I-ReWater**, un Interreg (España–Portugal–Francia)
sobre reutilización de agua.

## El catálogo

```bash
curl https://api.i-rewater-hub.com/api/v1/webgis/public
```

Devuelve 2 categorías y **15 capas**, con metadatos completos: campos, leyenda, filtros y temáticas.

| Capa | slug | Tipo | Tabla | Campos |
|---|---|---|---|---|
| Estaciones depuradoras (EDAR) | `hib-edar` | vector | `edar` | 19 |
| Unidades de Demanda Agrícola | `hib-uda` | vector | `uda` | 8 |
| Perímetros de regadío | `hib-regadio` | vector | `regadio` | 5 |
| Particiones de regadío (25 h) | `hib-regadio-particion` | vector | `regadio_particion` | 4 |
| Demarcaciones hidrográficas | `hib-demarcacion` | vector | `demarcacion` | 13 |
| Indicadores regionales (NUTS2) | `hib-nuts2` | vector | `nuts2` | 13 |
| Indicadores provinciales (NUTS3) | `hib-nuts3` | vector | `nuts3` | 13 |

## Cómo se sacan los datos

**No hay endpoint de datos.** Solo **vector tiles MVT**:

```
https://api.i-rewater-hub.com/api/v1/tiles/hib_edar/{z}/{x}/{y}.pbf
```

Se recorren los tiles que cubren España, Portugal, Baleares y Canarias a un zoom dado, se decodifican
con `mapbox-vector-tile` y se deduplican por `id` (un objeto aparece en varios tiles por el solape).

```bash
uv run --with mapbox-vector-tile python scripts/irewater.py --capa hib_edar --zoom 8
```

### Reproyección de las coordenadas

Los MVT traen coordenadas **dentro del tile** (0-4096, `y` hacia abajo), no lon/lat:

```python
lon = (x + px / 4096) / 2**z * 360 - 180
lat = atan(sinh(pi * (1 - 2 * (y + py / 4096) / 2**z))) * 180 / pi
```

Verificado con las plantas más grandes: Besòs (2,27 M HE) cae en Barcelona, Sur (1,39 M HE) en
Madrid, Pinedo en Valencia, Galindo en Bilbao, Guadalhorce en Málaga.

## Lo que aporta: agua regenerable

3.501 EDAR con **volumen reutilizable**, **superficie potencialmente regable** y **demanda potencial
de riego**. Ese dato no está en ninguna fuente primaria con ese formato.

| | |
|---|---|
| EDAR | **3.501** (España 2.086 · Francia 921 · Portugal 484 · Andorra 4) |
| Volumen reutilizable en España | **3.617,9 hm³/año** |
| Impacto hidrológico | Bajo 1.943 · Alto 769 · Moderado 569 · Nulo 220 |

Campos de una EDAR:

| Campo | Ejemplo (Besòs) |
|---|---|
| `qentrada_he` | 2.278.009 habitantes equivalentes |
| `capacidad` | caudal de diseño |
| `volumen_reutilizable_m3` | volumen anual reutilizable |
| `superficie_pot_regable_ha` | hectáreas que se podrían regar |
| `demanda_potencial_riego` | demanda de riego en la zona |
| `indice_impacto_hidrologico` | Bajo / Moderado / Alto / Nulo |
| `municipio` | **municipio servido, no ubicación de la planta** |

**Ojo con `municipio`**: es el municipio al que sirve la depuradora, no dónde está. Usarlo para
geolocalizar lleva a errores de cientos de kilómetros («Sevilla la Nueva» está en Madrid).


## Lo que el catálogo anuncia y lo que sirve

De las 7 capas vectoriales del catálogo, **solo 2 publican tiles**:

| Capa | Tiles | Resultado |
|---|---|---|
| `hib_edar` | **200** | 3.501 EDAR |
| `hib_demarcacion` | **200** | 29 demarcaciones (España 17, Portugal 8, Francia 2, Andorra 2) |
| `hib_uda` | **404** | sin datos |
| `hib_regadio` | **404** | sin datos |
| `hib_regadio_particion` | 404 | sin datos |
| `hib_nuts2` | 404 | sin datos |
| `hib_nuts3` | 404 | sin datos |

El catálogo las describe con campos, leyenda y filtros, pero el endpoint de tiles responde
**404**. No es un fallo del cliente: el servidor no las tiene. Se comprobó a z=6, 7 y 8.

Las demarcaciones de I-ReWater **complementan** las 25 de MITECO: añaden Portugal, Francia y
Andorra, que la fuente española no cubre.

## Cartografía de referencia: las fuentes oficiales

La segunda categoría del catálogo apunta directamente a los servicios oficiales, y esas sí son
fuentes primarias:

| Capa | Servicio oficial |
|---|---|
| Red hidrográfica | `servicios.idee.es/wms-inspire/hidrografia` — **IDEe** |
| SIGPAC: recintos | `sigpac-hubcloud.es/wms` — **FEGA/MITECO** |
| Catastro | `ovc.catastro.meh.es` — **Dirección General del Catastro** |
| Ortofoto PNOA | `ign.es/wms-inspire/pnoa-ma` — **IGN** |
| Ortofoto Portugal | `ortos.dgterritorio.gov.pt` — **DGT Portugal** |

Estas se citan por su organismo, no por I-ReWater.

## Atribución

I-ReWater es un **agregador**: no produce los datos de EDAR, los armoniza de fuentes nacionales y
añade los campos derivados. En el visor se cita **I-ReWater HUB (proyecto Interreg)** como origen
de la capa y se declara en el recibo que el valor está en los campos calculados.

## Ficheros

- `datos/irewater_hib_edar.geojson` — 3.501 puntos, 1,8 MB.
- `datos/irewater_hib_edar_recibo.json` — conteos y distribución de impacto.
