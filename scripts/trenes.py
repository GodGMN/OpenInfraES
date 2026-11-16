# -*- coding: utf-8 -*-
"""Trenes en tiempo real desde GTFS-Realtime de Renfe (abierto, sin clave).

Fuente: https://gtfsrt.renfe.com/{vehicle_positions,trip_updates,alerts}.pb
Formato: GTFS-Realtime (Protocol Buffers). Se convierte a GeoJSON para el visor.

Uso:
    python scripts/trenes.py
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

from google.transit import gtfs_realtime_pb2 as pb

UA = {"User-Agent": "OpenInfraES/1.0 (datos abiertos)"}
BASE = "https://gtfsrt.renfe.com/"
DEST = "C:/Users/d_ant/Projects/OpenInfraES/datos"


def bajar(nombre):
    req = urllib.request.Request(BASE + nombre, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def main():
    crudo = bajar("vehicle_positions.pb")
    feed = pb.FeedMessage()
    feed.ParseFromString(crudo)
    generado = datetime.fromtimestamp(feed.header.timestamp, tz=timezone.utc) if feed.header.timestamp else None

    feats = []
    for e in feed.entity:
        if not e.HasField("vehicle"):
            continue
        v = e.vehicle
        pos = v.position
        if not pos.latitude and not pos.longitude:
            continue
        # Renfe no rellena route_id: la ruta va implícita en la etiqueta ("C1-23551")
        etiqueta = v.vehicle.label or ""
        ruta = v.trip.route_id or ""
        if not ruta:
            m = re.match(r"^([A-Z]+\d+)", etiqueta)
            ruta = m.group(1) if m else None
        props = {
            "tren": v.vehicle.id or e.id,
            "etiqueta": etiqueta or None,
            "viaje": v.trip.trip_id or None,
            "ruta": ruta or None,
            "rumbo": round(pos.bearing, 1) if pos.bearing else None,
            "velocidad_kmh": round(pos.speed * 3.6, 1) if pos.speed else None,
            "ts": v.timestamp or None,
            "hora": datetime.fromtimestamp(v.timestamp, tz=timezone.utc).strftime("%H:%M:%S") if v.timestamp else None,
            "fuente": "Renfe GTFS-RT (gtfsrt.renfe.com)",
        }
        feats.append({"type": "Feature", "properties": props,
                      "geometry": {"type": "Point", "coordinates": [pos.longitude, pos.latitude]}})

    gj = {"type": "FeatureCollection", "features": feats}
    json.dump(gj, open(DEST + "/trenes.geojson", "w", encoding="utf-8"), ensure_ascii=False)

    # alertas (incidencias de servicio)
    alertas = []
    try:
        afeed = pb.FeedMessage()
        afeed.ParseFromString(bajar("alerts.pb"))
        for e in afeed.entity:
            if not e.HasField("alert"):
                continue
            al = e.alert
            def tr(campo):
                t = getattr(al, campo, None)
                if not t:
                    return None
                for item in t.translation:
                    if item.text:
                        return item.text
                return None
            cab = tr("header_text")
            desc = tr("description_text")
            rutas = [ie.route_id for ie in al.informed_entity if ie.route_id]
            alertas.append({"titulo": cab, "descripcion": desc, "rutas": rutas[:6],
                            "inicio": al.active_period[0].start if al.active_period else None,
                            "fin": al.active_period[0].end if al.active_period else None})
    except Exception as e:
        print("  alertas: %s" % type(e).__name__)

    json.dump({"generado": generado.isoformat() if generado else None, "alertas": alertas},
              open(DEST + "/trenes_alertas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("  trenes: %d con posición" % len(feats))
    print("  alertas: %d" % len(alertas))
    print("  feed generado: %s" % (generado.isoformat() if generado else "—"))
    if alertas:
        print("  primera alerta: %s" % (alertas[0]["titulo"] or "—")[:90])

    json.dump({"features": len(feats), "alertas": len(alertas),
               "fichero": "trenes.geojson", "fuente": "Renfe GTFS-RT",
               "generado": generado.isoformat() if generado else None},
              open(DEST + "/trenes_recibo.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
