#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arnes del repositorio OpenInfraES. Offline y sin dependencias.

Comprueba:
  1. Que existen los GeoJSON y los CSV agregados.
  2. Que los agregados cuadran con los GeoJSON (segmentos y MW).
  3. Que los conteos coinciden con los declarados por la fuente.
  4. Que existe recibo de procedencia con URL.
Sale 0 si todo esta en verde.
"""
import csv
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
errores = []


def error(m):
    errores.append(m)


def leer_csv(nombre):
    ruta = os.path.join(DATOS, nombre)
    if not os.path.exists(ruta):
        error("falta datos/%s" % nombre)
        return []
    with open(ruta, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    # 1. GeoJSON
    lineas = plantas = None
    for nombre in ("lineas_hv.geojson", "plantas.geojson"):
        ruta = os.path.join(DATOS, nombre)
        if not os.path.exists(ruta):
            error("falta datos/%s (ejecuta scripts/descargar.py)" % nombre)
            continue
        d = json.load(open(ruta, encoding="utf-8"))
        feats = d.get("features", [])
        if len(feats) < 1000:
            error("datos/%s: solo %d features" % (nombre, len(feats)))
        if nombre.startswith("lineas"):
            lineas = feats
        else:
            plantas = feats

    # 2 y 3. agregados
    agg_l = leer_csv("agregado_lineas.csv")
    agg_t = leer_csv("agregado_plantas_tecnologia.csv")
    agg_c = leer_csv("agregado_plantas_ccaa.csv")
    agg_o = leer_csv("agregado_lineas_operador.csv")

    if agg_l:
        seg = sum(int(f["segmentos"]) for f in agg_l)
        if lineas is not None and seg != len(lineas):
            error("agregado_lineas: %d segmentos != %d features" % (seg, len(lineas)))
        if seg != 4929:
            error("agregado_lineas: %d segmentos != 4929 declarados" % seg)
        kv = {}
        for f in agg_l:
            k = int(f["tension_kv"])
            kv[k] = kv.get(k, 0) + int(f["segmentos"])
        if kv.get(400000) != 1752:
            error("400 kV: %s != 1752" % kv.get(400000))
        if kv.get(220000) != 3176:
            error("220 kV: %s != 3176" % kv.get(220000))

    if agg_t:
        mw = sum(float(f["mw"]) for f in agg_t)
        n = sum(int(f["plantas"]) for f in agg_t)
        if plantas is not None and n != len(plantas):
            error("agregado_plantas: %d plantas != %d features" % (n, len(plantas)))
        if n != 5797:
            error("agregado_plantas: %d plantas != 5797 declaradas" % n)
        if not (120000 < mw < 135000):
            error("MW totales fuera de rango razonable: %.0f" % mw)

    if agg_c and agg_t:
        mw_c = sum(float(f["mw"]) for f in agg_c)
        mw_t = sum(float(f["mw"]) for f in agg_t)
        if abs(mw_c - mw_t) > 50:
            error("MW por CCAA (%.0f) != MW por tecnologia (%.0f)" % (mw_c, mw_t))

    if agg_o and agg_l:
        seg_o = sum(int(f["segmentos"]) for f in agg_o)
        seg_l = sum(int(f["segmentos"]) for f in agg_l)
        if seg_o != seg_l:
            error("agregado por operador (%d) != agregado por tension (%d)" % (seg_o, seg_l))

    # 4. recibo
    ruta = os.path.join(DATOS, "_procedencia.json")
    if not os.path.exists(ruta):
        error("falta datos/_procedencia.json (ejecuta scripts/descargar.py)")
    else:
        p = json.load(open(ruta, encoding="utf-8"))
        for f in p.get("ficheros", []):
            if not str(f.get("url", "")).startswith("http"):
                error("_procedencia.json: %s sin URL" % f.get("fichero"))

    # 4b. conteos de OSM (foto completa)
    ruta_c = os.path.join(DATOS, "conteos_osm_20261116.json")
    if not os.path.exists(ruta_c):
        error("falta datos/conteos_osm_20261116.json")
    else:
        c = json.load(open(ruta_c, encoding="utf-8"))
        if not c.get("conteos"):
            error("conteos_osm: sin bloque 'conteos'")
        if not str(c.get("capturado", ""))[:4] == "2026":
            error("conteos_osm: sin fecha de captura creible")

    # 4c. capas OSM opcionales: si existen, no pueden estar vacias
    for capa in ("gasoductos", "presas", "desaladoras"):
        ruta_g = os.path.join(DATOS, capa + ".geojson")
        if os.path.exists(ruta_g):
            try:
                n = len(json.load(open(ruta_g, encoding="utf-8")).get("features", []))
            except Exception:
                error("datos/%s.geojson: no se puede leer" % capa)
                continue
            if n == 0:
                error("datos/%s.geojson: existe pero esta vacio (0 features)" % capa)

    # 4d. recibo de capas oficiales y capas que usa el visor
    ra = os.path.join(DATOS, "oficial", "_recibo_oficial.json")
    if not os.path.exists(ra):
        error("falta datos/oficial/_recibo_oficial.json (ejecuta scripts/capas_oficiales.py)")
    else:
        rec = json.load(open(ra, encoding="utf-8"))
        if len(rec.get("capas", [])) < 17:
            error("recibo de capas oficiales: solo %d capas" % len(rec.get("capas", [])))
        for capa in rec.get("capas", []):
            if capa.get("features", 0) == 0:
                error("oficial/%s: 0 features" % capa.get("id"))
        usadas = ["desaladoras", "nuclear", "gas-regasificacion", "gas-almacenamiento",
                  "agua-embalsada", "red-electrica", "conducciones-combustible"]
        for u in usadas:
            if not os.path.exists(os.path.join(DATOS, "oficial", u + ".geojson")):
                error("falta datos/oficial/%s.geojson (lo usa el visor)" % u)

    # 4e. capas de transporte (visor Hermes)
    rh = os.path.join(DATOS, "hermes", "_recibo_hermes.json")
    if not os.path.exists(rh):
        error("falta datos/hermes/_recibo_hermes.json (ejecuta scripts/hermes.py)")
    else:
        rec = json.load(open(rh, encoding="utf-8"))
        if len(rec.get("capas", [])) < 5:
            error("recibo de Hermes: solo %d capas" % len(rec.get("capas", [])))
        for capa in rec.get("capas", []):
            if capa.get("features", 0) == 0:
                error("hermes/%s: 0 features" % capa.get("id"))
            if not os.path.exists(os.path.join(DATOS, "hermes", capa["id"] + ".geojson")):
                error("falta datos/hermes/%s.geojson" % capa["id"])

    # 4f. geometrias simplificadas del visor
    rec = os.path.join(DATOS, "simplificado", "_recibo.json")
    if not os.path.exists(rec):
        error("falta datos/simplificado/_recibo.json (ejecuta scripts/simplificar.py)")
    else:
        r = json.load(open(rec, encoding="utf-8"))
        tot_a = sum(c["vertices_antes"] for c in r["capas"])
        tot_d = sum(c["vertices_despues"] for c in r["capas"])
        if tot_d >= tot_a:
            error("simplificar no reduce vertices (%d -> %d)" % (tot_a, tot_d))
        print("  simplificado ............... %d -> %d vertices (-%.0f%%)"
              % (tot_a, tot_d, 100 * (1 - tot_d / tot_a)))

    # 4g. procedencia de cada capa del visor
    fv = os.path.join(DATOS, "fuentes.json")
    if not os.path.exists(fv):
        error("falta datos/fuentes.json (ejecuta scripts/fuentes_visor.py)")
    else:
        d = json.load(open(fv, encoding="utf-8"))
        if d.get("total_capas", 0) < 30:
            error("fuentes.json: solo %d capas" % d.get("total_capas", 0))
        sin = [k for k, v in d.get("capas", {}).items() if not v.get("fuente")]
        if sin:
            error("fuentes.json: %d capas sin fuente (%s)" % (len(sin), ", ".join(sin[:5])))
        print("  procedencia de datos ........ %d capas documentadas" % d.get("total_capas", 0))

    # 5. visor
    for f in ("index.html", "README.md"):
        if not os.path.exists(os.path.join(RAIZ, f)):
            error("falta %s" % f)

    print("=" * 58)
    print(" OPENINFRAES · VALIDADOR")
    print("=" * 58)
    print("  GeoJSON .............. %s lineas / %s plantas" %
          (len(lineas) if lineas else "-", len(plantas) if plantas else "-"))
    print("  CSV agregados ........ %d" % len([1 for f in os.listdir(DATOS) if f.endswith(".csv")]))
    if errores:
        print("-" * 58)
        for e in errores:
            print("  x " + e)
        print(" RESULTADO: ROJO")
        return 1
    print(" RESULTADO: VERDE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
