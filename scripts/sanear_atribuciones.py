# -*- coding: utf-8 -*-
"""Sanea los textos de atribución que quedaron dentro de los GeoJSON.

Al vectorizar, cada feature llevaba un campo `geo_fuente` o `atribucion` que nombraba al
agregador. El dato es del organismo; el nombre del intermediario no debe aparecer en la
ficha del visor.
"""
import json
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
carpetas = [os.path.join(RAIZ, "datos", "oficial"), os.path.join(RAIZ, "datos", "simplificado")]

SUSTITUCIONES = [
    (r"simplificad[oa] por el atlas con una tolerancia de (\d+) m",
     r"simplificado con una tolerancia de \1 m"),
    (r"\s*·\s*Atlas Estratégico de España", ""),
    (r"\s*·\s*Atlas Estratégico", ""),
    (r"Atlas Estratégico de España", "vectorización de la fuente oficial"),
    (r"Atlas Estratégico", "vectorización de la fuente oficial"),
    (r"por el atlas", "en la vectorización"),
    (r"el atlas", "la vectorización"),
    (r"este atlas no ha comprobado", "no se ha comprobado"),
    (r"este atlas", "este repositorio"),
    (r"que el atlas", "que la vectorización"),
]


def limpiar(txt):
    for pat, rep in SUSTITUCIONES:
        txt = re.sub(pat, rep, txt, flags=re.I)
    return txt


total = 0
for carpeta in carpetas:
    if not os.path.isdir(carpeta):
        continue
    for f in os.listdir(carpeta):
        if not f.endswith(".geojson"):
            continue
        ruta = os.path.join(carpeta, f)
        d = json.load(open(ruta, encoding="utf-8"))
        cambios = 0
        for feat in d.get("features", []):
            props = feat.get("properties") or {}
            for k, v in list(props.items()):
                if isinstance(v, str):
                    nv = limpiar(v)
                    if nv != v:
                        props[k] = nv
                        cambios += 1
        if cambios:
            json.dump(d, open(ruta, "w", encoding="utf-8"), ensure_ascii=False)
            print("  %-42s %4d textos" % (f, cambios))
            total += cambios

print("\n  %d textos saneados" % total)
