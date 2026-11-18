# -*- coding: utf-8 -*-
"""Genera datos/fuentes.json: la procedencia de cada capa del visor.

Todo sale de los recibos reales (no se escribe a mano): capas oficiales, visor Hermes, OSM agua,
Overpass y el recibo de simplificacion. El visor pinta esta tabla en el panel 'Fuentes'.
"""
import datetime
import json
import os

DATOS = "C:/Users/d_ant/Projects/OpenInfraES/datos"
HOY = datetime.date.today().isoformat()

# cada capa, a su organismo oficial. Sin agregadores.
OFICIAL = {
    "parques-eolicos": ("MITECO", "https://www.miteco.gob.es", "Registro de instalaciones de producción"),
    "plantas-solares": ("MITECO", "https://www.miteco.gob.es", "Registro de instalaciones de producción"),
    "gas-regasificacion": ("Enagás", "https://www.enagas.es", "Plantas de regasificación declaradas"),
    "gas-almacenamiento": ("Enagás", "https://www.enagas.es", "Almacenamientos subterráneos"),
    "gas-interconexiones": ("Enagás", "https://www.enagas.es", "Interconexiones internacionales"),
    "refinerias": ("CORES", "https://www.cores.es", "Refinerías del sistema petrolífero"),
    "almacenamiento-petrolifero": ("CORES", "https://www.cores.es", "Almacenamiento de productos petrolíferos"),
    "nuclear": ("CSN", "https://www.csn.es", "Centrales y reactores autorizados"),
    "residuos-radiactivos": ("ENRESA", "https://www.enresa.es", "Instalaciones de gestión de residuos"),
    "electricidad-interconexiones": ("REE", "https://www.ree.es", "Interconexiones del sistema eléctrico"),
    "red-electrica": ("IGN", "https://www.ign.es", "BTN Continua: red y recintos de subestación"),
    "conducciones-combustible": ("Enagás", "https://www.enagas.es", "Conducciones de gas"),
    "generacion-electrica-provincia": ("REE", "https://www.ree.es", "Reparto provincial de generación"),
    "hidrogeno-produccion": ("MITECO", "https://www.miteco.gob.es", "Proyectos de Interés Común (PCI)"),
    "agua-embalsada": ("MITECO", "https://www.miteco.gob.es", "Boletín Hidrológico, parte semanal"),
    "desaladoras": ("MITECO", "https://www.miteco.gob.es", "Instalaciones de desalación"),
    "hidrogeno-red": ("MITECO", "https://www.miteco.gob.es", "Red de hidrógeno (PCI)"),
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
    "eolicos": "parques-eolicos",
    "solares": "plantas-solares",
    "residuos": "residuos-radiactivos",
    "petrolifero": "almacenamiento-petrolifero",
    "h2red": "hidrogeno-red",
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
    oficial = leer("oficial/_recibo_oficial.json", {})
    for c in oficial.get("capas", []):
        org, url, metodo = OFICIAL.get(c["id"], ("sin declarar", "", ""))
        fuentes[c["id"]] = {
            "capa": c["id"], "titulo": c.get("titulo"),
            "fuente": org, "editor": org,
            "licencia": c.get("licencia"),
            "actualizado": c.get("verificado_a"),
            "descargado": HOY,
            "features": c.get("features"),
            "url": url,
            "metodo": metodo,
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
            org, url, metodo = OFICIAL.get(origen, ("sin declarar", "", ""))
            fuentes[capa] = {"capa": capa, "titulo": capa, "fuente": org,
                             "editor": org, "licencia": "CC BY 4.0",
                             "actualizado": None, "descargado": HOY,
                             "features": None, "url": url, "metodo": metodo}

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

    # carburantes y sismos: recibo propio de cada script
    import os as _os
    for capa, fich, fuente, editor, lic, url, met in (
        ("carburantes", "carburantes_recibo.json", "MITECO", "Secretaría de Estado de Energía",
         "Reutilización con atribución (Ley 37/2007)",
         "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/",
         "GET al JSON de estaciones terrestres; coma decimal"),
        ("demarcaciones", "demarcaciones_recibo.json", "MITECO", "MITECO · SIG",
         "Reutilización con atribución (Ley 37/2007)",
         "https://sig.miteco.gob.es/arcgis/rest/services/25830/aguaHidroDemarcaciones",
         "query ArcGIS REST, maxAllowableOffset 0.0005"),
        ("sismos", "sismos_recibo.json", "EMSC-CSEM", "seismicportal.eu",
         "abierta con atribución", "https://www.seismicportal.eu/fdsnws/event/1/query",
         "FDSN query con bbox de Espana"),
    ):
        r = leer(fich, {})
        if r:
            fuentes[capa] = {"capa": capa, "titulo": capa.capitalize(), "fuente": fuente,
                             "editor": editor, "licencia": lic,
                             "actualizado": r.get("fecha_dato") or r.get("desde"),
                             "descargado": HOY, "features": r.get("features"),
                             "url": url, "metodo": met}


    # --- NAP: paradas de GTFS (Metro, Cercanías, AVE) ---
    for capa, etq, titulo in (
        ("nap-metro", "metro-madrid", "Metro de Madrid (NAP)"),
        ("nap-cercanias", "cercanias-renfe", "Cercanías Renfe (NAP)"),
        ("nap-ave", "renfe-ave", "Renfe AVE y largo recorrido (NAP)"),
        ("nap-lineas-metro", "lineas_metro-madrid", "Líneas de Metro Madrid"),
        ("nap-lineas-cercanias", "lineas_cercanias-renfe", "Líneas de Cercanías"),
    ):
        r = leer("nap_%s_recibo.json" % etq, {})
        if r:
            fuentes[capa] = {
                "capa": capa, "titulo": titulo,
                "fuente": "NAP · MITMA", "editor": "NAP · MITMA",
                "licencia": "Reutilización con atribución (Ley 37/2007)",
                "actualizado": r.get("descargado") or None,
                "descargado": HOY,
                "features": r.get("paradas") or r.get("features"),
                "url": "https://nap.transportes.gob.es/api",
                "metodo": "GTFS-ZIP del NAP; cabecera `ApiKey`",
            }


    # --- DGT: NAP de Trafico (DATEX II) ---
    for capa, fich, titulo, ds in (
        ("dgt-camaras", "dgt_camaras_recibo.json", "Cámaras de tráfico (DGT)", "Cámaras DGT DATEX2 v3.7"),
        ("dgt-paneles", "dgt_paneles_recibo.json", "Paneles de mensaje variable", "Paneles DGT DATEX2 v3.7"),
        ("dgt-incidencias", "dgt_incidencias_recibo.json", "Incidencias en tiempo real", "Incidencias DGT DATEX2 v3.7"),
        ("dgt-electrolineras", "dgt_electrolineras_recibo.json", "Puntos de recarga eléctrica", "Puntos de recarga eléctrica para vehículos"),
    ):
        r = leer(fich, {})
        if r:
            fuentes[capa] = {
                "capa": capa, "titulo": titulo,
                "fuente": "DGT", "editor": "DGT · NAP de Tráfico",
                "licencia": "reutilización con atribución",
                "actualizado": r.get("actualizado") or None,
                "descargado": HOY,
                "features": r.get("features"),
                "url": "https://nap.dgt.es",
                "metodo": "DATEX II v3 (XML) del NAP de Tráfico · " + ds,
            }


    # --- GTFS-Realtime: vehiculos en vivo ---
    r = leer("gtfsrt_recibo.json", {})
    if r and r.get("feeds"):
        renfe = r["feeds"].get("renfe", {})
        fuentes["gtfsrt"] = {
            "capa": "gtfsrt", "titulo": "Vehículos en vivo (GTFS-RT)",
            "fuente": "Operadores (Renfe)", "editor": "GTFS-Realtime",
            "licencia": "condiciones del editor",
            "actualizado": (renfe.get("timestamp_feed") or "")[:19] or None,
            "descargado": r.get("descargado"),
            "features": renfe.get("vehiculos"),
            "url": renfe.get("url") or "https://gtfsrt.renfe.com/",
            "metodo": "protobuf GTFS-RT, refresco continuo",
        }


    # --- AEMET: zonas de aviso con geometria ---
    r = leer("aemet_zonas_recibo.json", {})
    if r:
        fuentes["aemet-zonas"] = {
            "capa": "aemet-zonas", "titulo": "Avisos AEMET (zonas)",
            "fuente": "AEMET", "editor": "AEMET · Meteoalerta",
            "licencia": "© AEMET, citar como autora",
            "actualizado": (r.get("elaborado") or "")[:8] or None,
            "descargado": r.get("descargado"),
            "features": r.get("features"),
            "url": r.get("url") or "https://www.aemet.es/es/eltiempo/prediccion/avisos",
            "metodo": "tar.gz de GeoJSON de la pagina de avisos (sin clave)",
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
