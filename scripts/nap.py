# -*- coding: utf-8 -*-
"""NAP · Punto de Acceso Nacional de transportes (MITMA).

El NAP **sí** tiene API. Lo que fallaba era la cabecera: se llama **`ApiKey`** (ni `X-Api-Key`,
ni `Api-Key`, ni `Authorization`), y la ruta es `/api/Fichero/GetList`, no un CKAN.

    GET  /api/Fichero/GetList             catálogo completo (169 conjuntos, ~10 MB)
    POST /api/Fichero/Filter              filtrado del catálogo
    GET  /api/Fichero/downloadLink/{id}   URL firmada de S3 (caduca en 900 s)
    GET  /api/Region                      CCAA y provincias

169 conjuntos de **550 operadores**: 148 de autobús, 27 ferroviarios, 3 marítimos, 1 aéreo.
Formatos: 169 GTFS-ZIP, 86 GTFS-RT, 67 SIRI, 30 NeTEx.

    python scripts/nap.py --catalogo
    python scripts/nap.py --lista --tipo Ferroviario
    python scripts/nap.py --gtfs 1133 --etiqueta alsa

De cada GTFS extrae paradas con coordenadas (GeoJSON), catálogo de líneas y **frecuencias por
línea** (headway medio y por franja horaria), que es lo que declara `frequencies.txt`.
"""
import argparse
import csv
import datetime
import io
import json
import os
import sys
import time
import urllib.request
import zipfile
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos")
BASE = "https://nap.transportes.gob.es/api"


def clave():
    k = os.environ.get("NAP_API_KEY")
    if k:
        return k.strip()
    ruta = os.path.join(RAIZ, ".env")
    if os.path.exists(ruta):
        for linea in open(ruta, encoding="utf-8"):
            if linea.startswith("NAP_API_KEY="):
                v = linea.split("=", 1)[1].strip()
                if v:
                    return v
    raise SystemExit("falta NAP_API_KEY en .env (la clave del NAP; va en la cabecera `ApiKey`)")


def pide(ruta, crudo=False, intentos=3):
    """El NAP devuelve 200 con 0 bytes en ráfaga: se reintenta."""
    ultimo = None
    for _ in range(intentos):
        req = urllib.request.Request(
            "%s/%s" % (BASE, ruta),
            headers={"ApiKey": clave(), "Accept": "application/json",
                     "User-Agent": "OpenInfraES/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                b = r.read()
                if not b.strip():
                    ultimo = "respuesta vacía (0 bytes)"
                    time.sleep(3)
                    continue
                return b.decode("utf-8", "replace") if crudo else json.loads(b)
        except Exception as e:
            ultimo = str(e)[:100]
            time.sleep(3)
    raise SystemExit("NAP %s: %s" % (ruta, ultimo))


def catalogo():
    d = pide("Fichero/GetList")
    c = d.get("conjuntosDatoDto", [])
    json.dump(d, open(os.path.join(DEST, "nap_catalogo.json"), "w", encoding="utf-8"),
              ensure_ascii=False)

    tipos = defaultdict(int)
    formatos = defaultdict(int)
    operadores = set()
    paradas = viajes = 0
    for x in c:
        for t in (x.get("tiposTransporte") or []):
            tipos[t.get("nombre")] += 1
        for f in (x.get("ficherosDto") or []):
            formatos[f.get("tipoFicheroNombre")] += 1
            paradas = max(paradas, f.get("numeroParadas") or 0)
            viajes = max(viajes, f.get("numeroViajes") or 0)
        for o in (x.get("operadores") or []):
            operadores.add(o.get("nombre"))

    recibo = {
        "fuente": "NAP · MITMA",
        "url": BASE + "/Fichero/GetList",
        "cabecera": "ApiKey",
        "conjuntos": len(c),
        "operadores": len(operadores),
        "por_tipo": dict(tipos),
        "por_formato": dict(formatos),
        "max_paradas_un_conjunto": paradas,
        "max_viajes_un_conjunto": viajes,
        "descargado": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    json.dump(recibo, open(os.path.join(DEST, "nap_catalogo_recibo.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)
    print("  %d conjuntos · %d operadores" % (len(c), len(operadores)))
    for k, v in sorted(tipos.items(), key=lambda kv: -kv[1]):
        print("   %-16s %3d" % (k, v))
    for k, v in sorted(formatos.items(), key=lambda kv: -kv[1]):
        print("   %-16s %3d" % (k, v))


def lista(tipo=None):
    d = json.load(open(os.path.join(DEST, "nap_catalogo.json"), encoding="utf-8"))
    filas = []
    for x in d["conjuntosDatoDto"]:
        if tipo and not any(tipo.lower() in (t.get("nombre") or "").lower()
                            for t in (x.get("tiposTransporte") or [])):
            continue
        for f in (x.get("ficherosDto") or []):
            if f.get("tipoFicheroNombre") != "GTFS-ZIP":
                continue
            filas.append((f.get("numeroParadas") or 0, f["ficheroId"], x["nombre"],
                          (f.get("tamanio") or 0) / 1e6, f.get("numeroViajes") or 0))
            break
    filas.sort(reverse=True)
    print("  %-6s %-8s %-8s %-9s %s" % ("id", "paradas", "viajes", "MB", "nombre"))
    for p, fid, nom, mb, vj in filas[:40]:
        print("  %-6s %-8s %-8s %-9.1f %s" % (fid, p or "—", vj or "—", mb, nom[:54]))


def descarga_gtfs(fichero_id):
    url = pide("Fichero/downloadLink/%s" % fichero_id, crudo=True).strip().strip('"')
    print("  URL firmada obtenida")
    req = urllib.request.Request(url, headers={"User-Agent": "OpenInfraES/1.0"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return r.read()


def extrae(zbytes, etiqueta, fichero_id, _fecha=None):
    if _fecha is None:
        _fecha = __import__("datetime").date.today() + __import__("datetime").timedelta(days=1)
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    nombres = z.namelist()

    def hoja(n):
        for x in nombres:
            if x.endswith("/" + n) or x == n:
                return x
        return None

    def limpia(r):
        """Algunos GTFS rellenan a ancho fijo: route_id '10T0001C1  ' no casa con
        el '10T0001C1' de trips.txt. Sin strip, 269 de 277 rutas quedan huerfanas
        y la linea sale con su ID interno en vez de C1."""
        return {(k or "").strip(): (v or "").strip() for k, v in r.items()}

    def filas(n, filtro=None):
        ruta = hoja(n)
        if not ruta:
            return []
        texto = z.read(ruta).decode("utf-8-sig", "replace")
        it = (limpia(r) for r in csv.DictReader(io.StringIO(texto)))
        return [r for r in it if (filtro is None or filtro(r))]

    def itera(n):
        """Itera sin cargar el fichero entero: stop_times puede tener millones de filas."""
        ruta = hoja(n)
        if not ruta:
            return
        with z.open(ruta) as fh:
            texto = io.TextIOWrapper(fh, encoding="utf-8-sig", errors="replace")
            for r in csv.DictReader(texto):
                yield {(k or "").strip(): (v or "").strip() for k, v in r.items()}

    # --- paradas
    feats = []
    for s in filas("stops.txt"):
        try:
            lon, lat = float(s["stop_lon"]), float(s["stop_lat"])
        except (KeyError, ValueError):
            continue
        feats.append({"type": "Feature",
                      "geometry": {"type": "Point", "coordinates": [lon, lat]},
                      "properties": {"nombre": s.get("stop_name") or "",
                                     "codigo": s.get("stop_code") or "",
                                     "id": s.get("stop_id") or ""}})

    # route_short_name viene VACIO en Cercanias: sin este fallback las lineas salen
    # como IDs internos (10T0018C5) en vez de C-1, C-2...
    # --- calendario: un GTFS trae TODOS los patrones (L-V, sabados, festivos, verano).
    # Sumarlos da "salidas de ningun dia concreto": C1 salia con 26.847 al dia, imposible.
    # Se filtra por los service_id activos en una fecha real.
    import datetime as _dt
    fecha = _fecha
    dia_sem = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"][fecha.weekday()]
    ymd = fecha.strftime("%Y%m%d")
    activos = set()
    for c in filas("calendar.txt"):
        if (c.get(dia_sem) or "0") == "1":
            ini, fin = c.get("start_date") or "", c.get("end_date") or ""
            if (not ini or ini <= ymd) and (not fin or ymd <= fin):
                activos.add(c.get("service_id"))
    for c in filas("calendar_dates.txt"):
        if (c.get("date") or "") == ymd:
            if (c.get("exception_type") or "") == "1":
                activos.add(c.get("service_id"))
            elif (c.get("exception_type") or "") == "2":
                activos.discard(c.get("service_id"))

    rutas = {r["route_id"]: {
                "corto": ((r.get("route_short_name") or "").strip()
                          or (r.get("route_long_name") or "").strip()
                          or r["route_id"]),
                "largo": (r.get("route_long_name") or "").strip(),
                "tipo": r.get("route_type") or ""}
             for r in filas("routes.txt")}

    # --- frecuencias: trip_id -> headway, agregado por ruta
    # solo los viajes que circulan ese dia
    viaje_ruta = {t["trip_id"]: t.get("route_id") for t in filas("trips.txt")
                  if not activos or t.get("service_id") in activos}
    print("  servicio activo el %s: %d de %d viajes" % (fecha, len(viaje_ruta), len(filas("trips.txt"))))
    por_ruta = defaultdict(list)
    for f in filas("frequencies.txt"):
        rid = viaje_ruta.get(f.get("trip_id"))
        if not rid:
            continue
        try:
            por_ruta[rid].append((f.get("start_time") or "", int(float(f.get("headway_secs") or 0))))
        except ValueError:
            pass

    metodo = "frequencies.txt"

    # Renfe y otros operadores NO publican frequencies.txt: su horario es fijo por viaje.
    # OJO: en largo recorrido un "headway" no significa nada (un AVE no pasa cada 3 min
    # porque salga 3 trenes a la misma hora). Para esos, lo honesto es salidas al día.
    if not por_ruta:
        metodo = "stop_times.txt (salidas reales, no frequencies)"
        # No fiarse de stop_sequence: unos GTFS numeran 1, otros 01, otros empiezan en 0.
        # La hora de salida del viaje es el MINIMO de sus paradas. Se recorre en streaming.
        viaje_hora = {}
        n_filas = 0
        for r in itera("stop_times.txt"):
            n_filas += 1
            tid = r.get("trip_id")
            hora = (r.get("departure_time") or r.get("arrival_time") or "")
            if not tid or len(hora) < 4:
                continue
            previa = viaje_hora.get(tid)
            if previa is None or hora < previa:
                viaje_hora[tid] = hora
        print("  stop_times: %d filas · %d viajes con hora" % (n_filas, len(viaje_hora)))

        lineas = defaultdict(lambda: {"rutas": set(), "salidas": 0, "por_hora": defaultdict(int)})
        for tid, rid in viaje_ruta.items():
            hs = viaje_hora.get(tid)
            if not hs or not rid:
                continue
            try:
                h = int(hs.split(":")[0])
            except ValueError:
                continue
            if h > 23:      # GTFS usa 24:30:00 para servicios que pasan de medianoche
                h = 23
            elif h < 0:
                continue
            nom = (rutas.get(rid, {}).get("corto") or rid)
            L = lineas[nom]
            L["rutas"].add(rid)
            L["salidas"] += 1
            L["por_hora"][h] += 1

        frec = []
        for nom, L in lineas.items():
            horas = {str(h): n for h, n in sorted(L["por_hora"].items())}
            pico = max(L["por_hora"].values()) if L["por_hora"] else 0
            frec.append({
                "ruta": nom,
                "tipo": rutas.get(next(iter(L["rutas"])), {}).get("tipo") or "",
                "rutas": len(L["rutas"]),
                "salidas_dia": L["salidas"],
                "salidas_hora_pico": pico,
                "headway_pico_min": round(60 / pico, 1) if pico >= 3 else None,
                "por_hora": horas,
            })
        frec.sort(key=lambda x: -x["salidas_dia"])
    else:
        frec = []
        for rid, vals in por_ruta.items():
            vals = [v for v in vals if v[1] > 0]
            if not vals:
                continue
            r = rutas.get(rid, {})
            franjas = defaultdict(list)
            for hora, v in vals:
                franjas[(hora.split(":")[0] if hora else "?")].append(v)
            frec.append({
                "ruta": r.get("corto") or rid,
                "nombre": r.get("largo") or "",
                "tipo": r.get("tipo") or "",
                "headway_min_medio": round(sum(v for _, v in vals) / len(vals) / 60, 1),
                "franjas": {h: round(sum(v) / len(v) / 60, 1) for h, v in sorted(franjas.items())},
            })
        frec.sort(key=lambda x: x["headway_min_medio"])

    json.dump({"type": "FeatureCollection", "features": feats},
              open(os.path.join(DEST, "nap_paradas_%s.geojson" % etiqueta), "w", encoding="utf-8"),
              ensure_ascii=False)

    recibo = {"fuente": "NAP · MITMA", "conjunto": etiqueta, "fichero_id": fichero_id,
              "fecha_servicio": _fecha.isoformat(),
              "paradas": len(feats), "lineas": len(rutas),
              "lineas_con_frecuencia": len(frec), "metodo_frecuencia": metodo,
              "frecuencias": frec[:60]}
    json.dump(recibo, open(os.path.join(DEST, "nap_%s_recibo.json" % etiqueta), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)
    return feats, rutas, frec


def main():
    ap = argparse.ArgumentParser(description="NAP · API de transportes (MITMA)")
    ap.add_argument("--catalogo", action="store_true")
    ap.add_argument("--lista", action="store_true")
    ap.add_argument("--tipo")
    ap.add_argument("--gtfs", type=int, metavar="ID")
    ap.add_argument("--etiqueta", default="gtfs")
    a = ap.parse_args()

    if a.catalogo:
        catalogo()
    elif a.lista:
        lista(a.tipo)
    elif a.gtfs:
        print("  descargando fichero %s..." % a.gtfs)
        b = descarga_gtfs(a.gtfs)
        print("  %.1f MB" % (len(b) / 1e6))
        fechas = [__import__('datetime').date.today() + __import__('datetime').timedelta(days=d)
                  for d in (1,)]
        feats, rutas, frec = extrae(b, a.etiqueta, a.gtfs, fechas[0])
        print("  %d paradas · %d líneas · %d con frecuencias" % (len(feats), len(rutas), len(frec)))
        for f in frec[:8]:
            if "headway_min_medio" in f:
                print("   %-12s %5.1f min medio" % (f["ruta"][:12], f["headway_min_medio"]))
            else:
                print("   %-12s %5d salidas/dia · pico %2d/h · %s rutas"
                      % (f["ruta"][:12], f["salidas_dia"], f["salidas_hora_pico"], f["rutas"]))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
