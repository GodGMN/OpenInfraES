# -*- coding: utf-8 -*-
"""AEMET · avisos meteorológicos CON geometría (zonas Meteoalerta).

Meteoalarm daba los avisos sin coordenadas. AEMET sí publica las **zonas de aviso como polígonos**,
sin clave: en la página de avisos hay un enlace a un `tar.gz` de GeoJSON que se regenera cada hora.

    https://www.aemet.es/es/eltiempo/prediccion/avisos
      -> /es/geojson/download/avisos/geojson_<epoch>.tar.gz
          r_D+0_<elaborado>_penbal_<...>.geojson   península y Baleares
          r_D+0_<elaborado>_can_<...>.geojson      Canarias

`r_D+0` es el aviso de hoy (D+0); el tar trae también D+1 y D+2. Los ficheros de menos de 300 bytes van
vacíos: esa área no tiene avisos.

    python scripts/aemet_geo.py
"""
import datetime
import io
import json
import os
import re
import tarfile
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos")
PAGINA = "https://www.aemet.es/es/eltiempo/prediccion/avisos"
UA = {"User-Agent": "Mozilla/5.0 (compatible; OpenInfraES/1.0)",
      "Accept-Language": "es-ES,es;q=0.9"}

# niveles de Meteoalerta
NIVEL = {0: ("sin aviso", "#64748b"), 1: ("amarillo", "#facc15"),
         2: ("naranja", "#fb923c"), 3: ("rojo", "#ef4444")}

FENOMENOS = {
    "1": "Viento", "2": "Lluvia", "3": "Nieve", "4": "Tormenta",
    "5": "Niebla", "6": "Rachas de viento", "7": "Polvo en suspensión",
    "8": "Aludes", "9": "Temperaturas máximas", "10": "Temperaturas mínimas",
    "11": "Riberas y desbordamientos", "12": "Incendios forestales",
    "13": "Fenómenos costeros", "14": "Tormenta tropical",
}


def baja(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def redondea(geo, dec=4):
    if isinstance(geo, list):
        return [redondea(x, dec) for x in geo]
    if isinstance(geo, float):
        return round(geo, dec)
    return geo


def main():
    html = baja(PAGINA).decode("iso-8859-15", "replace")
    m = re.search(r"(?:https://www\.aemet\.es)?/es/geojson/download/avisos/geojson_\d+\.tar\.gz", html)
    if not m:
        raise SystemExit("no encuentro el enlace del geojson de avisos en la página de AEMET")
    url = m.group(0)
    if url.startswith("/"):
        url = "https://www.aemet.es" + url
    print("  %s" % url)

    tar = baja(url, timeout=180)
    print("  %.1f MB" % (len(tar) / 1e6))

    feats, ficheros, elaborado = [], [], ""
    with tarfile.open(fileobj=io.BytesIO(tar), mode="r:gz") as tf:
        for mi in tf.getmembers():
            n = mi.name
            if not n.endswith(".geojson") or not n.startswith("r_D+0_"):
                continue
            if "_penbal_" not in n and "_can_" not in n:
                continue
            if mi.size < 300:          # vacío: sin avisos en esa área
                continue
            try:
                fc = json.loads(tf.extractfile(mi).read().decode("utf-8", "replace"))
            except Exception:
                continue
            ficheros.append(n)
            mm = re.search(r"r_D\+0_(\d{14})_", n)
            if mm and not elaborado:
                elaborado = mm.group(1)
            for ft in fc.get("features", []):
                p = ft.get("properties") or {}
                avisos = p.get("Avis_COCO") or []
                nivel = 0
                for a in avisos:
                    try:
                        nivel = max(nivel, int(a.get("nivel_num") or 0))
                    except (TypeError, ValueError):
                        pass
                if not nivel:
                    try:
                        nivel = int(p.get("Av_mayor") or p.get("Nivel_COCO") or 0)
                    except (TypeError, ValueError):
                        nivel = 0
                if not nivel:
                    continue                     # zonas sin aviso: no se pintan
                feats.append({
                    "type": "Feature",
                    "geometry": redondea(ft.get("geometry")),
                    "properties": {
                        "zona": p.get("Nombre_zona") or "",
                        "provincia": p.get("Provincia") or "",
                        "codigo": p.get("COD_Z") or "",
                        "nivel": nivel,
                        "nivel_txt": NIVEL.get(nivel, ("?", ""))[0],
                        "fenomenos": ", ".join(sorted({
                            FENOMENOS.get(a.get("fenomeno") or "", a.get("parametro") or "")
                            for a in avisos if a})),
                        "avisos": [{
                            "fenomeno": FENOMENOS.get(a.get("fenomeno") or "", a.get("parametro") or ""),
                            "nivel": a.get("nivel_num"),
                            "descripcion": (a.get("descripcion") or "")[:260],
                            "desde": a.get("onset_local") or "",
                            "hasta": a.get("expires_local") or "",
                        } for a in avisos],
                    }})

    json.dump({"type": "FeatureCollection", "features": feats},
              open(os.path.join(DEST, "aemet_zonas.geojson"), "w", encoding="utf-8"),
              ensure_ascii=False)

    por_nivel = {}
    for f in feats:
        k = f["properties"]["nivel_txt"]
        por_nivel[k] = por_nivel.get(k, 0) + 1
    recibo = {
        "fuente": "AEMET", "dataset": "Meteoalerta — zonas de aviso",
        "url": PAGINA, "url_geojson": url,
        "licencia": "© AEMET. Reproducción autorizada citando a AEMET como autora.",
        "elaborado": elaborado,
        "descargado": datetime.datetime.now().isoformat(timespec="seconds"),
        "ficheros": ficheros, "features": len(feats),
        "por_nivel": por_nivel,
        "geometria": True,
        "nota": "Zonas con aviso, como polígonos. Los ficheros de menos de 300 bytes van vacíos (sin aviso).",
    }
    json.dump(recibo, open(os.path.join(DEST, "aemet_zonas_recibo.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("  %d zonas con aviso · elaborado %s" % (len(feats), elaborado))
    for k, v in por_nivel.items():
        print("   %-10s %d" % (k, v))


if __name__ == "__main__":
    main()