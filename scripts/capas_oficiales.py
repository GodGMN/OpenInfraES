# -*- coding: utf-8 -*-
"""Descarga de las capas oficiales ya vectorizadas (IGN, MITECO, CSN, CORES, Enagas).com) las capas de energia y agua.

Licencia CC-BY-4.0. Se guarda el manifest filtrado como recibo (version, fecha de verificacion,
atribucion). No se transforma nada: se copia la capa tal cual y se agrega aparte.
"""
import json
import os
import time
import urllib.request

def _base():
    """URL del servicio que sirve las capas ya vectorizadas. Va en .env, no en el repo."""
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    for linea in open(ruta, encoding="utf-8"):
        if linea.startswith("CAPAS_VECTORIZADAS_URL="):
            return linea.split("=", 1)[1].strip()
    raise SystemExit("falta CAPAS_VECTORIZADAS_URL en .env")


BASE = _base()
UA = {"User-Agent": "OpenInfraES/1.0 (datos abiertos)"}
import os
DEST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datos", "oficial")

GRUPOS = {"renovables", "gas", "nuclear", "sistema-electrico", "agua", "hidrogeno"}


def main():
    os.makedirs(DEST, exist_ok=True)
    man_url = BASE + "/datos/manifest.json"
    man = json.load(urllib.request.urlopen(urllib.request.Request(man_url, headers=UA), timeout=120))
    seleccion = [c for c in man["capas"] if c.get("grupo") in GRUPOS]
    print("capas oficiales: %d | seleccionadas: %d" % (len(man["capas"]), len(seleccion)))
    print("release:", man.get("release"), "| schema:", man.get("schema_version"))
    print()

    recibo = {"fuente": "Capas oficiales (IGN, MITECO, CSN, CORES, Enagás) #er Viejo)",
              "url": BASE,
              "release": man.get("release"), "schema_version": man.get("schema_version"),
              "capas": []}

    for c in seleccion:
        fichero = c.get("fichero") or ("capas/%s.geojson" % c["id"])
        url = BASE + "/datos/" + fichero.lstrip("/")
        ruta = os.path.join(DEST, os.path.basename(fichero))
        cuerpo, estado = b"", 0
        for intento in range(6):
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=180) as r:
                    cuerpo = r.read()
                    estado = r.status
                if cuerpo:
                    break
                print("      (200 vacio, espero %ds)" % (20 * (intento + 1)))
            except Exception as e:
                print("      intento %d: %s" % (intento + 1, type(e).__name__))
            time.sleep(20 * (intento + 1))
        try:
            open(ruta, "wb").write(cuerpo)
            try:
                gj = json.loads(cuerpo.decode("utf-8"))
                n = len(gj.get("features", []))
                # una capa puede mezclar tipos: recogerlos TODOS, no solo el de la primera feature
                tipos = sorted({f["geometry"]["type"] for f in gj.get("features", []) if f.get("geometry")})
                tipo = "+".join(tipos) if tipos else "-"
            except Exception:
                n, tipo = 0, "?"
            recibo["capas"].append({"id": c["id"], "titulo": c.get("titulo"), "grupo": c.get("grupo"),
                                    "fichero": os.path.basename(fichero), "features": n,
                                    "geometria": tipo, "verificado_a": c.get("verificado_a"),
                                    "version": c.get("version"), "licencia": c.get("licencia"), "http": estado,
                                    "bytes": len(cuerpo)})
            print("  %-32s %5d %-12s %7.1f KB  %s" % (c["id"], n, tipo, len(cuerpo) / 1024,
                                                       (c.get("verificado_a") or "")[:10]))
        except Exception as e:
            print("  %-32s ERROR %s" % (c["id"], type(e).__name__))

    with open(os.path.join(DEST, "_recibo_oficial.json"), "w", encoding="utf-8") as fh:
        json.dump(recibo, fh, ensure_ascii=False, indent=1)
    print("\nrecibo: datos/oficial/_recibo_oficial.json")


if __name__ == "__main__":
    main()
