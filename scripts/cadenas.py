# -*- coding: utf-8 -*-
"""Cadenas de procedencia: quien produce el dato, quien lo publica y que fecha tiene cada cosa.

La pregunta que resuelve: si el visor toma el dato del Atlas, y el Atlas lo toma del
Boletín Hidrológico, ¿de cuándo es el dato? Aquí se separan tres fechas distintas:

  fecha_dato        cuando se midio el dato (la que declara el productor)
  fecha_publicacion cuando el agregador lo publico (verificado_a / release)
  fecha_descarga    cuando lo bajamos nosotros

Solo se escribe lo que esta documentado en el repo o en el propio dato. Donde el
productor no lo declara, se dice.
"""
import json
import os

DEST = "C:/Users/d_ant/Projects/OpenInfraES/datos"
HOY = "2026-11-16"

# capa -> (productor primario, como llega, nota)
CADENAS = {
    # --- Atlas Estrategico: los eslabones que el propio dato declara
    "embalses": ("MITECO — Boletín Hidrológico (parte semanal)", "Atlas Estratégico",
                 "El parte trae fecha propia en el campo fecha_dato; el Atlas la conserva."),
    "subestaciones": ("IGN — BTN Continua (Base Topográfica Nacional)", "Atlas Estratégico",
                      "El campo atribucion del dato dice: «Obra derivada de BTN Continua CC-BY 4.0 ign.es»."),
    "desaladoras": ("MITECO / Acuamed (instalaciones declaradas)", "Atlas Estratégico",
                    "El Atlas añade estado administrativo y verificación por registro."),
    "nuclear": ("Consejo de Seguridad Nuclear / propietarios", "Atlas Estratégico",
                "Potencia y tecnología por reactor; el estado se verifica por registro."),
    "regas": ("Enagás / operadores de planta", "Atlas Estratégico", ""),
    "gasalm": ("Enagás / operadores", "Atlas Estratégico", ""),
    "refinerias": ("Corporación de Reservas / operadores", "Atlas Estratégico", ""),
    "interelec": ("REE — operador del sistema", "Atlas Estratégico", ""),
    "h2": ("MITECO — Proyectos de Interés Común (PCI)", "Atlas Estratégico", ""),
    # --- capas propias de OpenInfraES
    "l400": ("Red Eléctrica de España (instalaciones) / mapeo OSM", "OpenInfraES ← OSM",
             "La tensión viene etiquetada en cada línea de OSM; no se cruza con REE."),
    "l220": ("Red Eléctrica de España (instalaciones) / mapeo OSM", "OpenInfraES ← OSM", ""),
    "gasoductos": ("Enagás / mapeo OSM", "OpenInfraES ← OSM", "Operador y presión según etiquetas de OSM."),
    "hidro": ("Propietarios de central / mapeo OSM + ELECTRA", "OpenInfraES ← OSM", ""),
    "gasgen": ("Propietarios / mapeo OSM", "OpenInfraES ← OSM", "Subconjunto de plantas.geojson."),
    "resto": ("Propietarios / mapeo OSM", "OpenInfraES ← OSM", "Subconjunto de plantas.geojson."),
    # --- MITMA
    "carreteras": ("MITMA — Inventario de la Red de Carreteras del Estado", "Visor Hermes (ArcGIS REST)",
                   "Fuente primaria: el propio ministerio. No hay intermediario."),
    "puertos": ("Puertos del Estado / autoridades portuarias", "Visor Hermes (ArcGIS REST)", ""),
    "terminales-puerto": ("Autoridades portuarias", "Visor Hermes (ArcGIS REST)", ""),
    "terminales-aero": ("Aena", "Visor Hermes (ArcGIS REST)", ""),
    "terminales-aero-pista": ("Aena", "Visor Hermes (ArcGIS REST)", ""),
    "intermodales": ("Adif / Puertos del Estado", "Visor Hermes (ArcGIS REST)", ""),
    "estaciones-gas": ("MITECO — registro de carburantes", "Visor Hermes (ArcGIS REST)",
                       "Los flags GNL/GNC/H2 son del registro; el visor filtra a 165 de 11.485."),
    # --- agua (OSM)
    "edar": ("Ayuntamientos / confederaciones (declarado en OSM)", "OpenInfraES ← OSM",
             "No es el inventario oficial del MITECO: es lo que está mapeado en OSM."),
    "etap": ("Confederaciones / ayuntamientos (declarado en OSM)", "OpenInfraES ← OSM", ""),
    "trasvases": ("Ministerio / confederaciones (trazado mapeado en OSM)", "OpenInfraES ← OSM",
                  "118 tramos unidos en 26 trazos. No existe capa oficial abierta."),
    "canales": ("Confederaciones hidráulicas / comunidades de regantes", "OpenInfraES ← OSM",
                "Acequias históricas: muchas con siglos de historia."),
    "agua-conducciones": ("Confederaciones y comunidades de regantes (mapeo OSM)",
                          "OpenInfraES ← OSM",
                          "Fichero crudo del que salen las capas Trasvases y Canales."),
    "rios": ("Confederaciones hidráulicas (geometría OSM)", "OpenInfraES ← OSM",
             "Caudal consultado en vivo a Open-Meteo Flood (GloFAS), que es MODELADO, no aforo."),
}


# ids del Atlas que comparten origen con su alias del visor
ALIAS_INVERSO = {
    "gas-regasificacion": "regas",
    "gas-almacenamiento": "gasalm",
    "electricidad-interconexiones": "interelec",
    "hidrogeno-produccion": "h2",
    "red-electrica": "subestaciones",
    "agua-embalsada": "embalses",
    "parques-eolicos": "hidro",
    "plantas-solares": "resto",
    "gas-interconexiones": "gasoductos",
    "almacenamiento-petrolifero": "refinerias",
    "residuos-radiactivos": "nuclear",
    "puertos-interes-general": "puertos",
    "terminales-portuarias": "terminales-puerto",
    "terminales-aeropuerto": "terminales-aero",
    "pistas-aeropuerto": "terminales-aero",
    "terminales-mercancias": "intermodales",
    "conducciones-combustible": "gasoductos",
    "hidrogeno-red": "h2",
    "generacion-electrica-provincia": "hidro",
}


def main():
    ruta = os.path.join(DEST, "fuentes.json")
    d = json.load(open(ruta, encoding="utf-8"))
    puestos = 0
    for capa, v in d["capas"].items():
        clave = capa if capa in CADENAS else ALIAS_INVERSO.get(capa)
        prod, via, nota = CADENAS.get(clave, (None, None, None))
        v["cadena"] = {
            "productor": prod or "no declarado por el editor",
            "publica": via or v.get("editor"),
            "consume": "OpenInfraES (descarga directa del fichero)",
            "nota": nota or "",
        }
        # tres fechas distintas, y ninguna se inventa
        v["fecha_dato"] = v.get("actualizado") if capa in ("embalses",) else None
        v["fecha_publicacion"] = v.get("actualizado")
        v["fecha_descarga"] = v.get("descargado")
        if prod:
            puestos += 1
    d["generado"] = HOY
    d["nota_cadena"] = ("Cada capa declara productor (quien genera el dato), publica (quien lo "
                        "sirve tal como lo consumimos) y consume (nosotros). Son tres fechas "
                        "distintas: la del dato, la de publicación y la de descarga.")
    json.dump(d, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("  %d capas, %d con cadena documentada" % (len(d["capas"]), puestos))
    for k in ("embalses", "subestaciones", "carreteras", "rios"):
        if k in d["capas"]:
            c = d["capas"][k]["cadena"]
            print("   %-14s %s -> %s" % (k, c["productor"][:44], c["publica"][:26]))
    sin = [k for k, v in d["capas"].items() if v["cadena"]["productor"].startswith("no declarado")]
    if sin:
        print("  sin productor declarado: %s" % ", ".join(sin[:8]))


if __name__ == "__main__":
    main()
