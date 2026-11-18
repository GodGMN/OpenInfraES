# -*- coding: utf-8 -*-
"""NAP · líneas de bus y tren (shapes.txt de los GTFS).

Un GTFS trae las paradas en `stops.txt` y el **trazado real de cada línea** en `shapes.txt`:
puntos ordenados por `shape_id`. Cruzando:

    shapes.txt  shape_id, lat, lon, sequence   -> el trazado
    trips.txt   shape_id, route_id, service_id -> a qué línea pertenece
    routes.txt  route_id, short_name, type     -> su nombre

se obtiene cada línea dibujada por donde pasa de verdad, no una recta entre paradas.

    python scripts/nap_lineas.py --gtfs 1130 --etiqueta cercanias-renfe
    python scripts/nap_lineas.py --gtfs 1134 --etiqueta metro-madrid
"""
import argparse
import csv
import datetime
import io
import json
import os
import sys
import zipfile
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nap import descarga_gtfs, DEST

# route_type de GTFS
TIPO = {"0": "tranvía", "1": "metro", "2": "tren", "3": "autobús",
        "4": "ferry", "5": "teleférico", "6": "funicular", "7": "funicular",
        "11": "trolebús", "12": "monorraíl"}



# Colores oficiales de línea (plano de Metro de Madrid / CRTM). Se guardan EN EL DATO, no en
# el visor: así el color viaja con la línea y cualquier otro proyecto lo hereda.
COLORES = {
    "metro-madrid": {
        "1": "#2DBEF0", "2": "#E23A39", "3": "#FFDF00", "4": "#814C9E",
        "5": "#6DBE45", "6": "#9CA3AF", "7": "#F58220", "8": "#EC038B",
        "9": "#9B0D82", "10": "#005AA9", "11": "#00893D", "12": "#A5BE00",
        "R": "#003DA5",
    },
    # Cercanías: paleta del núcleo de Madrid, aproximada donde el plano no da color propio
    "cercanias-renfe": {
        "C1": "#00A0DF", "C2": "#00893D", "C3": "#9B0D82", "C4": "#005AA9",
        "C5": "#FFDF00", "C6": "#E23A39", "C7": "#F58220", "C8": "#6DBE45",
        "C9": "#814C9E", "C10": "#A5BE00",
        "R1": "#EC038B", "R2": "#2DBEF0", "R3": "#F58220", "R4": "#00893D",
        "R5": "#814C9E", "R6": "#005AA9", "R7": "#E23A39", "R8": "#6DBE45",
        "R9": "#9B0D82",
    },
}


def main():
    ap = argparse.ArgumentParser(description="NAP · líneas desde shapes.txt")
    ap.add_argument("--gtfs", type=int, required=True)
    ap.add_argument("--etiqueta", required=True)
    ap.add_argument("--fecha", help="YYYY-MM-DD; por defecto mañana")
    a = ap.parse_args()

    fecha = (datetime.date.fromisoformat(a.fecha) if a.fecha
             else datetime.date.today() + datetime.timedelta(days=1))
    print("  descargando fichero %s..." % a.gtfs)
    zb = descarga_gtfs(a.gtfs)
    print("  %.1f MB" % (len(zb) / 1e6))

    z = zipfile.ZipFile(io.BytesIO(zb))
    nombres = z.namelist()

    def hoja(n):
        for x in nombres:
            if x.endswith("/" + n) or x == n:
                return x
        return None

    def itera(n):
        ruta = hoja(n)
        if not ruta:
            return
        with z.open(ruta) as fh:
            texto = io.TextIOWrapper(fh, encoding="utf-8-sig", errors="replace")
            for r in csv.DictReader(texto):
                yield {(k or "").strip(): (v or "").strip() for k, v in r.items()}

    # --- calendario: solo los servicios que circulan ese día
    dia = ["monday", "tuesday", "wednesday", "thursday", "friday",
           "saturday", "sunday"][fecha.weekday()]
    ymd = fecha.strftime("%Y%m%d")
    activos = set()
    for c in itera("calendar.txt"):
        if (c.get(dia) or "0") == "1":
            ini, fin = c.get("start_date") or "", c.get("end_date") or ""
            if (not ini or ini <= ymd) and (not fin or ymd <= fin):
                activos.add(c.get("service_id"))
    for c in itera("calendar_dates.txt"):
        if (c.get("date") or "") == ymd:
            if c.get("exception_type") == "1":
                activos.add(c.get("service_id"))
            elif c.get("exception_type") == "2":
                activos.discard(c.get("service_id"))

    # --- rutas
    rutas = {}
    for r in itera("routes.txt"):
        rutas[r["route_id"]] = {
            "linea": r.get("route_short_name") or r.get("route_long_name") or r["route_id"],
            "nombre": r.get("route_long_name") or "",
            "tipo": TIPO.get(r.get("route_type") or "", r.get("route_type") or ""),
        }

    # --- shape_id -> route_id (solo viajes activos)
    shape_ruta = {}
    for t in itera("trips.txt"):
        if activos and t.get("service_id") not in activos:
            continue
        sid = t.get("shape_id")
        if sid and sid not in shape_ruta:
            shape_ruta[sid] = t.get("route_id")

    # --- trazados
    puntos = defaultdict(list)
    for s in itera("shapes.txt"):
        sid = s.get("shape_id")
        if sid not in shape_ruta:
            continue
        try:
            puntos[sid].append((int(float(s.get("shape_pt_sequence") or 0)),
                                float(s.get("shape_pt_lon")), float(s.get("shape_pt_lat"))))
        except (TypeError, ValueError):
            continue

    # --- agrupar por línea: puede haber varios shapes por ruta (ida y vuelta)
    por_linea = defaultdict(list)
    for sid, pts in puntos.items():
        rid = shape_ruta.get(sid)
        if not rid or len(pts) < 2:
            continue
        pts.sort()
        por_linea[rid].append([round(x, 5) for _, x, y in pts] and
                              [[round(x, 5), round(y, 5)] for _, x, y in pts])

    paleta = COLORES.get(a.etiqueta, {})
    def color_de(linea):
        base = (linea or "").strip()
        if base in paleta:
            return paleta[base]
        # C1a, C4b... heredan el color de su línea base
        for k in sorted(paleta, key=len, reverse=True):
            if base.startswith(k):
                return paleta[k]
        return None

    feats = []
    for rid, trazados in por_linea.items():
        r = rutas.get(rid, {})
        for i, coords in enumerate(trazados):
            if len(coords) < 2:
                continue
            feats.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {
                    "linea": r.get("linea") or rid,
                    "nombre": r.get("nombre") or "",
                    "tipo": r.get("tipo") or "",
                    "ramal": i + 1,
                    "puntos": len(coords),
                    "color": color_de(r.get("linea")),
                }})

    salida = os.path.join(DEST, "nap_lineas_%s.geojson" % a.etiqueta)
    json.dump({"type": "FeatureCollection", "features": feats},
              open(salida, "w", encoding="utf-8"), ensure_ascii=False)

    # resumen por línea
    resumen = defaultdict(lambda: {"trazados": 0, "puntos": 0})
    for f in feats:
        L = resumen[f["properties"]["linea"]]
        L["trazados"] += 1
        L["puntos"] += f["properties"]["puntos"]

    recibo = {
        "fuente": "NAP · MITMA", "conjunto": a.etiqueta, "fichero_id": a.gtfs,
        "fecha_servicio": fecha.isoformat(),
        "features": len(feats), "lineas": len(resumen),
        "shapes": len(puntos), "tamano_kb": round(os.path.getsize(salida) / 1024, 1),
        "lineas_detalle": [{"linea": k, "trazados": v["trazados"], "puntos": v["puntos"]}
                           for k, v in sorted(resumen.items())][:80],
        "descargado": datetime.datetime.now().isoformat(timespec="seconds"),
        "nota": "Un LineString por shape (ida/vuelta y ramales son trazados distintos).",
        "colores": "oficiales de línea (plano de Metro de Madrid); en Cercanías, paleta aproximada",
    }
    json.dump(recibo, open(os.path.join(DEST, "nap_lineas_%s_recibo.json" % a.etiqueta), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)

    print("  %d trazados · %d líneas · %.1f MB" % (len(feats), len(resumen), recibo["tamano_kb"] / 1024))
    for k, v in sorted(resumen.items())[:12]:
        print("   %-8s %2d trazados · %6d puntos" % (k, v["trazados"], v["puntos"]))


if __name__ == "__main__":
    main()