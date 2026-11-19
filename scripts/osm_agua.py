# -*- coding: utf-8 -*-
"""Busca EDAR, ETAP y conducciones de agua en OSM (Overpass) y las guarda como GeoJSON.

- EDAR  -> man_made=wastewater_plant
- ETAP  -> man_made=water_works
- agua  -> man_made=pipeline + substance=water (aproximacion a trasvases y aducciones)
"""
import os
import json
import time
import urllib.parse
import urllib.request

ESPEJOS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
UA = {"User-Agent": "OpenInfraES/1.0 (datos abiertos)"}
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos")

CONSULTAS = {
    "edar": """[out:json][timeout:180];
area["ISO3166-1"="ES"][admin_level=2]->.a;
(
  node["man_made"="wastewater_plant"](area.a);
  way["man_made"="wastewater_plant"](area.a);
  relation["man_made"="wastewater_plant"](area.a);
);
out center tags;""",
    "etap": """[out:json][timeout:180];
area["ISO3166-1"="ES"][admin_level=2]->.a;
(
  node["man_made"="water_works"](area.a);
  way["man_made"="water_works"](area.a);
);
out center tags;""",
    "agua-conducciones": """[out:json][timeout:240];
area["ISO3166-1"="ES"][admin_level=2]->.a;
(
  way["man_made"="pipeline"]["substance"="water"](area.a);
);
out geom tags;""",
}


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
                time.sleep(4 * (intento + 1))
    raise RuntimeError(ultimo)


def a_geojson(d):
    feats = []
    for el in d.get("elements", []):
        t = el.get("tags", {})
        props = {k: v for k, v in t.items() if k in (
            "name", "operator", "operator:type", "capacity", "capacity:persons", "design_capacity",
            "start_date", "ref", "substance", "diameter", "pressure", "location", "treatment",
            "addr:city", "addr:province", "wikidata", "wikipedia")}
        props["osm_id"] = el["id"]
        props["osm_tipo"] = el["type"]
        if el["type"] == "node":
            geom = {"type": "Point", "coordinates": [el["lon"], el["lat"]]}
        elif "center" in el:
            geom = {"type": "Point", "coordinates": [el["center"]["lon"], el["center"]["lat"]]}
            props["geometria_original"] = "poligono"
        elif "geometry" in el:
            geom = {"type": "LineString",
                    "coordinates": [[p["lon"], p["lat"]] for p in el["geometry"] if p]}
        else:
            continue
        feats.append({"type": "Feature", "properties": props, "geometry": geom})
    return {"type": "FeatureCollection", "features": feats}


recibo = {}
for nombre, q in CONSULTAS.items():
    try:
        d = overpass(q)
    except Exception as e:
        print("  %-20s ERROR %s" % (nombre, e))
        continue
    gj = a_geojson(d)
    ruta = "%s/%s.geojson" % (DEST, nombre)
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(gj, fh, ensure_ascii=False)
    con_nombre = sum(1 for f in gj["features"] if f["properties"].get("name"))
    recibo[nombre] = {"features": len(gj["features"]), "con_nombre": con_nombre}
    print("  %-20s %5d features (%d con nombre)" % (nombre, len(gj["features"]), con_nombre))

json.dump(recibo, open(DEST + "/osm_agua_recibo.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nrecibo: datos/osm_agua_recibo.json")
