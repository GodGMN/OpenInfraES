# Códigos postales · modelo y fuentes

## El problema

Un código postal **no es un municipio**. Un CP puede bañar varios términos
(`28914` Getafe / Leganés, `25123` Lleida / Torrefarrera) y un municipio grande tiene
decenas de CP. Guardar «el municipio del CP» es perder información; guardar «el
primero que devuelve la API» es inventarla. Ejemplo real de lo que pasó con ese atajo:
el `28760` (Tres Cantos) salía como Madrid.

## El modelo

`datos/cp_municipios.json` (≈250 KB, va en el repo: es dato de base, no caché).

```
"28013": [ [cod_ine, municipio, provincia, poblacion, anio_padron, n_direcciones], ... ]
```

* **Todas** las filas de un CP, ordenadas por `n_direcciones` de mayor a menor.
* La **primera** es el municipio **principal** (donde caen más direcciones de ese CP).
* El resto son municipios que el CP también toca, con su recuento: no se descartan ni
  se eligen a suertes.
* La población es siempre la del **municipio** (padrón INE, con su año), no la del CP.

API pública en el visor:

```js
OpenInfraES.cp("28914")
// [ { cod_ine:"28065", municipio:"Getafe",   ..., direcciones:812, principal:true  },
//   { cod_ine:"28074", municipio:"Leganés",  ..., direcciones:  3, principal:false } ]
OpenInfraES.irA("28065")     // lleva el mapa al municipio y abre su ficha
```

En el buscador, un CP de 5 cifras resuelve a su municipio principal y lista los demás.

## Las fuentes, y por qué esta

| Fuente | Estado | Por qué |
|---|---|---|
| **IGN · IDEE — API de Direcciones de CartoCiudad** (OGC API Features) | **en uso** | Responde sin clave; cada dirección trae `component_PostalDescriptor`, `component_AdminUnitName_4` (municipio) y `_3` (provincia). Es API y es oficial. |
| CNIG · Centro de Descargas (geopackage de CartoCiudad por provincia) | **bloqueada** | `curl` devuelve **000** (sin conexión) desde esta red. Sería la vía con `ine_mun` en el propio fichero. |
| Catastro · descargadatos (callejero) | **bloqueada** | Igual: **000**. |
| INE · API de tablas (Tempus3) | **no existe** | Ni `OPERACIONES_DISPONIBLES` (166 operaciones) ni las tablas del padrón traen CP; la tabla `33583` de población por CP devuelve **204 vacío**. |
| datos.gob.es · API de catálogo | **no existe** | Búsqueda por título «códigos postales»: **0 resultados**. |

## El barrido

`scripts/callejero.py` recorre el espacio completo de CP españoles (01000–52999,
52.000 candidatos) **por lotes** con filtro `IN (...)`, cuenta cuántas direcciones hay
de cada pareja CP–municipio y subdivide el lote cuando un CP no aparece (puede no
existir o haber quedado fuera del límite de respuesta). Los recuentos se guardan en
`datos/.cp_api_cache_<desde>_<hasta>.json`, así que se puede **cortar y reanudar**.

El **código INE no viene en la API**: se resuelve contra `datos/municipios.geojson` por
(nombre normalizado + provincia del CP) y **solo si es único en esa provincia**. Los
casos con más de un candidato se escriben en `homonimos` y no se resuelven a ciegas.

```bash
python scripts/callejero.py                  # barrido completo (~15 min)
python scripts/callejero.py --desde 28 --hasta 28
python scripts/callejero.py --control        # solo contrasta, no consulta
```

## El control

La tabla anterior (3.291 CP sacados de los puntos de recarga de la DGT, con municipio
cruzado por código) se usa como **testigo**: cada CP que ya teníamos tiene que
aparecer en la nueva con el **mismo código INE**, sea como principal o como secundario.
Si discrepa, la salida lo dice y `validar.py` falla. Este control es lo que permitió
detectar el error del «primer municipio»: con el modelo de recuento, Madrid pasó de
23 discrepancias a **0**.
