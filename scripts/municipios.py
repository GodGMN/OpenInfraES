#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Municipios de España: polígonos oficiales + población del padrón, cruzados por CÓDIGO.

Dos fuentes, cada una en lo que es buena:

  geometría   Eurostat GISCO · LAU (Local Administrative Units), versión 1M.
              Es la capa administrativa oficial europea y trae el código INE en `LAU_ID`
              (5 dígitos) — por eso el cruce va por código y no por nombre.
  población   INE · Padrón municipal continuo (Tempus3, tabla 29005, sin clave).
              Se pide por API cada vez que se regenera; el fichero no se versiona en crudo.

El WFS del IGN (`wfs-inspire/unidades-administrativas`) era la primera opción, pero su
GetCapabilities no publica FeatureTypeList y devuelve 400 a cualquier `typeNames`: se
comprobó y se descartó (ver docs/municipios.md).

    python scripts/municipios.py                 # descarga LAU si falta y regenera
    python scripts/municipios.py --lau ruta.geojson

Escribe:
    datos/municipios.geojson        capa del visor (simplificada, con población y tramo)
    datos/municipios_recibo.json    recibo: conteos, cruces y validaciones

Sale con código 1 si una validación dura falla (códigos repetidos, área fuera de rango,
población que no cuadra con la del país). Una capa que no cuadra no se escribe a medias.
"""
import argparse
import json
import math
import os
import re
import sys
import unicodedata
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
TMP = os.environ.get("TMPDIR") or os.environ.get("TEMP") or "/tmp"

LAU_URL = ("https://gisco-services.ec.europa.eu/distribution/v2/lau/geojson/"
           "LAU_RG_01M_2021_4326.geojson")
INE_PADRON = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/29005?nult=1"
INE_PROV = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2852?nult=1"

# superficie oficial de España (IGN): 505.990 km². Tolerancia del 2 % para la suma de municipios.
SUPERFICIE_ES = 505990.0
POBLACION_ES_MIN, POBLACION_ES_MAX = 47_000_000, 50_000_000

ARTICULOS = {"el", "la", "los", "las", "lo", "l", "es", "sa", "s", "a", "o", "os", "as",
             "de", "del", "dels", "d", "en", "y", "i", "e"}


def sin_acentos(t):
    return unicodedata.normalize("NFD", t or "").encode("ascii", "ignore").decode()


def norm_nombre(t):
    """Nombre comparable: sin acentos, sin artículos ni preposiciones, sin puntuación.

    «Coruña, A» / «A Coruña» / «L'Hospitalet de Llobregat» / «Hospitalet de Llobregat, L'»
    tienen que caer en la misma clave, o el cruce pierde registros en silencio.
    """
    t = sin_acentos(t).lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    pal = [p for p in t.split() if p and p not in ARTICULOS]
    return " ".join(pal)


def esfera_km2(geom):
    """Área esférica de un Polygon/MultiPolygon, en km², restando los huecos."""
    R = 6371.0088
    def anillo(pts):
        a = 0.0
        for i in range(len(pts) - 1):
            lo1, la1 = math.radians(pts[i][0]), math.radians(pts[i][1])
            lo2, la2 = math.radians(pts[i + 1][0]), math.radians(pts[i + 1][1])
            a += (lo2 - lo1) * (2 + math.sin(la1) + math.sin(la2))
        return abs(a * R * R / 2)
    t, c = geom["type"], geom["coordinates"]
    if t == "Polygon":
        anillos = [c]
    else:
        anillos = c
    total = 0.0
    for poly in anillos:
        total += anillo(poly[0])
        for hueco in poly[1:]:
            total -= anillo(hueco)
    return total


def dp(pts, tol):
    """Douglas-Peucker iterativo (pila explícita): un anillo grande desborda la recursión."""
    n = len(pts)
    if n < 3:
        return pts
    keep = [False] * n
    keep[0] = keep[-1] = True
    pila = [(0, n - 1)]
    t2 = tol * tol
    while pila:
        i, j = pila.pop()
        if j <= i + 1:
            continue
        x1, y1 = pts[i][0], pts[i][1]
        dx, dy = pts[j][0] - x1, pts[j][1] - y1
        dd = dx * dx + dy * dy
        mejor, idx = -1.0, -1
        for k in range(i + 1, j):
            px, py = pts[k][0] - x1, pts[k][1] - y1
            if dd > 0:
                t = max(0.0, min(1.0, (px * dx + py * dy) / dd))
            else:
                t = 0.0
            ex, ey = px - t * dx, py - t * dy
            d2 = ex * ex + ey * ey
            if d2 > mejor:
                mejor, idx = d2, k
        if mejor > t2:
            keep[idx] = True
            pila.append((i, idx))
            pila.append((idx, j))
    return [p for p, k in zip(pts, keep) if k]


def simplificar(geom, tol):
    t, c = geom["type"], geom["coordinates"]
    def simp_anillo(pts):
        pts = dp(pts, tol)
        if len(pts) < 4:                     # un anillo de 3 puntos no es un polígono
            return None
        if pts[0] != pts[-1]:
            pts = pts + [pts[0]]
        return pts
    if t == "Polygon":
        anillos = [simp_anillo(c[0])]
        anillos += [simp_anillo(h) for h in c[1:]]
        anillos = [a for a in anillos if a]
        return {"type": "Polygon", "coordinates": anillos} if anillos else None
    polys = []
    for poly in c:
        pri = simp_anillo(poly[0])
        if not pri:
            continue
        polys.append([pri] + [x for x in (simp_anillo(h) for h in poly[1:]) if x])
    if not polys:
        return None
    return {"type": "MultiPolygon", "coordinates": polys}


def bajar(url, destino):
    print("  bajando %s" % url[:80])
    req = urllib.request.Request(url, headers={"User-Agent": "OpenInfraES/1.0 (datos abiertos)"})
    with urllib.request.urlopen(req, timeout=300) as r, open(destino, "wb") as fh:
        fh.write(r.read())


def padron():
    """{nombre_normalizado: (población, año)} desde el padrón continuo del INE (API, sin clave)."""
    import urllib.parse
    print("  INE · padrón municipal (tabla 29005)")
    req = urllib.request.Request(INE_PADRON, headers={"User-Agent": "OpenInfraES/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        series = json.loads(r.read().decode("utf-8"))
    salida, dup = {}, 0
    for sr in series:
        nom = sr.get("Nombre") or ""
        bajo = nom.lower()
        # «Ababuj. Total. Total habitantes. Personas.» — la segunda dimensión es el sexo:
        # sin exigir «. total.» se cuela la fila de Hombres/Mujeres y la suma se va a la mitad.
        if "total habitantes" not in bajo or ". total." not in bajo:
            continue
        municipio = nom.split(".")[0].strip()
        datos = sr.get("Data") or []
        if not datos or datos[-1].get("Valor") is None:
            continue
        ultimo = datos[-1]
        clave = norm_nombre(municipio)
        if not clave:
            continue
        valor = (float(ultimo["Valor"]), int(ultimo.get("Anyo") or 0))
        if clave in salida:
            dup += 1
            if salida[clave][0] != valor[0]:
                salida[clave] = ("AMBIGUO", 0)     # mismo nombre en dos provincias
            continue
        salida[clave] = valor
    print("     %d municipios con padrón (%d claves duplicadas)" % (len(salida), dup))
    return salida


def provincias_ine():
    """{cod_ine_provincia: población} del INE, para validar la suma municipal por provincia."""
    print("  INE · población por provincia (tabla 2852)")
    req = urllib.request.Request(INE_PROV, headers={"User-Agent": "OpenInfraES/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        series = json.loads(r.read().decode("utf-8"))
    salida = {}
    for sr in series:
        datos = sr.get("Data") or []
        if not datos or datos[-1].get("Valor") is None:
            continue
        cod = str(sr.get("COD") or "")
        salida[cod] = float(datos[-1]["Valor"])
    return salida


def main():
    ap = argparse.ArgumentParser(description="Capa de municipios con población")
    ap.add_argument("--lau", help="GeoJSON LAU ya descargado (si no, se baja)")
    ap.add_argument("--tol", type=float, default=0.003, help="tolerancia de simplificación en grados")
    a = ap.parse_args()

    lau = a.lau or os.path.join(TMP, "lau.geojson")
    if not os.path.exists(lau):
        bajar(LAU_URL, lau)
    print("  leyendo %s" % lau)
    d = json.load(open(lau, encoding="utf-8"))
    es = [f for f in d["features"] if (f.get("properties") or {}).get("CNTR_CODE") == "ES"]
    del d
    print("  municipios en la fuente: %d" % len(es))

    pob = padron()

    # código de provincia → nombre, desde la capa de provincias que ya está en el repo
    prov = {}
    ruta_prov = os.path.join(DATOS, "nuts3_es.geojson")
    if os.path.exists(ruta_prov):
        for f in json.load(open(ruta_prov, encoding="utf-8")).get("features", []):
            pr2 = f.get("properties") or {}
            cod = str(pr2.get("cod_ine") or "").zfill(2)
            if cod and pr2.get("nombre"):
                prov[cod] = pr2["nombre"]
    print("  provincias para el cruce: %d" % len(prov))

    salida, recibo_mun = [], []
    sin_padron = 0
    area_suma = 0.0
    pob_suma = 0.0
    vertices_antes = vertices_despues = 0
    for f in es:
        pr = f["properties"]
        cod = str(pr.get("LAU_ID") or "").strip()
        if len(cod) == 4:
            cod = "0" + cod                      # el INE publica 5 dígitos
        nombre = pr.get("LAU_NAME") or pr.get("NAME_LATN") or ""
        clave = norm_nombre(nombre)
        p, anio = pob.get(clave, (None, None))
        fuente_pob = "INE · padrón"
        if p == "AMBIGUO":
            p = None                          # nombre compartido por varios municipios
        if p is None:
            p, anio, fuente_pob = pr.get("POP_2021"), 2021, \
                ("GISCO 2021 (nombre ambiguo)" if clave in pob else "GISCO 2021 (sin padrón)")
            sin_padron += 1
        area_oficial = float(pr.get("AREA_KM2") or 0)
        g = simplificar(f["geometry"], a.tol)
        if not g:
            continue
        area_geo = esfera_km2(g)
        area_suma += area_oficial
        pob_suma += float(p or 0)
        vertices_antes += sum(len(r) for poly in (
            [f["geometry"]["coordinates"]] if f["geometry"]["type"] == "Polygon"
            else f["geometry"]["coordinates"]) for r in poly)
        vertices_despues += sum(len(r) for poly in (
            [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]) for r in poly)
        recibo_mun.append({
            "cod_ine": cod, "nombre": nombre,
            "poblacion": float(p or 0), "anio_poblacion": anio, "poblacion_fuente": fuente_pob,
            "area_km2": round(area_oficial, 2), "area_geometria_km2": round(area_geo, 2),
            "desvio_area_pct": round(100 * (area_geo - area_oficial) / area_oficial, 2) if area_oficial else None,
        })
        salida.append({"type": "Feature", "properties": {
            "cod_ine": cod, "nombre": nombre, "poblacion": p, "anio_poblacion": anio,
            "poblacion_fuente": fuente_pob, "area_km2": round(area_oficial, 2),
            "provincia": cod[:2], "provincia_nombre": prov.get(cod[:2]),
        }, "geometry": g})

    # ---- validaciones duras: si no cuadran, no se escribe nada ----
    fallos = []
    codigos = [x["properties"]["cod_ine"] for x in salida]
    repetidos = len(codigos) - len(set(codigos))
    if repetidos:
        fallos.append("%d códigos INE repetidos" % repetidos)
    if abs(area_suma - SUPERFICIE_ES) / SUPERFICIE_ES > 0.02:
        fallos.append("área %.0f km² no cuadra con la oficial %.0f (±2%%)" % (area_suma, SUPERFICIE_ES))
    if not (POBLACION_ES_MIN <= pob_suma <= POBLACION_ES_MAX):
        fallos.append("población sumada %.0f fuera del rango del país" % pob_suma)

    # tramos por cuartiles reales de población (los usa la leyenda del visor)
    vals = sorted(x["properties"]["poblacion"] for x in salida if x["properties"]["poblacion"])
    cortes = [vals[int(len(vals) * q)] for q in (0.25, 0.5, 0.75)] if vals else []
    etiquetas = ["bajo", "medio-bajo", "medio-alto", "alto"]
    colores = ["#1d4ed8", "#0891b2", "#f59e0b", "#b91c1c"]
    for x in salida:
        p = x["properties"]["poblacion"] or 0
        i = 0 if p <= cortes[0] else 1 if p <= cortes[1] else 2 if p <= cortes[2] else 3
        x["properties"]["tramo_poblacion"] = etiquetas[i]
        x["properties"]["color"] = colores[i]

    recibo = {
        "capa": "municipios",
        "titulo": "Municipios con población",
        "geometria": "Eurostat GISCO · LAU 1M (LAU_RG_01M_2021_4326)",
        "geometria_url": LAU_URL,
        "geometria_organismo": "Eurostat · GISCO (unidades administrativas locales)",
        "poblacion": "INE · Padrón municipal continuo (tabla 29005)",
        "poblacion_url": INE_PADRON,
        "poblacion_organismo": "INE",
        "licencia": "© EuroGeographics (GISCO) · INE datos abiertos",
        "jerarquia": 1,
        "descargado": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "anio_padron": max([x["properties"]["anio_poblacion"] or 0 for x in salida]),
        "features": len(salida),
        "codigos_ine_unicos": len(set(codigos)),
        "sin_padron": sin_padron,
        "area_suma_km2": round(area_suma, 1),
        "poblacion_suma": round(pob_suma, 0),
        "tolerancia_grados": a.tol,
        "vertices": {"antes": vertices_antes, "despues": vertices_despues,
                     "reduccion_pct": round(100 * (1 - vertices_despues / max(1, vertices_antes)), 1)},
        "cortes": {"municipios_poblacion": [round(c) for c in cortes]},
        "fallos": fallos,
        "municipios": sorted(recibo_mun, key=lambda x: x["cod_ine"]),
    }

    if fallos:
        for f in fallos:
            print("  [X] " + f)
        print("  no se escribe: la capa no cuadra")
        return 1

    geo = os.path.join(DATOS, "municipios.geojson")
    json.dump({"type": "FeatureCollection", "features": salida},
              open(geo, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(recibo, open(os.path.join(DATOS, "municipios_recibo.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("  %d municipios · %.0f km² · %.0f hab (padrón %s)"
          % (len(salida), area_suma, pob_suma, recibo["anio_padron"]))
    print("  sin padrón (se usa GISCO 2021): %d" % sin_padron)
    print("  vértices %d -> %d (-%.0f%%) · %.1f MB"
          % (vertices_antes, vertices_despues, recibo["vertices"]["reduccion_pct"],
             os.path.getsize(geo) / 1e6))
    print("  datos/municipios.geojson + municipios_recibo.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
