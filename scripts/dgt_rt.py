# -*- coding: utf-8 -*-
"""DGT · tráfico en tiempo real (DATEX II).

El NAP de tráfico sí publica datos **en vivo**, y sin clave:

    incidencias   nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml
    paneles       nap.dgt.es/datex2/v3/dgt/VmsPublication/datex2_v37.xml

Cada petición devuelve el estado del instante (5,6 MB y 3,7 MB el 2026-11-16), así que es un
feed: se refresca, no se cachea.

    python scripts/dgt_rt.py --incidencias
"""
import argparse
import datetime
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos")
DGT = os.path.join(DEST, "dgt")
UA = {"User-Agent": "OpenInfraES/1.0", "Accept": "application/xml"}

FEEDS = {
    "incidencias": "https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml",
    "paneles": "https://nap.dgt.es/datex2/v3/dgt/VmsPublication/datex2_v37.xml",
}


def local(tag):
    return tag.split("}")[-1]


def descarga(nombre, forzar=False):
    os.makedirs(DGT, exist_ok=True)
    ruta = os.path.join(DGT, "%s.xml" % nombre)
    if not forzar and os.path.exists(ruta) and os.path.getsize(ruta) > 10000:
        print("  usando copia local: %.1f MB" % (os.path.getsize(ruta) / 1e6))
        return ruta
    req = urllib.request.Request(FEEDS[nombre], headers=UA)
    with urllib.request.urlopen(req, timeout=240) as r, open(ruta, "wb") as f:
        while True:
            trozo = r.read(1 << 20)
            if not trozo:
                break
            f.write(trozo)
    print("  %.1f MB" % (os.path.getsize(ruta) / 1e6))
    return ruta


def texto(el, *nombres):
    for hijo in el.iter():
        if local(hijo.tag) in nombres and (hijo.text or "").strip():
            return hijo.text.strip()
    return None


def incidencias(ruta):
    feats = []
    tipos = {}
    for _, el in ET.iterparse(ruta, events=("end",)):
        if local(el.tag) != "situationRecord":
            continue
        lat = texto(el, "latitude")
        lon = texto(el, "longitude")
        # El tipo NO es el primer hijo (eso da 'situationRecordCreationReference'): esta en
        # los hijos que acaban en *Type, y su texto es el subtipo concreto.
        CAMPOS = ("roadOrCarriagewayOrLaneManagementType", "abnormalTrafficType",
                  "obstructionType", "speedManagementType", "accidentType",
                  "nonWeatherRelatedRoadConditionType", "poorEnvironmentType",
                  "generalInstructionToRoadUsersType", "vehicleObstructionType",
                  "infrastructureDamageType")
        tipo = subtipo = None
        for hijo in el:
            n = local(hijo.tag)
            if n in CAMPOS and (hijo.text or "").strip():
                tipo = n.replace("Type", "")
                subtipo = hijo.text.strip()
                break
        if not tipo:
            nombre = texto(el, "genericSituationRecordName")
            tipo = "otra"
            subtipo = nombre or ""
        if not lat or not lon:
            el.clear()
            continue
        try:
            y, x = float(lat), float(lon)
        except ValueError:
            el.clear()
            continue
        props = {
            "tipo": tipo,
            "subtipo": subtipo or "",
            "gravedad": texto(el, "severity") or "",
            "estado": texto(el, "validityStatus") or "",
            "carretera": texto(el, "roadName") or "",
            "sentido": texto(el, "carriageway", "tpegDirectionRoad") or "",
            "carril": texto(el, "laneUsage") or "",
            "km": texto(el, "kilometerPoint") or "",
            "provincia": texto(el, "province") or "",
            "municipio": texto(el, "municipality") or "",
            "desde": texto(el, "overallStartTime") or "",
            "hasta": texto(el, "overallEndTime") or "",
        }
        feats.append({"type": "Feature",
                      "geometry": {"type": "Point", "coordinates": [x, y]},
                      "properties": props})
        tipos[props["tipo"]] = tipos.get(props["tipo"], 0) + 1
        el.clear()

    json.dump({"type": "FeatureCollection", "features": feats},
              open(os.path.join(DEST, "dgt_incidencias.geojson"), "w", encoding="utf-8"),
              ensure_ascii=False)
    activas = sum(1 for f in feats if f["properties"]["estado"] == "active")
    recibo = {
        "fuente": "DGT · NAP de Tráfico",
        "dataset": "Incidencias DGT DATEX2 v3.7",
        "url": FEEDS["incidencias"],
        "licencia": "reutilización con atribución",
        "features": len(feats),
        "activas": activas,
        "por_tipo": dict(sorted(tipos.items(), key=lambda kv: -kv[1])),
        "descargado": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    json.dump(recibo, open(os.path.join(DEST, "dgt_incidencias_recibo.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)
    print("  %d incidencias · %d activas" % (len(feats), activas))
    for t, n in recibo["por_tipo"].items():
        print("   %-38s %4d" % (t, n))
    return feats


def main():
    ap = argparse.ArgumentParser(description="DGT · tráfico en tiempo real")
    ap.add_argument("--incidencias", action="store_true")
    ap.add_argument("--refrescar", action="store_true", help="fuerza descarga nueva")
    a = ap.parse_args()
    if a.incidencias:
        incidencias(descarga("incidencias", a.refrescar))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
