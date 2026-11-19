# Normalización: provincia y comunidad SIEMPRE por código

Regla del proyecto: **una provincia o una comunidad autónoma nunca se identifica por su nombre.**
El nombre cambia según la fuente y cualquier cruce por texto pierde registros en silencio.

| Fuente | Cómo escribe |
|---|---|
| INE (padrón) | `Coruña, A` · `Rioja, La` · `Asturias, Principado de` |
| Capa I-ReWater | `A Coruña` · `La Rioja` · `Principado de Asturias` |
| OSM | `A Coruña` · `La Rioja` · `Asturias` |
| MITECO | `CANTABRICO OCCIDENTAL` |

Con cuatro grafías para el mismo territorio, cruzar por nombre **funciona hasta que deja de
funcionar**, y cuando falla no avisa: el campo se queda vacío.

## Los campos

`python scripts/normaliza.py` añade a cada polígono:

| Campo | Qué es | Salamanca | Baleares (prov.) | Baleares (CCAA) |
|---|---|---|---|---|
| `cod_ine` | Código INE de 2 dígitos | `37` | `07` | `04` |
| `nuts` | Código NUTS de Eurostat | `ES415` | `ES532` | `ES53` |
| `nombre_oficial` | El nombre del INE | `Salamanca` | `Baleares` | `Baleares` |
| `slug` | Identificador para URL | `salamanca` | `baleares` | `baleares` |

## La trampa que costó un dato corrupto

Los códigos de **provincia** y de **comunidad** no son el mismo sistema, aunque los dos sean de
dos dígitos:

| Territorio | Provincia | CCAA |
|---|---|---|
| Baleares | `07` | `04` |
| Madrid | `28` | `12` |
| Murcia | `30` | `13` |
| Asturias | `33` | `03` |
| Cantabria | `39` | `06` |
| Navarra | `31` | `14` |
| La Rioja | `26` | `16` |

Al principio había **un solo diccionario de excepciones** para las dos capas. Resultado: Baleares
se resolvía al código `07` también en la capa de comunidades, y **Castilla y León y Baleares
compartían código**. Un duplicado así no da error: da dos comunidades con el mismo identificador y
una suma mal.

Ahora hay dos tablas separadas, `EXTRA_PROV` y `EXTRA_CCAA`.

## Estado

```
provincias     48 con código · 0 sin código · 0 repetidos
comunidades    16 con código · 0 sin código · 0 repetidos
```

Las 48 provincias son las que trae la fuente NUTS3; faltan 4 de las 52 (islas menores y ciudades
autónomas), y eso está declarado en el recibo, no maquillado.
