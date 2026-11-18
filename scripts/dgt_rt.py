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
    "paneles_loc": "https://nap.dgt.es/datex2/v3/dgt/DevicePublication/vms_datex2_v37.xml",
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




def paneles():
    """Paneles de mensaje variable: el texto va en un feed y la posicion en OTRO.

    `VmsPublication` trae el mensaje y una referencia `vmsControllerReference@id`; la lat/lon
    esta en `DevicePublication`, donde `device@id` es el mismo numero. Sin cruzar los dos no
    hay ni mapa ni mensaje.
    """
    ruta_msg = descarga("paneles")
    ruta_loc = descarga("paneles_loc")

    # 1. posiciones
    pos = {}
    for _, el in ET.iterparse(ruta_loc, events=("end",)):
        if local(el.tag) != "device":
            continue
        did = el.get("id")
        lat = texto(el, "latitude")
        lon = texto(el, "longitude")
        if did and lat and lon:
            try:
                pos[did] = (float(lon), float(lat), texto(el, "roadName") or "",
                            texto(el, "province") or "")
            except ValueError:
                pass
        el.clear()
    print("  %d paneles con posición" % len(pos))

    # 2. mensajes, agrupados por controlador
    mensajes = {}
    for _, el in ET.iterparse(ruta_msg, events=("end",)):
        if local(el.tag) != "vmsControllerStatus":
            continue
        cid = None
        for h in el.iter():
            if local(h.tag) == "vmsControllerReference":
                cid = h.get("id")
                break
        if not cid:
            el.clear()
            continue
        lineas = []
        for h in el.iter():
            if local(h.tag) == "textLine" and (h.text or "").strip():
                # el texto viene con saltos y espacios de relleno del panel
                limpio = " ".join((h.text or "").split())
                if limpio:
                    lineas.append(limpio)
        if lineas:
            mensajes.setdefault(cid, [])
            for l in lineas:
                if l not in mensajes[cid]:
                    mensajes[cid].append(l)
        el.clear()
    print("  %d controladores con mensaje" % len(mensajes))

    feats = []
    for cid, lineas in mensajes.items():
        p = pos.get(cid)
        if not p:
            continue
        lon, lat, carretera, provincia = p
        feats.append({"type": "Feature",
                      "geometry": {"type": "Point", "coordinates": [lon, lat]},
                      "properties": {"panel": cid, "mensaje": " · ".join(lineas)[:180],
                                     "carretera": carretera, "provincia": provincia}})

    json.dump({"type": "FeatureCollection", "features": feats},
              open(os.path.join(DEST, "dgt_paneles.geojson"), "w", encoding="utf-8"),
              ensure_ascii=False)

    from collections import Counter
    top = Counter(" · ".join(v) for v in mensajes.values())
    recibo = {"fuente": "DGT · NAP de Tráfico", "dataset": "Paneles DGT DATEX2 v3.7",
              "url": FEEDS["paneles"], "url_localizaciones": FEEDS["paneles_loc"],
              "licencia": "reutilización con atribución",
              "features": len(feats), "paneles_localizados": len(pos),
              "descargado": datetime.datetime.now().isoformat(timespec="seconds"),
              "mensajes_top": [{"texto": t, "paneles": n} for t, n in top.most_common(10)]}
    json.dump(recibo, open(os.path.join(DEST, "dgt_paneles_recibo.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)
    print("  %d paneles con mensaje y posición" % len(feats))
    for t, n in top.most_common(6):
        print("   %-46s x%d" % (t[:46], n))


def main():
    ap = argparse.ArgumentParser(description="DGT · tráfico en tiempo real")
    ap.add_argument("--incidencias", action="store_true")
    ap.add_argument("--paneles", action="store_true")
    ap.add_argument("--refrescar", action="store_true", help="fuerza descarga nueva")
    a = ap.parse_args()
    if a.incidencias:
        incidencias(descarga("incidencias", a.refrescar))
    elif a.paneles:
        paneles()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
