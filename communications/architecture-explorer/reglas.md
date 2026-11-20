### Invariantes (de `GUIA.md` y de los gates del repo)

- **Los GeoJSON no se editan a mano.** Se regeneran con su script. Un dato mal se corrige en la
  fuente o en `scripts/<fuente>.py`, nunca en `datos/`.
- **Cada capa tiene su recibo** (`datos/<capa>_recibo.json`). Sin recibo, `validar.py` falla.
- **Nada inventado ni estimado sin marcar**: lo calculado (haversine, caudal modelado, trazado
  incompleto) se declara en el propio dato y en la ficha.
- **Licencia por capa.** OSM es ODbL; IGN/SCNE, MITMA y MITECO son CC BY 4.0; REE y OMIE tienen
  condiciones propias. Mezclar ODbL con CC BY en un derivado obliga a ODbL para el conjunto.
- **Toda cifra publicada lleva fecha de dato y fecha de descarga**: no son lo mismo.
- **Provincia y CCAA por código oficial**, nunca por nombre (`scripts/normaliza.py`).
- **Credenciales solo en `.env`** (ignorado por git). Nunca en commits, docs ni chat.
- **Los `.geojson` de `datos/` no se sirven con caché eterna**: el visor pide `?v=VER_DATOS`.

### Cómo se añade una capa (6 pasos, en este orden)

1. Script propio en `scripts/<fuente>.py`: descarga, normaliza y escribe su `_recibo.json`.
2. Si trae geometría: añadirla a `scripts/simplificar.py` con su tolerancia.
3. Declarar la fuente en `scripts/fuentes_visor.py` y la cadena en `scripts/cadenas.py`.
4. Añadir la entrada al array `CAPAS` de `index.html` (con `zoomMin` si a escala nacional no aporta).
5. Pasar los gates (abajo).
6. Commit en castellano describiendo la capa y su fuente.

### Verificar antes de dar algo por bueno

```bash
python scripts/cifras.py --check     # la tabla del README cuadra con el dato medido
python scripts/validar.py            # debe terminar en: RESULTADO: VERDE
python -m py_compile scripts/<lo_que_toques>.py
node --check <js>                    # si tocas JS suelto
```

En el navegador: `OpenInfraES.estados()` dice qué capa está cargada y con cuántos features; `bench()`
mide el arrastre. Antes de decir «va más fluido», medir.

### Trampas conocidas

- **`.github/workflows/validar.yml` no ejecuta `validar.py`**: el paso tiene dos comandos en el mismo
  `run:` sin `|`, YAML lo pliega en una línea y `python scripts/validar.py` acaba siendo argumento de
  `cifras.py` (que lo ignora). En cada push solo corre el gate de cifras. *(Pendiente de corregir.)*
- `scripts/validar.py` lleva conteos escritos a mano (`4929`, `1752`, `3176`) que también están en el
  README: si el dato crece, hay que tocar los dos sitios.
- `index.html` es un único fichero de ~2.600 líneas: el estado de una capa (`__cargada`) y el camino
  único `ponerCapa()` son la parte delicada. No añadir un segundo camino para encender capas.
- El repo pesa ~275 MB: no clonar ni copiar en bucle; no abrir `datos/dgt` (98 MB) con un editor.
