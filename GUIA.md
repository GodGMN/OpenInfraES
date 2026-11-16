---
titulo: Guía de trabajo — OpenInfraES
fecha: 2026-11-16
---

# GUIA.md

Reglas del repositorio. Breves y obligatorias.

## Qué es esto

Datos de infraestructura eléctrica española, abiertos y reutilizables. **No es un visor de
OpenInfraMap**: es una copia de trabajo con los datos normalizados, agregados y verificados.

## Reglas

1. **Los GeoJSON no se editan a mano.** Se regeneran con `scripts/descargar.py`. Si un dato está mal,
   se corrige en OSM o en la fuente, no en el fichero.
2. **Cada agregado lleva su verificación.** `scripts/agregar.py` falla si los conteos no cuadran con lo
   declarado por la fuente; `scripts/validar.py` falla si los CSV no cuadran entre sí.
3. **Nada de datos inventados ni "estimaciones" sin marcar.** Si algo es calculado (p. ej. km por
   haversine), se dice en el README.
4. **Atribución obligatoria.** OSM es ODbL: todo producto derivado debe citar «© colaboradores de
   OpenStreetMap» y compartirse igual.
5. **Toda cifra publicada, con fecha de extracción.** Los ficheros de origen llevan la fecha en el
   nombre; el recibo está en `datos/_procedencia.json`.

## Cómo añadir una capa nueva

1. Descargar a `datos/` con `scripts/descargar.py` (añadir la fuente a `FICHEROS`).
2. Agregar en `scripts/agregar.py` con su verificación de cuadre.
3. Añadir el CSV al README con su cifra y su fuente.
4. Pasar `python scripts/validar.py` (debe salir VERDE).
5. Commit en castellano, describiendo la capa.

## Limitaciones conocidas (no son bugs)

- Solo transporte (220/400 kV), no distribución.
- Longitud física, no de circuito.
- El 49% de los tramos no declara operador en OSM.
- El parque de generación viene de dos registros cruzados al 47% por nombre.

## Rutina

```bash
python scripts/descargar.py && python scripts/agregar.py && python scripts/validar.py
```
