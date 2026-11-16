#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agrega los GeoJSON de red electrica de Espana en CSV reutilizables.

Entrada (datos/): lineas_hv.geojson (OpenStreetMap, via spain-power-plants),
plantas.geojson (REE + ELECTRA/RAIPEE normalizado).
Salida (datos/): agregados por tension, operador, tecnologia y comunidad.

Verifica los conteos declarados por la fuente antes de escribir:
  4.929 segmentos, 1.752 de 400 kV, 3.176 de 220 kV, 5.797 plantas.
"""
import csv
import json
import math
import os
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")


def km_linea(coords):
    """Longitud aproximada (haversine) de una LineString en km."""
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp = p2 - p1
        dl = math.radians(lon2 - lon1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        total += 2 * 6371.0 * math.asin(math.sqrt(a))
    return total


def main():
    lineas = json.load(open(os.path.join(DATOS, "lineas_hv.geojson"), encoding="utf-8"))["features"]
    plantas = json.load(open(os.path.join(DATOS, "plantas.geojson"), encoding="utf-8"))["features"]

    # --- verificacion de conteos de la fuente
    por_tension = defaultdict(int)
    for f in lineas:
        por_tension[f["properties"].get("voltage")] += 1
    error = []
    if len(lineas) != 4929:
        error.append("lineas %d != 4929" % len(lineas))
    if por_tension.get(400000) != 1752:
        error.append("400 kV %d != 1752" % por_tension.get(400000))
    if por_tension.get(220000) != 3176:
        error.append("220 kV %d != 3176" % por_tension.get(220000))
    if len(plantas) != 5797:
        error.append("plantas %d != 5797" % len(plantas))
    if error:
        print("NO CUADRA con la fuente:")
        for e in error:
            print("  x", e)
        return 1

    # --- lineas por tension y tipo
    agg = defaultdict(lambda: [0, 0.0, 0])
    for f in lineas:
        p = f["properties"]
        kv = int(p.get("voltage") or 0)
        tipo = p.get("line_type") or "sin dato"
        circ = p.get("circuits")
        try:
            circ = int(circ) if circ not in (None, "") else 0
        except (TypeError, ValueError):
            circ = 0
        lon = km_linea(f["geometry"]["coordinates"])
        a = agg[(kv, tipo)]
        a[0] += 1
        a[1] += lon
        a[2] += circ

    with open(os.path.join(DATOS, "agregado_lineas.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["tension_kv", "tipo", "segmentos", "km", "circuitos_declarados"])
        for (kv, tipo), (n, lon, circ) in sorted(agg.items(), key=lambda x: (-x[0][0], x[0][1])):
            w.writerow([kv, tipo, n, round(lon, 1), circ])

    # --- lineas por operador
    op = defaultdict(lambda: [0, 0.0])
    for f in lineas:
        p = f["properties"]
        nombre = p.get("operator") or "sin operador declarado"
        op[nombre][0] += 1
        op[nombre][1] += km_linea(f["geometry"]["coordinates"])
    with open(os.path.join(DATOS, "agregado_lineas_operador.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["operador", "segmentos", "km"])
        for nombre, (n, lon) in sorted(op.items(), key=lambda x: -x[1][1]):
            w.writerow([nombre, n, round(lon, 1)])

    # --- plantas por tecnologia y comunidad
    tec = defaultdict(lambda: [0, 0.0])
    ccaa = defaultdict(lambda: [0, 0.0])
    ccaa_tec = defaultdict(lambda: [0, 0.0])
    for f in plantas:
        p = f["properties"]
        mw = float(p.get("installed_capacity_mw") or 0)
        t = p.get("technology_normalized") or "sin dato"
        c = p.get("autonomous_region") or "sin dato"
        tec[t][0] += 1
        tec[t][1] += mw
        ccaa[c][0] += 1
        ccaa[c][1] += mw
        ccaa_tec[(c, t)][0] += 1
        ccaa_tec[(c, t)][1] += mw

    with open(os.path.join(DATOS, "agregado_plantas_tecnologia.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["tecnologia", "plantas", "mw"])
        for t, (n, mw) in sorted(tec.items(), key=lambda x: -x[1][1]):
            w.writerow([t, n, round(mw, 1)])

    with open(os.path.join(DATOS, "agregado_plantas_ccaa.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["comunidad", "plantas", "mw"])
        for c, (n, mw) in sorted(ccaa.items(), key=lambda x: -x[1][1]):
            w.writerow([c, n, round(mw, 1)])

    with open(os.path.join(DATOS, "agregado_plantas_ccaa_tecnologia.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["comunidad", "tecnologia", "plantas", "mw"])
        for (c, t), (n, mw) in sorted(ccaa_tec.items(), key=lambda x: (x[0][0], -x[1][1])):
            w.writerow([c, t, n, round(mw, 1)])

    km_total = sum(v[1] for v in agg.values())
    mw_total = sum(v[1] for v in tec.values())
    print("CUADRA con la fuente:")
    print("  segmentos ......... %d (400 kV: %d, 220 kV: %d)" % (len(lineas), por_tension[400000], por_tension[220000]))
    print("  km (haversine) .... %.0f km" % km_total)
    print("  plantas ............ %d | %.0f MW" % (len(plantas), mw_total))
    print("  tecnologias ........ %d | comunidades: %d" % (len(tec), len(ccaa)))
    print("  CSV escritos en datos/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
