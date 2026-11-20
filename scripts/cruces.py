#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Propaga el CODIGO de demarcacion a todas las capas que la citan por nombre.

El nombre de la misma demarcacion no coincide entre fuentes: MITECO escribe
«Cuenca Mediterránea Andaluza» en el parte de embalses y «CUENCAS MEDITERRANEAS
ANDALUZAS» en el poligono. Cruzar eso por texto pierde registros en silencio. Aqui se
resuelve UNA vez, se guarda la tabla de alias con su similitud medida, y despues
todo se cruza por `cod_demar`.

    python scripts/cruces.py            # reescribe las capas y su recibo
"""
import difflib
import json
import os
import re
import sys
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
RUTA_ALIAS = os.path.join(DATOS, "alias_demarcaciones.json")

RUIDO = {"de", "del", "la", "el", "los", "las", "y", "e", "en", "las", "a", "con"}


def norm(t):
    t = unicodedata.normalize("NFD", t or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z ]", " ", t)
    return " ".join(p for p in t.split() if p and p not in RUIDO)


def leer(rel):
    p = os.path.join(DATOS, rel.replace("/", os.sep))
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def main():
    dem = leer("demarcaciones.geojson")
    if not dem:
        print("  [X] falta datos/demarcaciones.geojson")
        return 1
    canonicas = {}
    for f in dem["features"]:
        pr = f["properties"]
        cod = pr.get("cod_demar")
        if cod is None:
            continue
        canonicas[str(cod)] = pr.get("nom_demar") or ""
    por_norm = {norm(v): (k, v) for k, v in canonicas.items()}
    print("  demarcaciones oficiales: %d" % len(canonicas))

    alias, medida = {}, {}
    capas = ["simplificado/agua-embalsada.geojson", "oficial/desaladoras.geojson",
             "oficial/hidrogeno-produccion.geojson", "demarcaciones.geojson"]
    sin = []
    for rel in capas:
        d = leer(rel)
        if not d:
            continue
        cambiadas = 0
        for f in d["features"]:
            pr = f["properties"]
            nombre = pr.get("demarcacion") or pr.get("demarcacion_nombre") or pr.get("nom_demar")
            if not nombre:
                continue
            if "cod_demar" in pr:
                cambiadas += 1
                continue
            k = norm(nombre)
            hit = por_norm.get(k)
            via = "exacto"
            if not hit:
                cerca = difflib.get_close_matches(k, list(por_norm), n=1, cutoff=0.72)
                if cerca:
                    hit = por_norm[cerca[0]]
                    ratio = difflib.SequenceMatcher(None, k, cerca[0]).ratio()
                    via = "alias (%.2f)" % ratio
                    medida[nombre] = {"cod_demar": hit[0], "nombre_oficial": hit[1],
                                      "similitud": round(ratio, 3)}
                else:
                    sin.append(nombre)
                    continue
            pr["cod_demar"] = hit[0]
            pr["demarcacion_oficial"] = hit[1]
            alias[nombre] = {"cod_demar": hit[0], "nombre_oficial": hit[1], "cruce": via}
            cambiadas += 1
        json.dump(d, open(os.path.join(DATOS, rel.replace("/", os.sep)), "w", encoding="utf-8"),
                  ensure_ascii=False)
        print("  %-42s %5d/%5d con cod_demar" % (rel, cambiadas, len(d["features"])))

    rec = {"fuente": "MITECO · demarcaciones hidrográficas (datos/demarcaciones.geojson)",
           "demarcaciones": canonicas, "alias": alias, "notas": medida,
           "sin_resolver": sorted(set(sin))}
    json.dump(rec, open(RUTA_ALIAS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("  datos/alias_demarcaciones.json · %d alias" % len(alias))
    if sin:
        print("  [!] sin resolver: %s" % sorted(set(sin)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
