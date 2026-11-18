# -*- coding: utf-8 -*-
"""AEMET · avisos meteorológicos (CAP) vía Meteoalarm.

AEMET OpenData exige clave para `avisos_cap`. **Meteoalarm** (EUMETNET, del que AEMET es el nodo
español) publica los mismos avisos en abierto:

    https://feeds.meteoalarm.org/api/v1/warnings/feeds-spain     JSON, ~1,9 MB, 351 avisos

Cada aviso trae `event`, `severity`, `onset`, `expires`, `headline`, `description` y el área
(`areaDesc`), **pero no coordenadas ni polígono**: las áreas son comarcas («Interior de Pontevedra»,
«Albarracín y Jiloca»), 233 distintas, y el feed no trae su geometría.

Por eso **no se pinta en el mapa**: se guarda como lista y se declara. Inventar un punto por comarca
sería peor que no tenerla.

    python scripts/aemet.py
"""
import datetime
import json
import os
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos")
URL = "https://feeds.meteoalarm.org/api/v1/warnings/feeds-spain"

NIVEL = {"Minor": "amarillo", "Moderate": "amarillo", "Severe": "naranja",
         "Extreme": "rojo", "Unknown": "sin nivel"}


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "OpenInfraES/1.0",
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())

    avisos = []
    for w in d.get("warnings", []):
        a = w.get("alert") or {}
        for info in (a.get("info") or []):
            # CAP viene en varios idiomas: sin filtrar, cada aviso se cuenta dos veces
            # ("vientos de nivel amarillo" y "Moderate wind warning").
            if not (info.get("language") or "es").lower().startswith("es"):
                continue
            areas = [x.get("areaDesc") for x in (info.get("area") or []) if x.get("areaDesc")]
            ev = (info.get("event") or "").strip()
            avisos.append({
                "evento": ev,
                "nivel": NIVEL.get(info.get("severity") or "", "sin nivel"),
                "severidad": info.get("severity") or "",
                "certeza": info.get("certainty") or "",
                "urgencia": info.get("urgency") or "",
                "desde": info.get("onset") or "",
                "hasta": info.get("expires") or "",
                "titular": (info.get("headline") or ev)[:150],
                "descripcion": (info.get("description") or "")[:400],
                "zonas": areas,
                "enviado": a.get("sent") or "",
                "emisor": info.get("senderName") or "AEMET",
            })

    # solo los vigentes: hasta vacio o futuro
    ahora = datetime.datetime.now(datetime.timezone.utc).isoformat()
    vigentes = [x for x in avisos if not x["hasta"] or x["hasta"] > ahora]

    # resumen por evento y nivel
    por_nivel = {}
    por_evento = {}
    for x in vigentes:
        por_nivel[x["nivel"]] = por_nivel.get(x["nivel"], 0) + 1
        clave = x["evento"].replace("Aviso de ", "").strip()
        por_evento[clave] = por_evento.get(clave, 0) + 1

    zonas = sorted({z for x in vigentes for z in x["zonas"]})
    salida = {
        "fuente": "AEMET",
        "via": "Meteoalarm (EUMETNET)",
        "url": URL,
        "descargado": datetime.datetime.now().isoformat(timespec="seconds"),
        "total": len(avisos),
        "vigentes": len(vigentes),
        "por_nivel": dict(sorted(por_nivel.items(), key=lambda kv: -kv[1])),
        "por_evento": dict(sorted(por_evento.items(), key=lambda kv: -kv[1])[:12]),
        "zonas": zonas,
        "geometria": False,
        "nota_geometria": ("El feed de Meteoalarm no publica polígonos ni coordenadas: las áreas son "
                           "comarcas (233 distintas). Sin geometría no se pinta en el mapa; se muestra "
                           "como lista en el panel de Riesgo."),
        "avisos": sorted(vigentes, key=lambda x: (x["nivel"] != "rojo", x["nivel"] != "naranja",
                                                  x["desde"]))[:80],
    }
    json.dump(salida, open(os.path.join(DEST, "aemet_avisos.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("  %d avisos · %d vigentes · %d zonas" % (len(avisos), len(vigentes), len(zonas)))
    for k, v in salida["por_nivel"].items():
        print("   %-12s %d" % (k, v))
    for k, v in list(salida["por_evento"].items())[:6]:
        print("   %-28s %d" % (k[:28], v))


if __name__ == "__main__":
    main()
