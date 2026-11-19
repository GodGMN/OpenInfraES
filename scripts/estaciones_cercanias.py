# -*- coding: utf-8 -*-
"""Estaciones de Cercanías desde data.renfe.com (CKAN abierto, sin clave).

El NAP de transporte (nap.transportes.gob.es) exige API key; su catálogo CKAN responde
«Api Key was not provided». Pero data.renfe.com sí es abierto y publica un paquete
`estaciones-cercanias-<nucleo>` por cada núcleo, con CSV de lat/lon.

Salida: datos/estaciones-cercanias.geojson
"""
import os
import csv
import io
import json
import urllib.request

UA = {"User-Agent": "OpenInfraES/1.0 (datos abiertos)"}
API = "https://data.renfe.com/api/3/action/"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos", "estaciones-cercanias.geojson")


def get(url, crudo=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read()
    return data if crudo else json.loads(data.decode("utf-8"))


def main():
    lista = get(API + "package_list")["result"]
    paquetes = [p for p in lista if p.startswith("estaciones-cercanias")]
    print("  paquetes de estaciones: %d" % len(paquetes))

    feats, nucleos, sin_coord = [], [], 0
    for pid in paquetes:
        try:
            pk = get(API + "package_show?id=" + pid)["result"]
        except Exception as e:
            print("    %-34s ERROR %s" % (pid, type(e).__name__))
            continue
        nucleo = pid.replace("estaciones-cercanias-", "")
        recursos = [r for r in pk.get("resources", []) if (r.get("format") or "").upper() == "CSV"]
        if not recursos:
            continue
        try:
            txt = get(recursos[0]["url"], crudo=True).decode("utf-8-sig", errors="replace")
        except Exception as e:
            print("    %-34s CSV ERROR %s" % (pid, type(e).__name__))
            continue
        # el separador cambia según el fichero
        muestra = txt[:2000]
        sep = ";" if muestra.count(";") > muestra.count(",") else ","
        filas = list(csv.DictReader(io.StringIO(txt), delimiter=sep))
        if not filas:
            continue
        cols = {c.lower().strip(): c for c in filas[0].keys()}
        c_lat = next((cols[k] for k in cols if "latitud" in k or k == "lat"), None)
        c_lon = next((cols[k] for k in cols if "longitud" in k or k in ("lon", "lng")), None)
        c_nom = next((cols[k] for k in cols if "nombre" in k or "estacion" in k or "parada" in k), None)
        n = 0
        for f in filas:
            try:
                lat = float(str(f.get(c_lat, "")).replace(",", "."))
                lon = float(str(f.get(c_lon, "")).replace(",", "."))
            except (TypeError, ValueError):
                sin_coord += 1
                continue
            if not (-90 < lat < 90 and -20 < lon < 10):
                sin_coord += 1
                continue
            feats.append({
                "type": "Feature",
                "properties": {
                    "nombre": (f.get(c_nom) or "").strip() if c_nom else None,
                    "nucleo": nucleo,
                    "fuente": "data.renfe.com (CKAN)",
                    "url_dataset": "https://data.renfe.com/dataset/" + pid,
                },
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
            })
            n += 1
        nucleos.append({"nucleo": nucleo, "estaciones": n})
        print("    %-30s %4d estaciones" % (nucleo, n))

    json.dump({"type": "FeatureCollection", "features": feats},
              open(DEST, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"features": len(feats), "nucleos": nucleos, "sin_coordenada": sin_coord,
               "fuente": "data.renfe.com (CKAN abierto)",
               "fichero": "estaciones-cercanias.geojson"},
              open(DEST.replace(".geojson", "_recibo.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n  TOTAL %d estaciones en %d núcleos (%d filas sin coordenada válida)"
          % (len(feats), len(nucleos), sin_coord))


if __name__ == "__main__":
    main()
