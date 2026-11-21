# -*- coding: utf-8 -*-
"""Aeródromos, helipuertos y bases de hidroaviones de España (OurAirports, dominio público).

Fuente: https://davidmegginson.github.io/ourairports-data/airports.csv (CSV global, ~12 MB)
Filtro: iso_country == "ES" y se descartan los cerrados (type == "closed").

Qué aporta y qué NO: es la infraestructura física (pista, helipuerto, aeródromo), no el tráfico.
Los pasajeros y las terminales son del MITMA (capa `terminales-aero`). No se cruzan.

Salida: datos/aeropuertos.geojson + datos/aeropuertos_recibo.json
"""
import csv
import io
import json
import os
import urllib.request
from datetime import date

UA = {"User-Agent": "OpenInfraES/1.0"}
URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos", "aeropuertos.geojson")

# los códigos del origen no se publican crudos: la ficha del visor los enseña traducidos
TIPOS = {
    "large_airport": "Aeropuerto internacional",
    "medium_airport": "Aeropuerto regional",
    "small_airport": "Aeródromo",
    "heliport": "Helipuerto",
    "seaplane_base": "Base de hidroaviones",
    "balloonport": "Campo de globos",
}


def pies_a_metros(ft):
    try:
        return round(float(ft) * 0.3048, 1)
    except (TypeError, ValueError):
        return None


def main():
    req = urllib.request.Request(URL, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        texto = r.read().decode("utf-8")

    feats, cerrados, sin_coords = [], 0, 0
    for fila in csv.DictReader(io.StringIO(texto)):
        if fila.get("iso_country") != "ES":
            continue
        if fila.get("type") == "closed":
            cerrados += 1
            continue
        try:
            lat = float(fila["latitude_deg"])
            lon = float(fila["longitude_deg"])
        except (TypeError, ValueError, KeyError):
            sin_coords += 1
            continue
        tipo = TIPOS.get(fila.get("type"), "Otro")
        feats.append({
            "type": "Feature",
            "properties": {
                "nombre": fila.get("name") or fila.get("ident"),
                "tipo": tipo,
                "iata": (fila.get("iata_code") or "").strip() or None,
                "icao": (fila.get("icao_code") or "").strip() or None,
                "municipio": (fila.get("municipality") or "").strip() or None,
                "region": (fila.get("iso_region") or "").strip() or None,
                "elevacion_m": pies_a_metros(fila.get("elevation_ft")),
                "servicio_programado": "sí" if fila.get("scheduled_service") == "yes" else "no",
                "enlace": (fila.get("home_link") or "").strip() or None,
                "fuente": "OurAirports (dominio público)",
            },
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
        })

    feats.sort(key=lambda f: (f["properties"]["tipo"] != "Aeropuerto internacional",
                              f["properties"]["nombre"] or ""))
    json.dump({"type": "FeatureCollection", "features": feats},
              open(DEST, "w", encoding="utf-8"), ensure_ascii=False)

    por_tipo = {}
    for f in feats:
        por_tipo[f["properties"]["tipo"]] = por_tipo.get(f["properties"]["tipo"], 0) + 1
    recibo = {
        "features": len(feats),
        "por_tipo": por_tipo,
        "con_iata": sum(1 for f in feats if f["properties"]["iata"]),
        "servicio_programado": sum(1 for f in feats if f["properties"]["servicio_programado"] == "sí"),
        "descartados_cerrados": cerrados,
        "descartados_sin_coordenadas": sin_coords,
        "fecha_dato": date.today().isoformat(),
        "fuente": "OurAirports",
        "url": "https://ourairports.com/data/",
        "fichero": "aeropuertos.geojson",
    }
    json.dump(recibo, open(DEST.replace(".geojson", "_recibo.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("  aeropuertos ES: %d (%s)" % (len(feats), ", ".join(
        "%s %d" % (k, v) for k, v in sorted(por_tipo.items(), key=lambda x: -x[1]))))
    print("   con IATA %d · servicio programado %d · cerrados descartados %d"
          % (recibo["con_iata"], recibo["servicio_programado"], cerrados))


if __name__ == "__main__":
    main()
