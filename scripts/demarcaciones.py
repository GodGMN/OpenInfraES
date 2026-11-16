# -*- coding: utf-8 -*-
"""Demarcaciones hidrográficas del MITECO.

Es el dato que cuelga de cada presa y embalse: la presa dice a qué demarcación pertenece, y la
demarcación es la unidad de gestión (confederación). Servicio ArcGIS REST abierto, sin clave.

    python scripts/demarcaciones.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from http_oficial import pide

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos")
BASE = ("https://sig.miteco.gob.es/arcgis/rest/services/25830/"
        "aguaHidroDemarcaciones/MapServer/2/query")


def main():
    d = pide(BASE + "?where=1%3D1&outFields=*&returnGeometry=true&outSR=4326"
             "&f=geojson&maxAllowableOffset=0.0005",
             vacio_si=("features",))

    feats = d.get("features", [])
    # limpia propiedades vacias y normaliza el nombre
    for f in feats:
        p = f.get("properties") or {}
        f["properties"] = {k: v for k, v in p.items() if v not in (None, "", " ")}

    ruta = os.path.join(DEST, "demarcaciones.geojson")
    json.dump(d, open(ruta, "w", encoding="utf-8"), ensure_ascii=False)

    nombres = []
    for f in feats:
        p = f["properties"]
        for k in p:
            if any(t in k.lower() for t in ("nom", "name", "demarc")):
                nombres.append(str(p[k]))
                break

    recibo = {
        "fuente": "MITECO",
        "servicio": "sig.miteco.gob.es · aguaHidroDemarcaciones · capa 2",
        "url": BASE,
        "licencia": "Reutilización con atribución (Ley 37/2007)",
        "features": len(feats),
        "tamano_kb": round(os.path.getsize(ruta) / 1024, 1),
        "nombres": sorted(set(nombres))[:25],
    }
    json.dump(recibo, open(os.path.join(DEST, "demarcaciones_recibo.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)

    print("  %d demarcaciones · %s KB" % (len(feats), recibo["tamano_kb"]))
    for n in recibo["nombres"]:
        print("   ", n)


if __name__ == "__main__":
    main()
