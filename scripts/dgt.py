# -*- coding: utf-8 -*-
"""DGT · Punto de Acceso Nacional de Tráfico y Movilidad (DATEX II).

`nap.dgt.es` es un catálogo **distinto** del NAP de transportes (aquel es de operadores de
transporte público; este, de tráfico). Tiene **37 conjuntos**, y su API CKAN responde `403`,
así que los recursos se obtienen de la URL DATEX II directa que publica cada dataset.

    python scripts/dgt.py --camaras
    python scripts/dgt.py --electrolineras

Formatos: DATEX II v3 en XML. El de electrolineras pesa **84 MB** y se parsea en streaming
(iterparse) o se come la memoria.
"""
import argparse
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos")
DGT = os.path.join(DEST, "dgt")
UA = {"User-Agent": "OpenInfraES/1.0", "Accept": "application/xml"}

RECURSOS = {
    "camaras": "https://nap.dgt.es/datex2/v3/dgt/DevicePublication/camaras_datex2_v37.xml",
    "electrolineras": ("https://nap.dgt.es/datex2/v3/miterd/"
                       "EnergyInfrastructureTablePublication/electrolineras.xml"),
}


def local(tag):
    return tag.split("}")[-1]


def descarga(nombre):
    os.makedirs(DGT, exist_ok=True)
    ruta = os.path.join(DGT, "%s.xml" % nombre)
    if os.path.exists(ruta) and os.path.getsize(ruta) > 1000:
        print("  ya descargado: %.1f MB" % (os.path.getsize(ruta) / 1e6))
        return ruta
    print("  descargando %s..." % nombre)
    req = urllib.request.Request(RECURSOS[nombre], headers=UA)
    with urllib.request.urlopen(req, timeout=900) as r, open(ruta, "wb") as f:
        while True:
            trozo = r.read(1 << 20)
            if not trozo:
                break
            f.write(trozo)
    print("  %.1f MB" % (os.path.getsize(ruta) / 1e6))
    return ruta


def texto(el, *nombres):
    """Primer descendiente cuyo tag local esté en `nombres`."""
    for hijo in el.iter():
        if local(hijo.tag) in nombres and (hijo.text or "").strip():
            return hijo.text.strip()
    return None


def camaras(ruta):
    feats = []
    for _, el in ET.iterparse(ruta, events=("end",)):
        if local(el.tag) != "device":
            continue
        lat = texto(el, "latitude")
        lon = texto(el, "longitude")
        if not lat or not lon:
            el.clear()
            continue
        try:
            y, x = float(lat), float(lon)
        except ValueError:
            el.clear()
            continue
        feats.append({"type": "Feature",
                      "geometry": {"type": "Point", "coordinates": [x, y]},
                      "properties": {
                          "carretera": texto(el, "roadName") or "",
                          "provincia": texto(el, "province") or "",
                          "destino": texto(el, "roadDestination") or "",
                          "km": texto(el, "kilometerPoint") or "",
                          "tipo": texto(el, "typeOfDevice") or "",
                          "actualizado": texto(el, "lastUpdateOfDeviceInformation") or "",
                          # deviceUrl es la FOTO de la camara, no un enlace informativo
                          "imagen": texto(el, "deviceUrl") or "",
                      }})
        el.clear()

    json.dump({"type": "FeatureCollection", "features": feats},
              open(os.path.join(DEST, "dgt_camaras.geojson"), "w", encoding="utf-8"),
              ensure_ascii=False)
    provincias = sorted({f["properties"]["provincia"] for f in feats if f["properties"]["provincia"]})
    recibo = {"fuente": "DGT · NAP de Tráfico", "dataset": "Cámaras DGT DATEX2 v3.7",
              "url": RECURSOS["camaras"], "licencia": "reutilización con atribución",
              "features": len(feats), "provincias": len(provincias),
              "ejemplo_provincias": provincias[:8]}
    json.dump(recibo, open(os.path.join(DEST, "dgt_camaras_recibo.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("  %d cámaras · %d provincias" % (len(feats), len(provincias)))
    for f in feats[:3]:
        p = f["properties"]
        print("   %-28s %s km %s" % (p["carretera"][:28], p["provincia"][:14], p["km"]))


def electrolineras(ruta):
    feats = []
    for _, el in ET.iterparse(ruta, events=("end",)):
        if local(el.tag) != "energyInfrastructureSite":
            continue
        lat = texto(el, "latitude")
        lon = texto(el, "longitude")
        if not lat or not lon:
            el.clear()
            continue
        try:
            y, x = float(lat), float(lon)
        except ValueError:
            el.clear()
            continue
        potencias = []
        conectores = 0
        for c in el.iter():
            if local(c.tag) == "maxPowerAtSocket":
                try:
                    potencias.append(float((c.text or "0").strip()))
                    conectores += 1
                except ValueError:
                    pass
        feats.append({"type": "Feature",
                      "geometry": {"type": "Point", "coordinates": [x, y]},
                      "properties": {
                          # OJO: `label` NO es el nombre del sitio, es el HORARIO
                          # ("Jueves (08:30 - 17:30)"). Llamarlo nombre llena el mapa de
                          # etiquetas que no identifican nada.
                          "nombre": texto(el, "name") or "",
                          "horario": texto(el, "label") or "",
                          "codigo_postal": texto(el, "postcode") or "",
                          "tipo_sitio": texto(el, "typeOfSite") or "",
                          "conectores": int(conectores),
                          "potencia_max_kw": (round(max(potencias) / 1000, 1)
                                              if potencias else None),
                          "actualizado": texto(el, "lastUpdated") or "",
                      }})
        el.clear()

    json.dump({"type": "FeatureCollection", "features": feats},
              open(os.path.join(DEST, "dgt_electrolineras.geojson"), "w", encoding="utf-8"),
              ensure_ascii=False)
    pot = [f["properties"]["potencia_max_kw"] for f in feats if f["properties"]["potencia_max_kw"]]
    recibo = {"fuente": "DGT · NAP de Tráfico",
              "dataset": "Puntos de recarga eléctrica para vehículos",
              "url": RECURSOS["electrolineras"],
              "features": len(feats), "con_conectores": len(pot),
              "potencia_max_kw": max(pot) if pot else None,
              "potencia_mediana_kw": sorted(pot)[len(pot) // 2] if pot else None}
    json.dump(recibo, open(os.path.join(DEST, "dgt_electrolineras_recibo.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)
    print("  %d electrolineras · %d con potencia declarada · máx %.0f kW"
          % (len(feats), len(pot), recibo["potencia_max_kw"] or 0))
    for f in feats[:3]:
        p = f["properties"]
        print("   %-30s %s kW" % (p["nombre"][:30], p["potencia_max_kw"]))


def main():
    ap = argparse.ArgumentParser(description="DGT · NAP de Tráfico (DATEX II)")
    ap.add_argument("--camaras", action="store_true")
    ap.add_argument("--electrolineras", action="store_true")
    a = ap.parse_args()
    if a.camaras:
        camaras(descarga("camaras"))
    elif a.electrolineras:
        electrolineras(descarga("electrolineras"))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
