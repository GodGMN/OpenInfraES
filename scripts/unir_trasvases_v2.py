# -*- coding: utf-8 -*-
"""Une los tramos sueltos de cada trasvase en un trazo continuo.

Tres correcciones sobre la primera versión:
1. El paréntesis NO se borra: «Postrasvase (margen izquierda)» y «(margen derecha)» son
   ramales distintos y fusionarlos mezclaba trazados. Ahora va como sufijo.
2. El guion y el espacio son lo mismo: «Tajo-Segura» y «Tajo Segura» sí son el mismo.
3. Se descartan los fragmentos de menos de 0,5 km o 3 vértices: son restos sueltos que
   ensuciaban el mapa sin aportar trazado.

Salida: datos/trasvases-union.geojson + datos/trasvases_recibo.json
"""
import json
import math
import re

DEST = "C:/Users/d_ant/Projects/OpenInfraES/datos"
TOL = 0.0006          # ~55 m: huecos reales del mapeo (carreteras, sifones)
TOL_HOLGURA = 0.003   # ~330 m: segunda pasada dentro del mismo trasvase (túneles)
MIN_KM = 0.5          # por debajo de esto es un fragmento, no un trazo
MIN_VERTICES = 3


def clave(nombre):
    """Normaliza sin perder el ramal: el paréntesis se conserva como sufijo."""
    n = (nombre or "").lower()
    ramal = ""
    m = re.search(r"\((.*?)\)", n)
    if m:
        ramal = " " + m.group(1)
        n = n[:m.start()] + n[m.end():]
    n = n.replace("-", " ")
    n = re.sub(r"[^a-záéíóúñü ]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return (n + ramal).strip()


def hav(a, b):
    R = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, (a[1], a[0], b[1], b[0]))
    x = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def longitud(c):
    return sum(hav(c[i], c[i + 1]) for i in range(len(c) - 1))


def cerca(a, b, tol):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def encadenar(lineas, tol):
    pend = [list(l) for l in lineas if len(l) >= 2]
    cadenas = []
    while pend:
        actual = pend.pop(0)
        creciendo = True
        while creciendo and pend:
            creciendo = False
            ini, fin = actual[0], actual[-1]
            for i, seg in enumerate(pend):
                si, sf = seg[0], seg[-1]
                if cerca(fin, si, tol):
                    actual += seg[1:]
                elif cerca(fin, sf, tol):
                    actual += list(reversed(seg))[1:]
                elif cerca(ini, sf, tol):
                    actual = seg[:-1] + actual
                elif cerca(ini, si, tol):
                    actual = list(reversed(seg))[:-1] + actual
                else:
                    continue
                pend.pop(i)
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
        lineas = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
        k = clave(nombre)
        grupos.setdefault(k, {"nombres": set(), "lineas": [], "descartados": 0})
        grupos[k]["nombres"].add(nombre)
        for l in lineas:
            if len(l) >= 2:
                grupos[k]["lineas"].append(l)

    feats, recibo = [], []
    print("  %-44s %5s %6s %9s %8s" % ("trasvase", "tram", "trazo", "km", "vert"))
    for k, v in sorted(grupos.items()):
        cadenas = encadenar(v["lineas"], TOL)
        if len(cadenas) > 1:
            cadenas = encadenar(cadenas, TOL_HOLGURA)
        # fuera fragmentos
        buenas = [c for c in cadenas if len(c) >= MIN_VERTICES and longitud(c) >= MIN_KM]
        descartados = len(cadenas) - len(buenas)
        if not buenas:
            continue
        km = sum(longitud(c) for c in buenas)
        vert = sum(len(c) for c in buenas)
        nombre = sorted(v["nombres"], key=len)[-1]
        todos = [p for c in buenas for p in c]
        bbox = [round(min(p[0] for p in todos), 3), round(min(p[1] for p in todos), 3),
                round(max(p[0] for p in todos), 3), round(max(p[1] for p in todos), 3)]
        # cobertura: si el nombre promete Tajo-Segura pero el trazado no llega al Segura,
        # se dice en el dato. OSM solo tiene mapeado el tramo alto.
        nota = None
        if "tajo" in nombre.lower() and "segura" in nombre.lower() and bbox[2] < -1.5:
            nota = ("Trazado incompleto en OSM: llega hasta Alarcón (lon %.2f) y no cubre "
                    "el tramo hasta Tous y el Segura. El resto no está mapeado con nombre." % bbox[2])
        feats.append({
            "type": "Feature",
            "properties": {
                "name": nombre, "nombre": nombre,
                "variantes": len(v["nombres"]),
                "tramos_origen": len(v["lineas"]),
                "trazos": len(buenas),
                "fragmentos_descartados": descartados,
                "longitud_km": round(km, 1),
                "bbox": bbox,
                "cobertura": nota or "completa según el nombre",
                "vertices": vert,
                "fuente": "OpenStreetMap (ODbL 1.0), tramos unidos por OpenInfraES",
            },
            "geometry": ({"type": "LineString", "coordinates": buenas[0]} if len(buenas) == 1
                         else {"type": "MultiLineString", "coordinates": buenas}),
        })
        recibo.append({"nombre": nombre, "tramos": len(v["lineas"]), "trazos": len(buenas),
                       "km": round(km, 1), "descartados": descartados})
        print("  %-44s %5d %6d %9.1f %8d" % (nombre[:44], len(v["lineas"]), len(buenas), km, vert))

    json.dump({"type": "FeatureCollection", "features": feats},
              open(DEST + "/trasvases-union.geojson", "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"trasvases": recibo, "tolerancia_m": int(TOL * 111000),
               "tolerancia_holgura_m": int(TOL_HOLGURA * 111000),
               "min_km": MIN_KM, "nota": "fragmentos de menos de 0,5 km descartados"},
              open(DEST + "/trasvases_recibo.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n  %d trasvases · %d trazos (de %d tramos)" % (
        len(feats), sum(f["properties"]["trazos"] for f in feats),
        sum(f["properties"]["tramos_origen"] for f in feats)))


if __name__ == "__main__":
    main()
