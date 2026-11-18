# Precio de la electricidad: OMIE y ENTSO-E dicen lo mismo

Dos fuentes independientes del mismo número, y una trampa de formato que cuesta una cifra falsa.

## OMIE · mercado diario

`scripts/omie.py` · sin clave.

```
https://www.omie.es/es/file-download?parents%5B0%5D=marginalpdbc&filename=marginalpdbc_YYYYMMDD.1
```

CSV con **96 filas por día**. Aquí está la trampa: **las 96 filas no son horas, son cuartos de hora**.

| Campo | Significado |
|---|---|
| 1-3 | año, mes, día |
| **4** | **índice del cuarto de hora, 1-96** |
| 5 | precio España (€/MWh) |
| 6 | precio Portugal (€/MWh) |

Leer la columna 4 como «hora» da una media de 1,39 €/MWh en un día cuya media real era **52,13**.
El mercado diario español pasó a **resolución de 15 minutos**, y el CSV lo refleja.

Conversión: `hora = (cuarto - 1) // 4 + 1` · `minuto = ((cuarto - 1) % 4) * 15`.

### 2026-11-18

| | |
|---|---|
| Cuartos | 96 |
| Media | **52,13 €/MWh** |
| Mínimo | **0,00** a las 03:30 |
| Máximo | **150,00** a las 22:00 |

## ENTSO-E A44 · la verificación

`scripts/entsoe.py --precio YYYY-MM-DD` · requiere `ENTSOE_TOKEN`.

El mismo precio, en XML, con `<price.amount>` en lugar de `<quantity>` y resolución **PT15M**.
Sirve para **comprobar** el CSV de OMIE, y la comprobación sale limpia:

> **78 de 78 cuartos coinciden al céntimo.**

ENTSO-E publicó **78 de las 96** posiciones ese día (faltaban las 12-24 y 51-56). Por eso su
media sale 63,07 y la de OMIE 52,13: **le faltan justo las horas baratas**. Una media calculada
sobre un subconjunto no es la media del día — comparar medias entre las dos fuentes es un error,
comparar cuarto a cuarto es la prueba.


### Por qué el error era creíble

Cortar las 96 filas en cuatro grupos de 24 da cuatro medias que **parecen** cuatro mercados,
porque cada grupo es una franja horaria con su propio nivel de precio:

| Cuartos | Franja | Media |
|---|---|---:|
| 1-24 | 01:00 – 06:45 | **1,39** |
| 25-48 | 07:00 – 12:45 | 46,26 |
| 49-72 | 13:00 – 18:45 | 50,40 |
| 73-96 | 19:00 – 00:45 | **110,48** |

La primera franja es la madrugada, con precio casi cero. Por eso «media 1,39» no chirriaba:
era un número plausible, solo que de las seis de la mañana. La curva sube a lo largo del día y
el máximo (**150,00 a las 22:00**) cae en la última franja, la más cara. Todo encaja — y por eso
el error pasó desapercibido hasta que ENTSO-E puso el contraste.

**Regla**: si un CSV trae 96 filas donde esperabas 24, sospecha de la resolución antes que de
un formato raro. Un dato plausible puede seguir siendo el dato equivocado.

## Trampas

- **96 filas = 96 cuartos**, no 4 bloques de 24 horas. El campo 4 llega hasta 96.
- **El día empieza a la 01:00** en hora peninsular: el período de ENTSO-E va de `23:00Z` a `23:00Z`.
- **ENTSO-E puede venir incompleto** (78 de 96): nunca reindexar las posiciones, se conservan.
- **Es el precio mayorista**, no el recibo: faltan peajes, cargos e impuestos.

## Ficheros

- `datos/omie_precio.json` — 96 cuartos, con hora y minuto ya calculados.
- `datos/entsoe_precio.json` — el contraste, con las posiciones originales.
