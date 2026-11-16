# -*- coding: utf-8 -*-
"""Une los tramos sueltos de cada trasvase en un trazo continuo.

OSM entrega el Tajo-Segura como decenas de segmentos independientes. Aquí se encadenan
por nombre: se toma un segmento y se busca otro cuyo extremo coincida (dentro de una
tolerancia) con el extremo libre; se repite hasta cerrar la cadena. Sin dependencias.
"""
import json
import re

DEST = "C:/Users/d_ant/Projects/OpenInfraES/datos"
TOL = 0.0006          # ~55 m: huecos reales del mapeo (carreteras, sifones)
TOL_HOLGURA = 0.012   # ~1,1 km: segunda pasada, solo dentro del MISMO trasvase (tuneles)


def clave(nombre):
    """Normaliza el nombre para agrupar variantes del mismo trasvase."""
    n = (nombre or "").lower()
    n = re.sub(r"\(.*?\)", " ", n)                 # quita "(margen izquierda)"
    n = re.sub(r"[^a-záéíóúñü ]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    # variantes sin guion: "tajo segura" == "tajo-segura"
    return n


def extremos(linea):
    return linea[0], linea[-1]


def cerca(a, b, tol=TOL):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def encadenar(lineas, tol=TOL):
    """Devuelve una lista de cadenas continuas a partir de segmentos sueltos."""
    pendientes = [list(l) for l in lineas if len(l) >= 2]
    cadenas = []
    while pendientes:
        actual = pendientes.pop(0)
        creciendo = True
        while creciendo and pendientes:
            creciendo = False
            ini, fin = extremos(actual)
            for i, seg in enumerate(pendientes):
                s_ini, s_fin = extremos(seg)
                if cerca(fin, s_ini, tol):       # fin -> ini
                    actual += seg[1:]
                elif cerca(fin, s_fin, tol):     # fin -> fin (invertido)
                    actual += list(reversed(seg))[1:]
                elif cerca(ini, s_fin, tol):     # fin -> ini por delante
                    actual = seg[:-1] + actual
                elif cerca(ini, s_ini, tol):     # invertido por delante
                    actual = list(reversed(seg))[:-1] + actual
                else:
                    continue
                pendientes.pop(i)
                creciendo = True
                break
        cadenas.append(actual)
    return cadenas


def main():
    d = json.load(open(DEST + "/agua-conducciones.geojson", encoding="utf-8"))
    grupos = {}
    for f in d["features"]:
        p = f["properties"] or {}
        nombre = p.get("name") or ""
        if not re.search(r"trasvase", nombre, re.I):
            continue
        g = f["geometry"]
        if g["type"] == "LineString":
            lineas = [g["coordinates"]]
        else:
            lineas = g["coordinates"]
        grupos.setdefault(clave(nombre), {"nombres": set(), "lineas": []})
        grupos[clave(nombre)]["nombres"].add(nombre)
        grupos[clave(nombre)]["lineas"].extend(lineas)

    feats = []
    print("  %-42s %5s %6s %8s" % ("trasvase", "tram", "trazo", "vertices"))
    for k, v in sorted(grupos.items()):
        cadenas = encadenar(v["lineas"], TOL)
        # segunda pasada: dentro del mismo trasvase se admite el hueco de un tunel
        if len(cadenas) > 1:
            cadenas = encadenar(cadenas, TOL_HOLGURA)
        vertices = sum(len(c) for c in cadenas)
        feats.append({
            "type": "Feature",
            "properties": {
                "name": sorted(v["nombres"], key=len)[-1],
                "nombre": sorted(v["nombres"], key=len)[-1],
                "variantes": len(v["nombres"]),
                "tramos_origen": len(v["lineas"]),
                "trazos": len(cadenas),
                "vertices": vertices,
                "tolerancia_m": "%d m (y %d m para tuneles)" % (TOL * 111000, TOL_HOLGURA * 111000),
                "fuente": "OpenStreetMap (ODbL 1.0), tramos unidos por Prometeo/OpenInfraES",
            },
            "geometry": ({"type": "LineString", "coordinates": cadenas[0]}
                         if len(cadenas) == 1 else
                         {"type": "MultiLineString", "coordinates": cadenas}),
        })
        print("  %-42s %5d %6d %8d" % (sorted(v["nombres"], key=len)[-1][:42],
                                       len(v["lineas"]), len(cadenas), vertices))

    gj = {"type": "FeatureCollection", "features": feats}
    json.dump(gj, open(DEST + "/trasvases-union.geojson", "w", encoding="utf-8"), ensure_ascii=False)
    print("\n  %d trasvases, %d trazos (de %d tramos)" % (
        len(feats), sum(f["properties"]["trazos"] for f in feats),
        sum(f["properties"]["tramos_origen"] for f in feats)))
    print("  -> datos/trasvases-union.geojson")


if __name__ == "__main__":
    main()
