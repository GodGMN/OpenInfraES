# -*- coding: utf-8 -*-
"""Terremotos recientes en el entorno de España (EMSC-CSEM, sin clave).

Fuente: https://www.seismicportal.eu/fdsnws/event/1/query (FDSN, JSON)
Cubre la Península, Baleares y Canarias con un bbox amplio.

Salida: datos/sismos.geojson
"""
import json
import urllib.parse
import urllib.request
from datetime import date, timedelta

UA = {"User-Agent": "OpenInfraES/1.0", "Accept": "application/json"}
DEST = "C:/Users/d_ant/Projects/OpenInfraES/datos/sismos.geojson"
DIAS = 7

# bbox: Canarias por el oeste/sur, Pirineos y Baleares por el norte/este
PARAMS = {
    "format": "json", "limit": 600,
    "minlatitude": 27.0, "maxlatitude": 44.5,
    "minlongitude": -19.5, "maxlongitude": 5.0,
    "orderby": "time",
}


def main():
    ini = (date.today() - timedelta(days=DIAS)).isoformat()
    params = dict(PARAMS, starttime=ini)
    url = "https://www.seismicportal.eu/fdsnws/event/1/query?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read().decode("utf-8"))

    feats = []
    for f in d.get("features", []):
        p = f.get("properties", {}) or {}
        coords = f.get("geometry", {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        feats.append({
            "type": "Feature",
            "properties": {
                "magnitud": p.get("mag"),
                "tipo_magnitud": p.get("magtype"),
                "profundidad_km": coords[2] if len(coords) > 2 else None,
                "lugar": (p.get("flynn_region") or p.get("place") or "").strip() or None,
                "hora": p.get("time"),
                "region": p.get("flynn_region"),
                "fuente": "EMSC-CSEM (seismicportal.eu)",
                "id_evento": f.get("id"),
            },
            "geometry": {"type": "Point", "coordinates": [coords[0], coords[1]]},
        })

    feats.sort(key=lambda x: (x["properties"].get("hora") or ""), reverse=True)
    json.dump({"type": "FeatureCollection", "features": feats},
              open(DEST, "w", encoding="utf-8"), ensure_ascii=False)

    mags = [f["properties"]["magnitud"] for f in feats if f["properties"]["magnitud"] is not None]
    recibo = {"features": len(feats), "dias": DIAS, "desde": ini,
              "mag_max": max(mags) if mags else None,
              "mag_media": round(sum(mags) / len(mags), 2) if mags else None,
              "fuente": "EMSC-CSEM", "fichero": "sismos.geojson"}
    json.dump(recibo, open(DEST.replace(".geojson", "_recibo.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("  sismos en %d días: %d · magnitud máx %s · media %s" % (
        DIAS, len(feats), recibo["mag_max"], recibo["mag_media"]))
    for f in feats[:6]:
        p = f["properties"]
        print("   M%-4s %-38s %s" % (p["magnitud"], str(p["lugar"])[:38], str(p["hora"])[:16]))


if __name__ == "__main__":
    main()
