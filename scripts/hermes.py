# -*- coding: utf-8 -*-
"""Descarga capas del visor Hermes (MITMA) como GeoJSON, con recibo.

ArcGIS REST admite f=geojson en 10.9. Se pagina con resultOffset/resultRecordCount.
"""
import json
import os
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; OpenInfraES/1.0)"}
BASE = "https://mapas.fomento.gob.es/arcgis/rest/services/"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos", "hermes")

CAPAS = [
    ("carreteras", "Hermes/0__CARRETERAS", 0, "Red de carreteras del Estado"),
    ("puertos-interes-general", "Hermes/0__PUERTOS", 1, "Puertos de interés general"),
    ("terminales-portuarias", "Hermes/0__PUERTOS", 3, "Terminales portuarias"),
    ("terminales-aeropuerto", "Hermes/0__AEROPUERTOS", 1, "Terminales de pasajeros"),
    ("pistas-aeropuerto", "Hermes/0__AEROPUERTOS", 2, "Pistas de aterrizaje"),
    ("terminales-mercancias", "Hermes/0__TERMINALES_INTERMODALES", 1, "Terminales intermodales de mercancías"),
    ("estaciones-gas", "Hermes/7__COMBUSTIBLES_ALTERNATIVOS", 457, "Estaciones de servicio con GNL"),
]


def bajar(srv, lid, campos="*"):
    salida, offset, total = [], 0, None
    while True:
        params = {"where": "1=1", "outFields": campos, "returnGeometry": "true",
                  "outSR": "4326", "f": "geojson", "resultRecordCount": 1000}
        if offset:
            params["resultOffset"] = offset
        q = urllib.parse.urlencode(params)
        url = "%s%s/MapServer/%d/query?%s" % (BASE, srv, lid, q)
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read().decode("utf-8"))
        if "error" in d:
            raise RuntimeError(d["error"].get("message", "error ArcGIS"))
        feats = d.get("features", [])
        salida.extend(feats)
        if total is None:
            total = d.get("totalFeatures") or d.get("properties", {}).get("exceededTransferLimit")
        if len(feats) < 1000:
            break
        offset += len(feats)
        time.sleep(0.3)
        if offset > 60000:
            break
    return salida


os.makedirs(DEST, exist_ok=True)
recibo = {"fuente": "Visor Hermes — MITMA (mapas.fomento.gob.es)", "licencia": "CC-BY-4.0 (scne.es)",
          "servicio": BASE, "capas": []}

for nombre, srv, lid, desc in CAPAS:
    try:
        feats = bajar(srv, lid)
    except Exception as e:
        print("  %-26s ERROR %s" % (nombre, e))
        continue
    gj = {"type": "FeatureCollection", "features": feats}
    ruta = os.path.join(DEST, nombre + ".geojson")
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(gj, fh, ensure_ascii=False)
    prop0 = list(feats[0]["properties"].keys())[:6] if feats else []
    recibo["capas"].append({"id": nombre, "descripcion": desc, "servicio": srv, "layer": lid,
                            "features": len(feats), "props": prop0})
    print("  %-26s %5d features  %7.0f KB  props=%s" % (nombre, len(feats),
          os.path.getsize(ruta) / 1024, prop0[:4]))

with open(os.path.join(DEST, "_recibo_hermes.json"), "w", encoding="utf-8") as fh:
    json.dump(recibo, fh, ensure_ascii=False, indent=1)
print("\nrecibo: datos/hermes/_recibo_hermes.json")
