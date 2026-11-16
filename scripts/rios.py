# -*- coding: utf-8 -*-
"""Ríos principales de España desde OSM, agrupados por nombre y con punto de aforo.

Para cada río se agrupan sus tramos, se calcula la longitud total y se elige un punto
(el vértice central del tramo más largo) donde consultar el caudal con la API de
Open-Meteo Flood (GloFAS), que no necesita clave.
"""
import json
import math
import time
import urllib.parse
import urllib.request

ESPEJOS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
UA = {"User-Agent": "OpenInfraES/1.0 (datos abiertos; contacto: ntizar)"}
DEST = "C:/Users/d_ant/Projects/OpenInfraES/datos"
MIN_KM = 12          # por debajo de esto es arroyo, no río
MAX_RIOS = 260

Q = """[out:json][timeout:300];
area["ISO3166-1"="ES"][admin_level=2]->.a;
way["waterway"="river"]["name"](area.a);
out geom tags;"""


def overpass(q):
    ultimo = None
    for url in ESPEJOS:
        for intento in range(2):
            try:
                datos = urllib.parse.urlencode({"data": q}).encode()
                req = urllib.request.Request(url, data=datos, headers=UA)
                with urllib.request.urlopen(req, timeout=320) as r:
                    return json.loads(r.read().decode("utf-8"))
            except Exception as e:
                ultimo = "%s: %s" % (url.split("/")[2], type(e).__name__)
                time.sleep(5 * (intento + 1))
    raise RuntimeError(ultimo)


def hav_km(a, b):
    R = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, (a[1], a[0], b[1], b[0]))
    d = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(d))


print("descargando ríos de OSM…")
d = overpass(Q)
print("  %d tramos" % len(d.get("elements", [])))

grupos = {}
for el in d.get("elements", []):
    t = el.get("tags", {})
    nombre = (t.get("name") or "").strip()
    if not nombre or not el.get("geometry"):
        continue
    coords = [[p["lon"], p["lat"]] for p in el["geometry"] if p]
    if len(coords) < 2:
        continue
    g = grupos.setdefault(nombre.lower(), {"nombre": nombre, "tramos": [], "km": 0.0,
                                           "nombres": set(), "props": {}})
    g["tramos"].append(coords)
    g["nombres"].add(nombre)
    g["km"] += sum(hav_km(coords[i], coords[i + 1]) for i in range(len(coords) - 1))
    for k in ("wikidata", "wikipedia"):
        if k in t and k not in g["props"]:
            g["props"][k] = t[k]

rios = sorted(grupos.values(), key=lambda g: -g["km"])
rios = [r for r in rios if r["km"] >= MIN_KM][:MAX_RIOS]
print("  %d ríos de más de %d km" % (len(rios), MIN_KM))

feats = []
for r in rios:
    largo = max(r["tramos"], key=len)          # el tramo con más detalle
    punto = largo[len(largo) // 2]             # punto medio donde consultar el caudal
    feats.append({
        "type": "Feature",
        "properties": {
            "nombre": r["nombre"], "name": r["nombre"],
            "longitud_km": round(r["km"], 1),
            "tramos": len(r["tramos"]),
            "variantes": len(r["nombres"]),
            "punto_aforo": [round(punto[0], 4), round(punto[1], 4)],
            "caudal_api": "Open-Meteo Flood (GloFAS)",
            **r["props"],
        },
        "geometry": {"type": "MultiLineString", "coordinates": r["tramos"]},
    })

json.dump({"type": "FeatureCollection", "features": feats},
          open(DEST + "/rios.geojson", "w", encoding="utf-8"), ensure_ascii=False)
print("\n  top 12 por longitud:")
for f in feats[:12]:
    p = f["properties"]
    print("   %-28s %6.0f km  (%d tramos)" % (p["nombre"][:28], p["longitud_km"], p["tramos"]))
kb = __import__("os").path.getsize(DEST + "/rios.geojson") / 1024
print("\n  -> datos/rios.geojson  (%.0f KB)" % kb)

json.dump({"features": len(feats), "tramos_osm": len(d.get("elements", [])),
           "min_km": MIN_KM, "fichero": "rios.geojson"},
          open(DEST + "/rios_recibo.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
