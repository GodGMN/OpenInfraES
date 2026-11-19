# -*- coding: utf-8 -*-
"""Red ferroviaria física de Adif: la vía, no el servicio.

Fuente F1 de la auditoría v2. El WFS de IDEADIF responde **403** (Akamai), confirmado dos veces y
también desde otro repo propio, así que no se insiste. El trazado oficial ya estaba descargado en
`era-visor/data/adif-tramos.geojson`: 1.178 tramos, 604.913 vértices, 16,5 MB.

Aquí se simplifica para el visor y se colorea por uso. Lo que aporta frente a lo que ya había:
el repo tenía ferrocarril **de servicio** (GTFS de Cercanías y Metro); esto es la **infraestructura**:
qué vía existe, de quién es el titular y para qué se usa.

    python scripts/adif.py --origen <ruta>/adif-tramos.geojson

La simplificación es Douglas-Peucker con tolerancia en grados (~0,0004 ≈ 40 m). No se usa shapely
porque no está instalado y para decimar líneas no hace falta.
"""
import argparse
import datetime
import json
import math
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")

# color por uso de la red: es lo que hace legible el mapa, no la longitud del tramo
COLOR = {
    "Uso principal Alta Vel.": ("#7c3aed", "Alta velocidad"),
    "Uso resto viaj. Interciud": ("#38bdf8", "Interciudad"),
    "N.Cercanías >= 80 cir/día": ("#22c55e", "Cercanías ≥80 cir/día"),
    "N.Cercanías < 80 cir/día": ("#86efac", "Cercanías <80 cir/día"),
    "Uso mercancías": ("#f59e0b", "Mercancías"),
    "Resto": ("#94a3b8", "Resto"),
    "Uso exclusivo Alta Vel.": ("#a78bfa", "Alta velocidad (exclusivo)"),
    "N.Cercanías": ("#4ade80", "Cercanías"),
    "Vía única": ("#94a3b8", "Vía única"),
}
OTRO = ("#64748b", "Otro uso")


def perp(p, a, b):
    """Distancia de p al segmento ab, en grados (aproximación plana)."""
    (x, y), (x1, y1), (x2, y2) = p, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


def douglas(pts, tol):
    """Douglas-Peucker iterativo (una línea de 600.000 puntos desborda la recursión)."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    pila = [(0, len(pts) - 1)]
    while pila:
        i, j = pila.pop()
        if j <= i + 1:
            continue
        mejor, idx = 0.0, i
        for k in range(i + 1, j):
            d = perp(pts[k], pts[i], pts[j])
            if d > mejor:
                mejor, idx = d, k
        if mejor > tol:
            keep[idx] = True
            pila.append((i, idx))
            pila.append((idx, j))
    return [p for p, k in zip(pts, keep) if k]


def limpia(props):
    """Solo lo que se va a mostrar o filtrar. Los campos vacíos no viajan."""
    salida = {}
    for k in ("codtramo", "cod_eje", "cod_linea", "provincia", "tipo_red",
              "cod_tipo_r", "cod_titula", "cod_nucleo"):
        v = props.get(k)
        if v not in (None, "", "NULL"):
            salida[k] = v.strip() if isinstance(v, str) else v
    # nombre corto para la ficha y la leyenda
    if salida.get("tipo_red"):
        color, etiqueta = COLOR.get(salida["tipo_red"], OTRO)
        salida["color_uso"] = color
        salida["uso"] = etiqueta
    return salida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origen", required=True, help="GeoJSON de tramos de Adif")
    ap.add_argument("--tol", type=float, default=0.0004, help="tolerancia en grados")
    a = ap.parse_args()

    d = json.load(open(a.origen, encoding="utf-8"))
    feats = d.get("features", [])
    print("  origen: %d tramos" % len(feats))

    salida, viejos, nuevos = [], 0, 0
    for f in feats:
        g = f.get("geometry") or {}
        if g.get("type") not in ("LineString", "MultiLineString"):
            continue
        lineas = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        partes = []
        for lin in lineas:
            viejos += len(lin)
            s = douglas([tuple(c[:2]) for c in lin], a.tol)
            nuevos += len(s)
            if len(s) >= 2:
                partes.append([[round(x, 5), round(y, 5)] for x, y in s])
        if not partes:
            continue
        salida.append({
            "type": "Feature",
            "geometry": ({"type": "LineString", "coordinates": partes[0]} if len(partes) == 1
                         else {"type": "MultiLineString", "coordinates": partes}),
            "properties": limpia(f.get("properties") or {}),
        })

    destino = os.path.join(DATOS, "adif_tramos.geojson")
    json.dump({"type": "FeatureCollection", "features": salida},
              open(destino, "w", encoding="utf-8"), ensure_ascii=False)

    json.dump({"capa": "adif-tramos", "features": len(salida),
               "vertices": nuevos, "vertices_origen": viejos,
               "descargado": datetime.date.today().isoformat(),
               "tolerancia_grados": a.tol},
              open(os.path.join(DATOS, "adif_tramos_recibo.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    mb = os.path.getsize(destino) / 1e6
    print("  %d tramos · %d → %d vértices (%.0f%% menos)" % (
        len(salida), viejos, nuevos, 100 * (1 - nuevos / max(viejos, 1))))
    print("  %.2f MB -> datos/adif_tramos.geojson" % mb)

    usos = {}
    for f in salida:
        u = (f["properties"].get("uso") or "Otro uso")
        usos[u] = usos.get(u, 0) + 1
    for u, n in sorted(usos.items(), key=lambda x: -x[1]):
        print("   %-28s %4d" % (u, n))


if __name__ == "__main__":
    main()