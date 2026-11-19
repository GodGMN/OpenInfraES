# INE · población por provincia y comunidad

API **Tempus3** del INE, sin clave: `servicios.ine.es/wstempus/js/ES`.

| Tabla | Contenido |
|---|---|
| **2852** | Población por provincias y sexo |
| 2853 | Población por comunidades y ciudades autónomas |

```bash
python scripts/ine.py
```

## Lo que se obtiene

> **47.385.107 habitantes** en España (cifras oficiales del padrón, 2025)

Se cruzan por nombre con los polígonos NUTS3/NUTS2 que ya tiene el visor y se les añade
`poblacion` y una **coropleta por cuartiles** (4 tramos de 12 provincias cada uno).

| Provincia | Habitantes |
|---|---:|
| Madrid | 6.751.251 |
| Barcelona | 5.714.730 |
| València/València | 2.589.312 |
| Sevilla | 1.947.852 |
| Alacant/Alicante | 1.881.762 |

## El cruce de nombres: tres trampas

El INE **no da el código de municipio** en esa tabla, solo el nombre. Hay que cruzar por texto, y
el texto no coincide:

1. **El INE pone el artículo al final**: `Coruña, A` · `Rioja, La` · `Balears, Illes`.
2. **Y el tipo de entidad también**: `Asturias, Principado de` · `Madrid, Comunidad de`.
   La capa escribe `Principado de Asturias` y `Comunidad de Madrid`.
3. **Provincias con dos nombres**: `Alacant/Alicante`, `Castelló/Castellón`, `València/València`.

La solución es comparar **solo las palabras significativas**, quitando artículos, preposiciones y
el ruido institucional (`principado`, `comunidad`, `region`, `foral`, `ciudad`, `autonoma`), y
ordenarlas alfabéticamente:

```
"Asturias, Principado de"  -> {asturias}
"Principado de Asturias"   -> {asturias}
"Alacant/Alicante"         -> {alacant} y {alicante}
```

Resultado: **48 de 48 provincias y 16 de 16 comunidades cruzadas, cero fallos.**

## Validación cruzada

Las dos capas suman **exactamente lo mismo**: 45.042.385 habitantes. Si el cruce hubiera metido
una provincia dos veces o perdido otra, las sumas no cuadrarían.

No llega a los 47.385.107 nacionales porque **faltan 4 provincias** de las 52 en la capa NUTS3
(las islas menores y las ciudades autónomas). Está declarado, no es un error de suma.

## Trampa de caché

El navegador servía el GeoJSON viejo y los colores no aparecían por mucho que se recargara. Se
añadió una constante `VER_DATOS` que se concatena a cada petición de datos:

```js
fetch(c.fichero + "?v=" + VER_DATOS)
```

**Hay que subirla al regenerar los geojson**, o los cambios no llegan.
