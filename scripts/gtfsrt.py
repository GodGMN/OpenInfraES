# -*- coding: utf-8 -*-
"""GTFS-Realtime · vehículos en vivo de los operadores que publican en abierto.

Un feed GTFS-RT es un **protobuf** que se consulta en bucle (cada 15-30 s). No es un fichero
que se descargue una vez: la URL devuelve la foto del instante.

**El NAP de transportes NO publica la URL de sus 86 feeds RT.** Se comprobó: el catálogo los
lista con todos los campos a cero y `Fichero/downloadLink/{id}` responde «Archivo no
encontrado». Así que aquí se usan las URLs directas de cada operador.

Verificado en abierto (2026-11-16):

    Renfe   gtfsrt.renfe.com/vehicle_positions.pb     406 trenes
            gtfsrt.renfe.com/trip_updates.pb          retrasos por parada
            gtfsrt.renfe.com/alerts.pb                 avisos de servicio

Requieren clave (no configuradas): TMB (401), EMT Madrid, EMT Valencia.

    python scripts/gtfsrt.py                 # todos los feeds abiertos
    python scripts/gtfsrt.py --feed renfe    # uno
    python scripts/gtfsrt.py --detalle       # además retrasos y avisos
"""
import argparse
import datetime
import json
import os
import sys

from google.transit import gtfs_realtime_pb2

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos")
UA = {"User-Agent": "OpenInfraES/1.0", "Accept": "application/x-protobuf"}

# feed -> (url, operador, tipo, estado)
FEEDS = {
    "renfe": {
        "operador": "Renfe",
        "url": "https://gtfsrt.renfe.com/vehicle_positions.pb",
        "url_retrasos": "https://gtfsrt.renfe.com/trip_updates.pb",
        "url_avisos": "https://gtfsrt.renfe.com/alerts.pb",
        "estado": "abierto",
    },
    "tmb": {"operador": "TMB", "url": "https://api.tmb.cat/v1/transit/gtfs-realtime/vehiclepositions",
            "estado": "requiere clave (401)"},
    "emt-madrid": {"operador": "EMT Madrid", "url": "", "estado": "requiere clave"},
}


def trae(url, intentos=3):
    """Descarga el protobuf. Renfe sirve 200 con 0 bytes si se le llama en ráfaga."""
    import time
    import urllib.request
    ultimo = None
    for _ in range(intentos):
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                b = r.read()
            if b:
                return b
            ultimo = "respuesta vacía (0 bytes)"
        except Exception as e:
            ultimo = str(e)[:90]
        time.sleep(3)
    raise RuntimeError(ultimo)


def lee(url):
    m = gtfs_realtime_pb2.FeedMessage()
    m.ParseFromString(trae(url))
    return m


def hora(ts):
    if not ts:
        return None
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat(timespec="seconds")


def _retraso(v):
    """VehiclePosition.delay no existe en todas las versiones del protobuf."""
    for obj, campo in ((v, "delay"), (v.trip, "delay")):
        try:
            if obj.HasField(campo):
                return int(getattr(obj, campo))
        except (ValueError, AttributeError):
            continue
    return None


def vehiculos(clave):
    f = FEEDS[clave]
    m = lee(f["url"])
    feats = []
    for e in m.entity:
        if not e.HasField("vehicle"):
            continue
        v = e.vehicle
        if not v.HasField("position") or not v.position.latitude:
            continue
        ruta = (v.trip.route_id or "").strip()
        # Renfe deja route_id VACIO: la linea va en la etiqueta ("C1-23551" -> "C1")
        if not ruta and v.vehicle and v.vehicle.label:
            ruta = v.vehicle.label.split("-")[0]
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [round(v.position.longitude, 6), round(v.position.latitude, 6)]},
            "properties": {
                "operador": f["operador"],
                "linea": ruta,
                "vehiculo": v.vehicle.id or v.vehicle.label or "",
                "etiqueta": v.vehicle.label or "",
                "rumbo": round(v.position.bearing, 0) if v.position.HasField("bearing") else None,
                "velocidad": round(v.position.speed * 3.6, 0) if v.position.HasField("speed") else None,
                "ultima": hora(v.timestamp),
                "retraso_s": _retraso(v),
            }})
    return feats, m.header.timestamp


def retrasos(clave):
    f = FEEDS[clave]
    m = lee(f["url_retrasos"])
    por_linea = {}
    for e in m.entity:
        if not e.HasField("trip_update"):
            continue
        tu = e.trip_update
        ruta = (tu.trip.route_id or "").strip()
        if not ruta and tu.trip.trip_id:
            ruta = tu.trip.trip_id.split("-")[0]
        if tu.HasField("delay"):
            por_linea.setdefault(ruta, []).append(tu.delay)
    resumen = []
    for r, vals in por_linea.items():
        if not vals:
            continue
        resumen.append({"linea": r, "viajes": len(vals),
                        "retraso_medio_s": round(sum(vals) / len(vals)),
                        "retraso_max_s": max(vals)})
    resumen.sort(key=lambda x: -x["retraso_medio_s"])
    return resumen


def avisos(clave):
    f = FEEDS[clave]
    m = lee(f["url_avisos"])
    salida = []
    for e in m.entity:
        if not e.HasField("alert"):
            continue
        a = e.alert
        # Renfe trae header_text VACIO: el texto util esta en description_text
        def txt(tr):
            for t in tr.translation:
                if (t.text or "").strip():
                    return t.text.strip()
            return ""
        salida.append({"titulo": txt(a.header_text) or txt(a.description_text)[:70],
                       "texto": txt(a.description_text)[:240],
                       "lineas": [ie.route_id for ie in a.informed_entity if ie.route_id][:6],
                       "desde": hora(a.active_period[0].start) if a.active_period else None})
    return salida


def main():
    ap = argparse.ArgumentParser(description="GTFS-Realtime · vehículos en vivo")
    ap.add_argument("--feed", default="renfe")
    ap.add_argument("--detalle", action="store_true")
    ap.add_argument("--todos", action="store_true")
    a = ap.parse_args()

    claves = [k for k, v in FEEDS.items() if v.get("url") and v["estado"] == "abierto"] \
        if a.todos else [a.feed]
    if a.todos:
        print("  feeds abiertos: %s" % ", ".join(claves))

    todos = []
    recibo = {"fuente": "GTFS-Realtime (protobuf)", "descargado":
              datetime.datetime.now().isoformat(timespec="seconds"), "feeds": {}}
    for k in claves:
        try:
            feats, ts = vehiculos(k)
            todos.extend(feats)
            lineas = sorted({f["properties"]["linea"] for f in feats if f["properties"]["linea"]})
            recibo["feeds"][k] = {"operador": FEEDS[k]["operador"], "url": FEEDS[k]["url"],
                                  "vehiculos": len(feats), "lineas": len(lineas),
                                  "timestamp_feed": hora(ts)}
            print("  %-10s %4d vehículos · %3d líneas" % (FEEDS[k]["operador"], len(feats), len(lineas)))
            if a.detalle:
                ret = retrasos(k)
                avi = avisos(k)
                recibo["feeds"][k]["retrasos"] = ret[:12]
                recibo["feeds"][k]["avisos"] = avi[:8]
                print("    retrasos: %s" % ", ".join(
                    "%s %+ds" % (r["linea"], r["retraso_medio_s"]) for r in ret[:5]))
                print("    avisos: %d" % len(avi))
        except Exception as e:
            recibo["feeds"][k] = {"operador": FEEDS[k]["operador"], "error": str(e)[:120]}
            print("  %-10s ERROR %s" % (FEEDS[k]["operador"], str(e)[:80]))

    json.dump({"type": "FeatureCollection", "features": todos},
              open(os.path.join(DEST, "gtfsrt_vehiculos.geojson"), "w", encoding="utf-8"),
              ensure_ascii=False)
    # compatibilidad con el visor, que ya lee datos/trenes.geojson
    if "renfe" in claves:
        json.dump({"type": "FeatureCollection",
                   "features": [f for f in todos if f["properties"]["operador"] == "Renfe"]},
                  open(os.path.join(DEST, "trenes.geojson"), "w", encoding="utf-8"),
                  ensure_ascii=False)
    json.dump(recibo, open(os.path.join(DEST, "gtfsrt_recibo.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("  %d vehículos -> datos/gtfsrt_vehiculos.geojson" % len(todos))


if __name__ == "__main__":
    main()
