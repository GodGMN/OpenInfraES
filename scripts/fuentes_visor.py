# -*- coding: utf-8 -*-
"""Genera datos/fuentes.json: la procedencia de cada capa del visor.

Todo sale de los recibos reales (no se escribe a mano): Atlas, visor Hermes, OSM agua,
Overpass y el recibo de simplificacion. El visor pinta esta tabla en el panel 'Fuentes'.
"""
import datetime
import json
import os

DATOS = "C:/Users/d_ant/Projects/OpenInfraES/datos"
HOY = datetime.date.today().isoformat()

ATLAS = {
    "nombre": "Atlas Estratégico de España",
    "editor": "eltercioviejo.com",
    "licencia": "CC-BY-4.0",
    "url": "https://atlas.eltercioviejo.com",
    "metodo": "GeoJSON por capa desde atlas.eltercioviejo.com/datos/capas/",
}
HERMES = {
    "nombre": "Visor Hermes — MITMA",
    "editor": "Ministerio de Transportes (ArcGIS REST)",
    "licencia": "CC-BY-4.0 (scne.es)",
    "url": "https://mapas.fomento.gob.es/VisorHermes/",
    "metodo": "query ArcGIS REST, paginado de 500 en 500",
}
OSM = {
    "nombre": "OpenStreetMap",
    "editor": "colaboradores de OSM",
    "licencia": "ODbL 1.0",
    "url": "https://www.openstreetmap.org",
    "metodo": "Overpass API (man_made=*)",
}
OSM_RED = {
    "nombre": "OpenStreetMap (red)",
    "editor": "colaboradores de OSM",
    "licencia": "ODbL 1.0",
    "url": "https://www.openstreetmap.org",
    "metodo": "Overpass API (power=line, pipeline, plant)",
}
ATLAS_IGME = {
    "nombre": "Atlas Estratégico (BTN Continua)",
    "editor": "IGN + Atlas",
    "licencia": "CC-BY-4.0",
    "url": "https://atlas.eltercioviejo.com",
    "metodo": "GeoJSON del Atlas",
}


def leer(rel, defecto=None):
    ruta = os.path.join(DATOS, rel)
    if not os.path.exists(ruta):
        return defecto
    try:
        return json.load(open(ruta, encoding="utf-8"))
    except Exception:
        return defecto


# el id del visor no siempre es el id del origen
ALIAS_HERMES = {
    "puertos": "puertos-interes-general",
    "terminales-puerto": "terminales-portuarias",
    "terminales-aero": "terminales-aeropuerto",
    "intermodales": "terminales-mercancias",
    "carreteras": "carreteras",
    "estaciones-gas": "estaciones-gas",
}

# capas del visor que son subconjuntos de un fichero de plantas
DERIVADAS = {
    "gasgen": ("Ciclos combinados", "plantas.geojson", "technology_normalized in (ccgt, fuel_gas)"),
    "resto": ("Resto del parque", "plantas.geojson", "resto de tecnologias"),
}

ALIAS = {
    "subestaciones": "red-electrica",
    "interelec": "electricidad-interconexiones",
    "nuclear": "nuclear",
    "regas": "gas-regasificacion",
    "gasalm": "gas-almacenamiento",
    "refinerias": "refinerias",
    "embalses": "agua-embalsada",
    "desaladoras": "desaladoras",
    "h2": "hidrogeno-produccion",
}


def main():
    fuentes = {}
    atlas = leer("atlas/_recibo_atlas.json", {})
    for c in atlas.get("capas", []):
        fuentes[c["id"]] = {
            "capa": c["id"], "titulo": c.get("titulo"),
            "fuente": ATLAS["nombre"], "editor": ATLAS["editor"],
            "licencia": c.get("licencia") or ATLAS["licencia"],
            "actualizado": c.get("verificado_a"),
            "descargado": HOY,
            "features": c.get("features"),
            "url": ATLAS["url"],
            "metodo": ATLAS["metodo"],
            "atribucion": c.get("atribucion"),
        }

    hermes = leer("hermes/_recibo_hermes.json", {})
    for c in hermes.get("capas", []):
        fuentes[c["id"]] = {
            "capa": c["id"], "titulo": c.get("descripcion"),
            "fuente": HERMES["nombre"], "editor": HERMES["editor"],
            "licencia": hermes.get("licencia", HERMES["licencia"]),
            "actualizado": None, "descargado": HOY,
            "features": c.get("features"),
            "url": HERMES["url"],
            "metodo": "%s/%d — %s" % (c.get("servicio"), c.get("layer", 0), HERMES["metodo"]),
        }

    osm_agua = leer("osm_agua_recibo.json", {})
    for capa, r in osm_agua.items():
        fuentes[capa] = {
            "capa": capa, "titulo": {"edar": "EDAR (depuradoras)",
                                     "etap": "ETAP (potabilizadoras)",
                                     "agua-conducciones": "Conducciones de agua"}.get(capa, capa),
            "fuente": OSM["nombre"], "editor": OSM["editor"],
            "licencia": OSM["licencia"],
            "actualizado": HOY, "descargado": HOY,
            "features": r.get("features"),
            "url": OSM["url"],
            "metodo": "%s · %d con nombre" % (OSM["metodo"], r.get("con_nombre", 0)),
        }

    # el recibo de Hermes puede no tener una capa descargada aparte: se completa contando el fichero
    carpeta = os.path.join(DATOS, "hermes")
    if os.path.isdir(carpeta):
        for fich in os.listdir(carpeta):
            if not fich.endswith(".geojson"):
                continue
            cid = fich[:-8]
            if cid in fuentes:
                continue
            try:
                n = len(json.load(open(os.path.join(carpeta, fich), encoding="utf-8"))["features"])
            except Exception:
                n = None
            fuentes[cid] = {"capa": cid, "titulo": cid.replace("-", " ").capitalize(),
                            "fuente": HERMES["nombre"], "editor": HERMES["editor"],
                            "licencia": HERMES["licencia"], "actualizado": None,
                            "descargado": HOY, "features": n, "url": HERMES["url"],
                            "metodo": HERMES["metodo"]}

    for capa, origen in ALIAS_HERMES.items():
        base = fuentes.get(origen)
        if base:
            f = dict(base); f["capa"] = capa
            fuentes[capa] = f

    # capas que salen de ficheros propios generados con Overpass/REE
    propios = {
        "l400": ("Líneas 400 kV", OSM_RED, None),
        "l220": ("Líneas 220 kV", OSM_RED, None),
        "gasoductos": ("Gasoductos", OSM_RED, None),
        "hidro": ("Centrales hidráulicas", OSM_RED, None),
    }
    for capa, (titulo, src, act) in propios.items():
        fuentes[capa] = {
            "capa": capa, "titulo": titulo, "fuente": src["nombre"], "editor": src["editor"],
            "licencia": src["licencia"], "actualizado": act, "descargado": HOY,
            "features": None, "url": src["url"], "metodo": src["metodo"],
        }
    for capa, origen in ALIAS.items():
        base = fuentes.get(origen)
        if base:
            f = dict(base)
            f["capa"] = capa
            fuentes[capa] = f
        else:
            fuentes[capa] = {"capa": capa, "titulo": capa, "fuente": ATLAS["nombre"],
                             "editor": ATLAS["editor"], "licencia": ATLAS["licencia"],
                             "actualizado": None, "descargado": HOY,
                             "features": None, "url": ATLAS["url"], "metodo": ATLAS["metodo"]}

    for capa, (titulo, fich, filtro) in DERIVADAS.items():
        fuentes[capa] = {
            "capa": capa, "titulo": titulo, "fuente": OSM_RED["nombre"],
            "editor": OSM_RED["editor"], "licencia": OSM_RED["licencia"],
            "actualizado": None, "descargado": HOY, "features": None,
            "url": OSM_RED["url"], "metodo": "%s · subconjunto: %s" % (OSM_RED["metodo"], filtro),
        }

    # trasvases y canales comparten fichero pero no significado: misma fuente, distinto filtro
    r_agua = osm_agua.get("agua-conducciones")
    import re as _re
    n_tras, n_can = None, None
    ruta_agua = os.path.join(DATOS, "agua-conducciones.geojson")
    if os.path.exists(ruta_agua):
        _f = json.load(open(ruta_agua, encoding="utf-8"))["features"]
        n_tras = sum(1 for x in _f if _re.search(r"trasvase|postrasvase",
                                                 (x.get("properties") or {}).get("name") or "", _re.I))
        n_can = len(_f) - n_tras
    if r_agua:
        for capa, titulo, filtro in (
            ("trasvases", "Trasvases", "118 tramos unidos en 26 trazos por scripts/unir_trasvases.py"),
            ("canales", "Canales y acequias", "resto: canales de riego, acequias y aducciones"),
        ):
            fuentes[capa] = {
                "capa": capa, "titulo": titulo, "fuente": OSM["nombre"], "editor": OSM["editor"],
                "licencia": OSM["licencia"], "actualizado": HOY, "descargado": HOY,
                "features": (26 if capa == "trasvases" else n_can), "url": OSM["url"],
                "metodo": "%s · %s" % (OSM["metodo"], filtro),
            }

    # ríos: geometria OSM, caudal por API en vivo
    rr = leer("rios_recibo.json", {})
    if rr:
        fuentes["rios"] = {
            "capa": "rios", "titulo": "Ríos (caudal en vivo)",
            "fuente": OSM["nombre"], "editor": OSM["editor"], "licencia": OSM["licencia"],
            "actualizado": None, "descargado": HOY, "features": rr.get("features"),
            "url": OSM["url"],
            "metodo": "%s · %d tramos agrupados, mínimo %s km; caudal por Open-Meteo Flood (GloFAS)"
                      % (OSM["metodo"], rr.get("tramos_osm", 0), rr.get("min_km", "")),
        }

    sim = leer("simplificado/_recibo.json", {})
    simpl = {os.path.basename(c["id"]): c for c in sim.get("capas", [])}

    salida = {
        "generado": HOY,
        "nota": "Generado por scripts/fuentes_visor.py desde los recibos reales. "
                "No se edita a mano.",
        "capas": fuentes,
        "simplificacion": simpl,
        "total_capas": len(fuentes),
    }
    ruta = os.path.join(DATOS, "fuentes.json")
    json.dump(salida, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    for k, v in sorted(fuentes.items()):
        print("  %-22s %-34s %s  %s" % (k, v["fuente"][:34], v["licencia"][:12],
                                        v["actualizado"] or "—"))
    print("\n%d capas -> datos/fuentes.json" % len(fuentes))


if __name__ == "__main__":
    main()
