#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Descarga los GeoJSON de red y plantas de Espana y deja recibo en datos/_procedencia.json."""
import json
import os
import urllib.request
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
UA = {"User-Agent": "OpenInfraES/1.0 (datos abiertos red electrica)"}
BASE = "https://raw.githubusercontent.com/ningunaparte/spain-power-plants/main/data/"

FICHEROS = {
    "lineas_hv.geojson": "powerlines_hv_2026-05-14.geojson",
    "plantas.geojson": "plants_commercial_2026-05-19.geojson",
}


def main():
    os.makedirs(DATOS, exist_ok=True)
    proc = {"capturado": datetime.now(timezone.utc).isoformat(), "fuente": "spain-power-plants (OSM + REE/ELECTRA)", "ficheros": []}
    for local, remoto in FICHEROS.items():
        url = BASE + remoto
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=240) as r:
            cuerpo = r.read()
            estado = r.status
        ruta = os.path.join(DATOS, local)
        with open(ruta, "wb") as fh:
            fh.write(cuerpo)
        try:
            feats = len(json.loads(cuerpo.decode("utf-8")).get("features", []))
        except Exception:
            feats = 0
        proc["ficheros"].append({"fichero": local, "url": url, "http": estado,
                                 "bytes": len(cuerpo), "features": feats})
        print("  %-20s %9d bytes  %5d features  HTTP %s" % (local, len(cuerpo), feats, estado))

    with open(os.path.join(DATOS, "_procedencia.json"), "w", encoding="utf-8") as fh:
        json.dump(proc, fh, ensure_ascii=False, indent=1)
    print("Recibo: datos/_procedencia.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
