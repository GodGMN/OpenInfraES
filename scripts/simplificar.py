# -*- coding: utf-8 -*-
"""Simplifica geometrias para el visor (Douglas-Peucker, sin dependencias).

Un GeoJSON con 94.000 vertices obliga a Leaflet a redibujar 94.000 puntos en cada
frame de arrastre. A escala nacional (zoom 5-11) la diferencia entre el vertice y su
simplificacion es de metros: no se ve, pero cuesta.

Genera datos/simplificado/<nombre>.geojson y deja un recibo con vertices antes/despues.
"""
import json
import math
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
DEST = os.path.join(DATOS, "simplificado")

# tolerancia en grados: 0.0008 ~ 89 m en el paralelo 40
CAPAS = [
    ("lineas_hv.geojson", 0.0008),
    ("gasoductos.geojson", 0.0008),
    ("atlas/red-electrica.geojson", 0.0003),   # recintos de subestacion: no aplanar el limite
    ("atlas/agua-embalsada.geojson", 0.0),     # puntos: nada que simplificar
    ("atlas/conducciones-combustible.geojson", 0.0008),
    ("atlas/hidrogeno-red.geojson", 0.0008),
    ("agua-conducciones.geojson", 0.0008),
    ("edar.geojson", 0.0),
    ("etap.geojson", 0.0),
    ("rios.geojson", 0.0012),          # ríos: contexto, no la capa protagonista
    ("trasvases-union.geojson", 0.0006),
]


def perp(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


def dp(puntos, tol):
    """Douglas-Peucker iterativo (sin recursion: una linea de 5.000 puntos revienta la pila)."""
    if len(puntos) < 3 or tol <= 0:
        return puntos
    mantener = [False] * len(puntos)
    mantener[0] = mantener[-1] = True
    pila = [(0, len(puntos) - 1)]
    while pila:
        i, j = pila.pop()
        if j - i < 2:
            continue
        dmax, idx = 0.0, i
        for k in range(i + 1, j):
            d = perp(puntos[k], puntos[i], puntos[j])
            if d > dmax:
                dmax, idx = d, k
        if dmax > tol:
            mantener[idx] = True
            pila.append((i, idx))
            pila.append((idx, j))
    return [p for p, m in zip(puntos, mantener) if m]


def simplificar_anillo(anillo, tol):
    if len(anillo) < 4:
        return anillo
    abierto = anillo[:-1] if anillo[0] == anillo[-1] else anillo[:]
    simple = dp(abierto, tol)
    if len(simple) < 3:
        return anillo
    if simple[0] != simple[-1]:
        simple.append(simple[0])          # cerrar el anillo
    return simple


def contar_coords(c):
    if not c:
        return 0
    if isinstance(c[0], (int, float)):
        return 1
    if isinstance(c[0][0], (int, float)):
        return len(c)
    return sum(contar_coords(x) for x in c)


def simplificar_geom(g, tol):
    t, c = g.get("type"), g.get("coordinates")
    if t == "Point" or not c:
        return g
    if t == "LineString":
        return {"type": t, "coordinates": dp([list(p[:2]) for p in c], tol)}
    if t == "MultiLineString":
        return {"type": t, "coordinates": [dp([list(p[:2]) for p in linea], tol) for linea in c]}
    if t == "Polygon":
        return {"type": t, "coordinates": [simplificar_anillo([list(p[:2]) for p in a], tol) for a in c]}
    if t == "MultiPolygon":
        return {"type": t, "coordinates": [[simplificar_anillo([list(p[:2]) for p in a], tol) for a in poly]
                                           for poly in c]}
    return g


def main():
    os.makedirs(DEST, exist_ok=True)
    recibo = {"tolerancia_grados": 0.0008, "nota": "0.0008 grados ~ 89 m en el paralelo 40", "capas": []}
    for rel, tol in CAPAS:
        origen = os.path.join(DATOS, rel)
        if not os.path.exists(origen):
            print("  falta %s" % rel)
            continue
        g = json.load(open(origen, encoding="utf-8"))
        antes = sum(contar_coords(f.get("geometry", {}).get("coordinates")) for f in g["features"])
        feats = []
        for f in g["features"]:
            f = dict(f)
            f["geometry"] = simplificar_geom(f.get("geometry", {}), tol)
            feats.append(f)
        despues = sum(contar_coords(f.get("geometry", {}).get("coordinates")) for f in feats)
        salida = os.path.join(DEST, os.path.basename(rel))
        json.dump({"type": "FeatureCollection", "features": feats},
                  open(salida, "w", encoding="utf-8"), ensure_ascii=False)
        ahorro = 100 * (1 - despues / antes) if antes else 0
        kb = os.path.getsize(salida) / 1024
        recibo["capas"].append({"id": rel, "tolerancia": tol, "features": len(feats),
                                "vertices_antes": antes, "vertices_despues": despues,
                                "ahorro_pct": round(ahorro, 1), "kb": round(kb)})
        print("  %-40s %7d -> %6d vertices  (-%4.1f%%)  %6.0f KB" % (rel, antes, despues, ahorro, kb))
    json.dump(recibo, open(os.path.join(DEST, "_recibo.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    tot_a = sum(c["vertices_antes"] for c in recibo["capas"])
    tot_d = sum(c["vertices_despues"] for c in recibo["capas"])
    print("\n  TOTAL %d -> %d vertices (-%.1f%%)" % (tot_a, tot_d, 100 * (1 - tot_d / tot_a)))


if __name__ == "__main__":
    main()
