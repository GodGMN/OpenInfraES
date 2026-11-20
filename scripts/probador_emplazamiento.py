#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Probador de emplazamiento — SOLO LECTURA sobre OpenInfraES.

Responde: "si quiero poner una desaladora en este punto, ¿qué me dice el Atlas
y qué NO me puede decir?"  No escribe nada dentro del repo: lee datos/ y emite
un informe en el directorio de salida.

Uso:
    python probador_emplazamiento.py --lat 37.4067 --lon -1.5822 \
        --nombre "Aguilas" --radio 25 --out salida/
"""
import argparse, json, math, os, re, statistics, sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(REPO, "datos")

# ---------------------------------------------------------------- utilidades
def cargar(rel):
    p = os.path.join(DATOS, rel)
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print(f"[aviso] no se pudo leer {rel}: {e}", file=sys.stderr)
        return None

def haversine(lat1, lon1, lat2, lon2):
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(a))

def coords_de(geom, tope=400):
    """Extrae coordenadas de cualquier geometría, muestreando si es enorme."""
    t, c = geom["type"], geom["coordinates"]
    pts = []
    def walk(x):
        if isinstance(x, (int, float)) and len(pts) < tope:
            pass
        if isinstance(x, list) and len(x) == 2 and all(isinstance(v, (int, float)) for v in x):
            pts.append(x); return
        if isinstance(x, list):
            for y in x:
                walk(y)
    walk(c)
    if len(pts) > tope:
        paso = max(1, len(pts)//tope)
        pts = pts[::paso]
    return pts

def dist_min_km(geom, lat, lon):
    if geom["type"] == "Point":
        lo, la = geom["coordinates"][:2]
        return haversine(lat, lon, la, lo)/1000
    pts = coords_de(geom)
    if not pts:
        return None
    return min(haversine(lat, lon, p[1], p[0]) for p in pts)/1000

def dentro(lat, lon, geom):
    """Ray casting para Polygon/MultiPolygon."""
    def anillo(poly, lat, lon):
        inside = False
        j = len(poly)-1
        for i in range(len(poly)):
            xi, yi = poly[i][:2]; xj, yj = poly[j][:2]
            if ((yi > lat) != (yj > lat)) and (lon < (xj-xi)*(lat-yi)/((yj-yi) or 1e-12)+xi):
                inside = not inside
            j = i
        return inside
    c = geom["coordinates"]
    if geom["type"] == "Polygon":
        return anillo(c[0], lat, lon)
    return any(anillo(p[0], lat, lon) for p in c)

def norm_dem(s):
    """Normaliza el nombre de la demarcación: quita acentos, artículos y plurales.
    Las dos capas no escriben igual el mismo nombre («Cuenca Mediterránea Andaluza»
    frente a «CUENCAS MEDITERRANEAS ANDALUZAS»), y cruzar por texto pierde registros."""
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    ruido = {"cuenca", "cuencas", "hidrografica", "hidrologica", "de", "del", "la", "las", "el", "los", "y"}
    out = []
    for w in re.split(r"[^a-z0-9]+", s):
        if not w or w in ruido:
            continue
        if len(w) > 4 and w.endswith("s"):
            w = w[:-1]
        out.append(w)
    return " ".join(sorted(out))

def capa_meta(fuentes, cid):
    c = (fuentes.get("capas") or {}).get(cid) or {}
    return {k: c.get(k) for k in ("titulo", "fuente", "editor", "licencia", "actualizado", "descargado", "features")}

# ---------------------------------------------------------------- sondeos
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--nombre", default="emplazamiento")
    ap.add_argument("--radio", type=float, default=25.0, help="radio de influencia en km")
    ap.add_argument("--out", default=os.path.join(REPO, "casos"),
                    help="carpeta de salida (una por emplazamiento)")
    a = ap.parse_args()
    lat, lon, R = a.lat, a.lon, a.radio
    os.makedirs(a.out, exist_ok=True)

    fuentes = cargar("fuentes.json") or {"capas": {}}
    cat = cargar("catalogo.json") or {}
    res = {"punto": {"nombre": a.nombre, "lat": lat, "lon": lon}, "radio_km": R,
           "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"), "bloques": []}

    def bloque(clave, titulo, estado, datos, capas=(), nota=""):
        res["bloques"].append({"clave": clave, "titulo": titulo, "estado": estado,
                               "datos": datos, "capas": list(capas), "nota": nota})

    # 1. Desaladoras existentes -------------------------------------------
    g = cargar("oficial/desaladoras.geojson")
    if g:
        cercanas = []
        for f in g["features"]:
            d = dist_min_km(f["geometry"], lat, lon)
            p = f["properties"]
            if d is not None:
                cercanas.append({"nombre": p.get("nombre"), "km": round(d, 1),
                                 "m3_dia": p.get("capacidad_m3_dia"), "hm3_anio": p.get("capacidad_hm3_anio"),
                                 "fase": p.get("fase"), "en_servicio": p.get("en_servicio_desde"),
                                 "demarcacion": p.get("demarcacion"), "geo_precision": p.get("geo_precision"),
                                 "id": f.get("id")})
        cercanas.sort(key=lambda x: x["km"])
        en_radio = [c for c in cercanas if c["km"] <= R]
        bloque("desaladoras", "Desaladoras existentes", "ok" if cercanas else "vacio",
               {"en_radio": en_radio, "mas_cercana": cercanas[0] if cercanas else None,
                "total_espana": len(g["features"])},
               ["desaladoras"],
               "Coordenada de precisión municipal en origen: la distancia es al núcleo, no a la planta.")

    # 2. Demarcación hidrográfica y población -----------------------------
    g = cargar("demarcaciones.geojson")
    dem = None
    if g:
        for f in g["features"]:
            if dentro(lat, lon, f["geometry"]):
                dem = f["properties"].get("nom_demar"); break
        bloque("demarcacion", "Demarcación hidrográfica", "ok" if dem else "vacio", {"nombre": dem},
               ["demarcaciones"])

    for clave, fichero, cid, etiq in [("poblacion_provincia", "nuts3_es.geojson", "ine-provincias", "Provincia"),
                                      ("poblacion_ccaa", "nuts2_es.geojson", "ine-ccaa", "Comunidad")]:
        g = cargar(fichero)
        if not g: continue
        hallado = None
        for f in g["features"]:
            if dentro(lat, lon, f["geometry"]):
                hallado = f["properties"]; break
        bloque(clave, f"Población ({etiq.lower()})", "parcial" if hallado else "vacio",
               {"unidad": hallado, "nivel": etiq.lower()} if hallado else {},
               [cid], "El Atlas no tiene población por municipio: solo provincia y comunidad.")

    # 3. Embalses: capacidad y agua del parte ------------------------------
    g = cargar("oficial/agua-embalsada.geojson")
    if g:
        cerca = []
        for f in g["features"]:
            p = f["properties"]
            misma = bool(dem) and norm_dem(p.get("demarcacion")) == norm_dem(dem)
            if dem and p.get("demarcacion") and not misma:
                continue
            d = dist_min_km(f["geometry"], lat, lon)
            cerca.append({"nombre": p.get("nombre"), "km": round(d, 1),
                          "capacidad_hm3": p.get("capacidad_hm3"), "agua_hm3": p.get("agua_actual_hm3"),
                          "demarcacion": p.get("demarcacion"), "fecha": p.get("fecha_verificacion")})
        cap = sum(c["capacidad_hm3"] or 0 for c in cerca)
        agua = sum(c["agua_hm3"] or 0 for c in cerca)
        nacional = []
        for f in g["features"]:
            d = dist_min_km(f["geometry"], lat, lon)
            internacional = f["properties"]
            nacional.append({"nombre": internacional.get("nombre"), "km": round(d, 1),
                             "capacidad_hm3": internacional.get("capacidad_hm3"),
                             "agua_hm3": internacional.get("agua_actual_hm3"),
                             "demarcacion": internacional.get("demarcacion")})
        nacional.sort(key=lambda x: x["km"])
        bloque("embalses", "Embalses de la demarcación (parte del Boletín Hidrológico)", "ok" if cerca else "vacio",
               {"demarcacion": dem, "n": len(cerca),
                "los_5_mas_cercanos_de_espana": nacional[:5], "capacidad_total_hm3": round(cap, 1), "agua_total_hm3": round(agua, 1),
                "llenado_pct": round(100*agua/cap, 1) if cap else None,
                "los_5_mas_cercanos": sorted(cerca, key=lambda x: x["km"])[:5],
                "en_radio_km": [c for c in cerca if c["km"] <= R][:12]},
               ["embalses", "agua-embalsada"])

    # 4. Ríos y caudal ----------------------------------------------------
    g = cargar("rios.geojson")
    if g:
        cerca = []
        for f in g["features"]:
            p = f["properties"]
            d = dist_min_km(f["geometry"], lat, lon)
            cerca.append({"nombre": p.get("nombre"), "km": round(d, 1), "longitud_km": p.get("longitud_km"),
                          "punto_aforo": p.get("punto_aforo"), "tiene_caudal_en_fichero": any(k in ("caudal","caudal_m3s","caudal_medio") for k in p)})
        cerca.sort(key=lambda x: x["km"])
        bloque("rios", "Ríos y cauces", "parcial" if cerca else "vacio",
               {"en_radio": [c for c in cerca if c["km"] <= R][:8], "mas_cercano": cerca[0] if cerca else None},
               ["rios"],
               "El GeoJSON NO trae valor de caudal: solo un punto de aforo. El caudal se pide a "
               "Open-Meteo Flood (GloFAS, modelado, malla ~5 km) y solo 7 días atrás + 2 de previsión.")
        # caudal real del punto de aforo más cercano (misma consulta que hace el visor)
        if cerca and cerca[0].get("punto_aforo"):
            lo, la = cerca[0]["punto_aforo"][:2]
            try:
                import urllib.request
                url = ("https://flood-api.open-meteo.com/v1/flood?latitude=%s&longitude=%s"
                       "&daily=river_discharge&past_days=7&forecast_days=2" % (la, lo))
                with urllib.request.urlopen(url, timeout=25) as r:
                    d = json.load(r)
                dias = d["daily"]["time"]; vals = d["daily"]["river_discharge"]
                bloque("caudal_vivo", "Caudal del punto de aforo más cercano (GloFAS, MODELADO)", "parcial",
                       {"rio": cerca[0]["nombre"], "punto_aforo": [lo, la], "unidad": "m³/s",
                        "serie": {k: v for k, v in zip(dias, vals)},
                        "horizonte_dias": len(dias),
                        "ojo": "modelo de reanálisis/previsión, no aforo oficial; el horizonte es de 2 días"},
                       ["rios"], "No hay serie histórica ni escenario a futuro: el proyecto necesita años, no 9 días.")
            except Exception as e:
                bloque("caudal_vivo", "Caudal del punto de aforo más cercano (GloFAS)", "error",
                       {"error": str(e)}, ["rios"])

    # 5. Reúso: EDAR con agua regenerable ---------------------------------
    g = cargar("irewater_hib_edar.geojson")
    if g:
        en_radio = []
        for f in g["features"]:
            d = dist_min_km(f["geometry"], lat, lon)
            if d is not None and d <= R:
                p = f["properties"]
                en_radio.append({"municipio": p.get("municipio"), "km": round(d, 1),
                                 "capacidad": p.get("capacidad"), "qentrada_he": p.get("qentrada_he"),
                                 "poblacion_servida": p.get("poblacion_servida"),
                                 "volumen_reutilizable_m3": p.get("volumen_reutilizable_m3"),
                                 "demanda_potencial_riego": p.get("demanda_potencial_riego"),
                                 "impacto": p.get("indice_impacto_hidrologico")})
        en_radio.sort(key=lambda x: x["km"])
        bloque("reuso", "EDAR con agua regenerable (I-ReWater HUB)", "ok" if en_radio else "vacio",
               {"n_en_radio": len(en_radio), "total_espana": len(g["features"]), "muestra": en_radio[:8]},
               ["irewater-edar"])

    # 6. Infraestructura de agua de OSM -----------------------------------
    for cid, fichero, etiq in [("edar", "edar.geojson", "EDAR OSM"), ("etap", "etap.geojson", "ETAP OSM"),
                               ("canales", "simplificado/agua-conducciones.geojson", "Canales/conducciones"),
                               ("trasvases", "simplificado/trasvases-union.geojson", "Trasvases")]:
        g = cargar(fichero)
        if not g: continue
        n = 0; ejemplos = []
        for f in g["features"]:
            d = dist_min_km(f["geometry"], lat, lon)
            if d is not None and d <= R:
                n += 1
                if len(ejemplos) < 5:
                    ejemplos.append({"nombre": f["properties"].get("name") or f["properties"].get("nombre"),
                                     "km": round(d, 1)})
        bloque("osm_" + cid, f"{etiq} en el radio", "ok" if n else "vacio",
               {"n": n, "ejemplos": ejemplos, "total_espana": len(g["features"])}, [cid])

    # 7. Generación eléctrica cercana y precio ----------------------------
    g = cargar("plantas.geojson")
    if g:
        en_radio = []
        for f in g["features"]:
            d = dist_min_km(f["geometry"], lat, lon)
            if d is not None and d <= R:
                p = f["properties"]
                en_radio.append({"nombre": p.get("name"), "km": round(d, 1),
                                 "mw": p.get("installed_capacity_mw"),
                                 "tecnologia": p.get("technology_normalized")})
        en_radio.sort(key=lambda x: x["km"])
        bloque("generacion", "Generación eléctrica en el radio", "ok" if en_radio else "vacio",
               {"n": len(en_radio), "mw_total": round(sum(x["mw"] or 0 for x in en_radio), 1),
                "muestra": en_radio[:8]}, ["plantas"])

    omie = cargar("omie_precio.json")
    if omie and omie.get("horas"):
        v = [h["es"] for h in omie["horas"] if h.get("es") is not None]
        bloque("precio_luz", "Precio de la electricidad (OMIE, día del fichero)", "ok",
               {"fecha": omie.get("fecha"), "eur_mwh_medio": round(statistics.mean(v), 2),
                "min": min(v), "max": max(v), "n_cuartos": len(v)}, ["omie_precio"])

    # 8. Riesgo: AEMET y sismos -------------------------------------------
    g = cargar("aemet_zonas.geojson")
    if g:
        zona = None
        for f in g["features"]:
            if dentro(lat, lon, f["geometry"]):
                p = f["properties"]
                zona = {"zona": p.get("zona"), "nivel": p.get("nivel_txt"),
                        "fenomenos": p.get("fenomenos"), "avisos": p.get("avisos")}
                break
        if not zona:
            cand = []
            for f in g["features"]:
                d = dist_min_km(f["geometry"], lat, lon)
                cand.append((d, f["properties"]))
            cand.sort(key=lambda t: t[0])
            zona = {"zona": cand[0][1].get("zona"), "km_al_borde": round(cand[0][0], 1),
                    "nivel": cand[0][1].get("nivel_txt"), "fenomenos": cand[0][1].get("fenomenos")} if cand else None
        bloque("aemet", "Avisos AEMET de la zona", "ok" if zona else "vacio", {"zona": zona}, ["aemet-zonas"])

    g = cargar("sismos.geojson")
    if g:
        en_radio = []
        for f in g["features"]:
            d = dist_min_km(f["geometry"], lat, lon)
            if d is not None and d <= 150:
                p = f["properties"]
                en_radio.append({"magnitud": p.get("magnitud"), "km": round(d, 1),
                                 "hora": p.get("hora"), "lugar": p.get("lugar")})
        en_radio.sort(key=lambda x: -x["magnitud"] or 0)
        bloque("sismos", "Sismicidad a menos de 150 km", "ok" if en_radio else "vacio",
               {"n": len(en_radio), "mayores": en_radio[:5]}, ["sismos"])

    # 9. Salud del catálogo ------------------------------------------------
    res["catalogo"] = {"total": cat.get("total"), "resumen": cat.get("resumen"), "avisos": cat.get("avisos")}

    # Lo que el expediente pide y el dato abierto NO da. No se pinta como cero: se nombra.
    res["huecos"] = [
        {"dato": "población municipal del punto", "estado": "pendiente",
         "por_que": "no hay capa de municipios (A2); hoy solo provincia y comunidad autónoma"},
        {"dato": "serie histórica y tendencia de caudal", "estado": "por_sondear",
         "por_que": "CEDEX · Anuario de aforos: descarga en bloque, sin endpoint de consulta"},
        {"dato": "demanda agraria de la cuenca", "estado": "vacio",
         "por_que": "el capturador de I-ReWater devolvió 0 teselas en regadío"},
        {"dato": "masas de agua subterránea", "estado": "por_sondear",
         "por_que": "IDE-MITECO (agua): sin sondeo del servicio de descarga"},
        {"dato": "Red Natura 2000 y espacios protegidos", "estado": "por_sondear",
         "por_que": "Banco de Datos de la Naturaleza: falta resolver la distribución"},
        {"dato": "calidad y salinidad del agua", "estado": "por_sondear",
         "por_que": "Náyade solo publica aguas de baño"},
        {"dato": "batimetría y emisario de vertido", "estado": "por_sondear",
         "por_que": "no existe capa abierta"},
    ]
    # un bloque vacío se suma a la lista en vez de quedarse en un «vacio» que nadie lee
    for bl in res["bloques"]:
        if bl["estado"] == "vacio":
            res["huecos"].append({"dato": bl["titulo"], "estado": "vacio",
                                  "por_que": "la consulta no devolvió registros en el radio"})

    # 10. Metadatos de las capas usadas ------------------------------------
    usadas = sorted({c for b in res["bloques"] for c in b["capas"]})
    res["capas_usadas"] = {c: capa_meta(fuentes, c) for c in usadas}

    # ---------------------------------------------------------------- salida
    jp = os.path.join(a.out, "informe_emplazamiento.json")
    json.dump(res, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    L = [f"# Emplazamiento candidato: {a.nombre}  ({lat}, {lon})",
         f"Radio de influencia: {R:.0f} km · generado {res['generado']}", ""]
    for b in res["bloques"]:
        L.append(f"## [{b['estado'].upper():7s}] {b['titulo']}")
        if b["nota"]: L.append(f"> {b['nota']}")
        L.append("```json")
        L.append(json.dumps(b["datos"], ensure_ascii=False, indent=1)[:2600])
        L.append("```")
        L.append("")
    L += ["## Qué falta (declarado, no inventado)", "", "| dato | estado | por qué |", "|---|---|---|"]
    for hj in res["huecos"]:
        L.append("| %s | %s | %s |" % (hj["dato"], hj["estado"], hj["por_que"]))
    L.append("")

    if res["catalogo"].get("resumen"):
        L += ["## Catálogo", "```json", json.dumps(res["catalogo"]["resumen"], ensure_ascii=False, indent=1), "```", ""]
    L += ["## Capas usadas y su procedencia", "| capa | fuente | licencia | actualizado | descargado | features |",
          "|---|---|---|---|---|---|"]
    for c, m in res["capas_usadas"].items():
        L.append(f"| {c} | {m.get('fuente')} | {m.get('licencia')} | {m.get('actualizado')} | {m.get('descargado')} | {m.get('features')} |")
    mp = os.path.join(a.out, "informe_emplazamiento.md")
    open(mp, "w", encoding="utf-8").write("\n".join(L))
    print("JSON:", jp); print("MD  :", mp)
    return 0

if __name__ == "__main__":
    sys.exit(main())
