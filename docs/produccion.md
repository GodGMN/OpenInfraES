# Producción: qué existe y qué no

## No existe producción por planta en abierto. Comprobado.

Lo primero que pidió David: «cuánto produce cada planta». **Ese dato no está publicado en España.**
No es que no lo encontráramos: es que el operador no lo sube.

ENTSO-E tiene el documento **A73** (*Actual generation per generation unit*) y REE está dado de alta
como dominio (`10YES-REE------0`). Probado con cuatro variantes de `processType`:

| Variante | Respuesta |
|---|---|
| `processType=A16` | `No matching data found for ACTUAL_GENERATION_OUTPUT_PER_UNIT_R3` |
| `processType=A01` | HTTP 400 |
| `processType=A02` | HTTP 400 |
| sin `processType` | HTTP 400 |

El token es válido —el mismo sirve para A75— y el endpoint existe. **No hay datos para España.**
Para producción por central habría que pedir acceso a ESIOS (`consultasios@ree.es`), que tiene
~2.000 indicadores y no todos abiertos.

## Lo que sí hay: A75, cada 15 minutos

`python scripts/entsoe.py --mix`

23 series por tecnología, resolución **PT15M**. Es el dato más fino que publica REE en abierto.

| Tecnología | 19-11-2026 (medio día) | % |
|---|---:|---:|
| Eólica terrestre | 208,6 GWh | 56,8 |
| Solar fotovoltaica | 51,2 GWh | 13,9 |
| Hidro bombeo | 40,2 GWh | 10,9 |
| Gas natural | 32,2 GWh | 8,8 |
| Nuclear | 16,7 GWh | 4,6 |
| Hidro fluyente | 7,6 GWh | 2,1 |
| Hidro embalse | 7,0 GWh | 1,9 |

**Trampa de unidades**: A75 da **MW medios de cada cuarto**, no energía. Sumar MW y llamarlo MWh
multiplica por 4 la cifra: daba 1.468 GWh para un día de ~700. La conversión es `MW × 0,25 h`.
Con la corrección, medio día son 367 GWh, que cuadra.

Si el día está en curso faltan cuartos: cada tecnología declara cuántos tiene (`cuartos`).

## La estimación por planta, y por qué es una estimación

Con la potencia instalada (5.797 plantas, 126.327 MW) y el **factor de carga** de cada tecnología
del día, se estima lo que produce cada planta:

```
producción_estimada (MWh/día) = potencia_MW × factor_carga × 24
```

Los factores salen de dividir la generación real entre la capacidad instalada:

| Tecnología | Capacidad | Factor de carga |
|---|---:|---:|
| Nuclear | 7.117 MW | **85,5 %** |
| Hidro bombeo | 3.425 MW | 71,1 % |
| Eólica | 31.325 MW | 54,4 % |
| Solar FV | 27.171 MW | 27,9 % |
| Gas (CCGT) | 24.562 MW | 11,4 % |

Ejemplo en la ficha del Parque Eólico Muxía I: *888 MWh/día estimados · 68,0 MW × factor 54,4 %*.

**Y se dice en la ficha que no es una medida.** Una planta concreta puede estar parada, en
mantenimiento o producir el triple que la media de su tecnología. El número sirve para ordenar,
no para facturar.

## Ficheros

- `datos/entsoe_mix.json` — generación por tecnología, 15 min, con capacidad y factor por tecnología.
- `datos/plantas.geojson` — 5.797 plantas con `installed_capacity_mw` y `technology_normalized`.
