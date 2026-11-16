# -*- coding: utf-8 -*-
"""Conducciones de agua en OSM: solo las que tienen nombre (trasvases y aducciones principales).

Sin filtro de nombre la consulta devuelve decenas de miles de tramos y el servidor la corta;
con nombre quedan las infraestructuras que importan (Tajo-Segura, Ebro, etc.).
"""
import json
import time
import urllib.parse
import urllib.request

ESPEJOS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
UA = {"User-Agent": "OpenInfraES/1.0 (datos abiertos)"}
DEST = "C:/Users/d_ant/Projects/OpenInfraES/datos"

Q = """[out:json][timeout:240];
area["ISO3166-1"="ES"][admin_level=2]->.a;
(
  way["man_made"="pipeline"]["substance"="water"]["name"](area.a);
  relation["man_made"="pipeline"]["substance"="water"]["name"](area.a);
  way["man_made"="canal"]["name"](area.a);
  way["waterway"="canal"]["name"](area.a);
);
out geom tags;"""


def overpass(q):
    ultimo = None
    for url in ESPEJOS:
        for intento in range(2):
            try:
                datos = urllib.parse.urlencode({"data": q}).encode()
                req = urllib.request.Request(url, data=datos, headers=UA)
                with urllib.request.urlopen(req, timeout=300) as r:
                    return json.loads(r.read().decode("utf-8"))
            except Exception as e:
                ultimo = "%s: %s" % (url.split("/")[2], type(e).__name__)
                time.sleep(3 * (intento + 1))
    raise RuntimeError(ultimo)


d = overpass(Q)
feats = []
for el in d.get("elements", []):
    t = el.get("tags", {})
    props = {k: v for k, v in t.items() if k in (
        "name", "operator", "ref", "substance", "waterway", "man_made", "canal", "usage",
        "diameter", "wikipedia", "wikidata", "start_date")}
    props["osm_id"] = el["id"]
    props["osm_tipo"] = el["type"]
    if el["type"] == "way" and el.get("geometry"):
        geom = {"type": "LineString", "coordinates": [[p["lon"], p["lat"]] for p in el["geometry"] if p]}
    elif el.get("members"):
        lineas = []
        for m in el["members"]:
            if m.get("geometry"):
                lineas.append([[p["lon"], p["lat"]] for p in m["geometry"] if p])
        if not lineas:
            continue
        geom = {"type": "MultiLineString", "coordinates": lineas}
    else:
        continue
    feats.append({"type": "Feature", "properties": props, "geometry": geom})

gj = {"type": "FeatureCollection", "features": feats}
json.dump(gj, open(DEST + "/agua-conducciones.geojson", "w", encoding="utf-8"), ensure_ascii=False)

nombres = sorted({f["properties"].get("name") for f in feats if f["properties"].get("name")})
print("%d tramos, %d nombres distintos" % (len(feats), len(nombres)))
for n in nombres[:28]:
    print("   ", n)

# completar el recibo sin perder EDAR/ETAP
recibo = json.load(open(DEST + "/osm_agua_recibo.json", encoding="utf-8"))
recibo["agua-conducciones"] = {"features": len(feats), "con_nombre": len(feats),
                               "nombres": len(nombres)}
json.dump(recibo, open(DEST + "/osm_agua_recibo.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nrecibo actualizado")
