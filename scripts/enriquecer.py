#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Encaja cada punto del visor en SU municipio y le hereda la poblacion.

Un embalse esta en un termino municipal: si el municipio tiene codigo INE y padrón,
el embalse tiene que decirlo sin que nadie lo escriba a mano. El encaje es por
GEOMETRIA (punto dentro del poligono oficial) y el resultado es un CODIGO.

    python scripts/enriquecer.py            # todas las capas de puntos declaradas
    python scripts/enriquecer.py --capa embalses

Escribe los campos nuevos dentro de cada GeoJSON y un recibo con el tanto por ciento
encajado por capa. Lo que no encaja se declara: no se le pone municipio «a ojo».
"""
import argparse
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")

CAPAS = {
    "embalses": "simplificado/agua-embalsada.geojson",
    "desaladoras": "oficial/desaladoras.geojson",
    "nuclear": "oficial/nuclear.geojson",
    "edar": "edar.geojson",
    "etap": "etap.geojson",
    "carburantes": "carburantes.geojson",
    "plantas": "plantas.geojson",
    "estaciones-cercanias": "estaciones-cercanias.geojson",
    "dgt-electrolineras": "dgt_electrolineras.geojson",
    "eolicos": "oficial/parques-eolicos.geojson",
    "solares": "oficial/plantas-solares.geojson",
    "regas": "oficial/gas-regasificacion.geojson",
    "gasalm": "oficial/gas-almacenamiento.geojson",
    "refinerias": "oficial/refinerias.geojson",
    "residuos": "oficial/residuos-radiactivos.geojson",
    "petrolifero": "oficial/almacenamiento-petrolifero.geojson",
    "h2red": "oficial/hidrogeno-red.geojson",
    "subestaciones": "oficial/red-electrica.geojson",
}


def carga_municipios():
    d = json.load(open(os.path.join(DATOS, "municipios.geojson"), encoding="utf-8"))
    rejilla = {}
    lista = []
    for f in d["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        x0 = y0 = 1e9
        x1 = y1 = -1e9
        for poly in polys:
            for p in poly[0]:
                x0 = min(x0, p[0]); x1 = max(x1, p[0])
                y0 = min(y0, p[1]); y1 = max(y1, p[1])
        i = len(lista)
        lista.append((x0, y0, x1, y1, polys, f["properties"]))
        cx0, cx1 = int(x0 * 8), int(x1 * 8)
        cy0, cy1 = int(y0 * 8), int(y1 * 8)
        for cxx in range(cx0, cx1 + 1):
            for cyy in range(cy0, cy1 + 1):
                rejilla.setdefault((cxx, cyy), []).append(i)
    return lista, rejilla


def dentro(polys, x, y):
    for poly in polys:
        for anillo_i, anillo in enumerate(poly):
            if anillo_i and not anillo_poly(anillo, x, y):
                continue
        if anillo_poly(poly[0], x, y):
            hueco = False
            for h in poly[1:]:
                if anillo_poly(h, x, y):
                    hueco = True
                    break
            if not hueco:
                return True
    return False


def anillo_poly(pts, x, y):
    c = False
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, yi = pts[i][0], pts[i][1]
        xj, yj = pts[j][0], pts[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-18) + xi):
            c = not c
        j = i
    return c


def encaja(rejilla, lista, x, y):
    cx, cy = int(x * 8), int(y * 8)
    for i in rejilla.get((cx, cy), ()):
        x0, y0, x1, y1, polys, pr = lista[i]
        if x < x0 or x > x1 or y < y0 or y > y1:
            continue
        if dentro(polys, x, y):
            return pr
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capa", help="solo una capa por su id")
    a = ap.parse_args()
    lista, rejilla = carga_municipios()
    print("  %d municipios indexados" % len(lista))
    recibo = {"fuente_municipios": "datos/municipios.geojson (Eurostat GISCO + INE)",
              "metodo": ("punto dentro del polígono municipal oficial; en polígonos y líneas se usa el "
               "centro de su envolvente, declarado como tal"),
              "capas": {}}
    for idc, rel in CAPAS.items():
        if a.capa and a.capa != idc:
            continue
        ruta = os.path.join(DATOS, rel.replace("/", os.sep))
        if not os.path.exists(ruta):
            continue
        d = json.load(open(ruta, encoding="utf-8"))
        ok = total = fuera = 0
        for f in d["features"]:
            g = f.get("geometry") or {}
            if not g.get("coordinates"):
                continue
            total += 1
            if g["type"] == "Point":
                x, y = g["coordinates"][0], g["coordinates"][1]
            else:
                # polígono o línea: se usa el punto medio de su envolvente (declarado en el recibo)
                pts = []
                def saca(c):
                    if isinstance(c[0], (int, float)):
                        pts.append(c)
                    else:
                        for z in c:
                            saca(z)
                saca(g["coordinates"])
                if not pts:
                    continue
                xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
                x, y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            pr = encaja(rejilla, lista, x, y)
            if pr:
                p = f["properties"]
                p["cod_ine_municipio"] = pr.get("cod_ine")
                p["municipio_ine"] = pr.get("nombre")
                p["poblacion_municipio"] = pr.get("poblacion")
                p["anio_poblacion_municipio"] = pr.get("anio_poblacion")
                p["provincia_municipio"] = pr.get("provincia_nombre")
                ok += 1
            else:
                f["properties"]["municipio_ine"] = None
                fuera += 1
        json.dump(d, open(ruta, "w", encoding="utf-8"), ensure_ascii=False)
        pct = 100 * ok / total if total else 0
        recibo["capas"][idc] = {"puntos": total, "encajados": ok, "sin_municipio": fuera,
                                "pct": round(pct, 1)}
        print("  %-22s %5d puntos · %5d encajados (%.1f %%)" % (idc, total, ok, pct))
    json.dump(recibo, open(os.path.join(DATOS, "enriquecimiento_recibo.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
