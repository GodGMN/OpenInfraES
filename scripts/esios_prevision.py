# -*- coding: utf-8 -*-
"""Previsión de demanda y eólica desde ESIOS (requiere token en .env).

Indicadores usados (verificados en el catálogo de 1.982):
    460  Previsión diaria de la demanda eléctrica peninsular
    541  Previsión de la producción eólica peninsular
(el 544 que probamos devuelve "Demanda prevista", no eólica: se descartó)

El token se lee de .env o del entorno. Nunca se escribe en el repo.
"""
import json
import os
import urllib.request
from datetime import date, timedelta

DESDE = "C:/Users/d_ant/Projects/OpenInfraES"
DEST = DESDE + "/datos"
UA = {"Accept": "application/json", "User-Agent": "OpenInfraES/1.0"}


def token():
    t = os.environ.get("ESIOS_TOKEN")
    if t:
        return t.strip()
    ruta = os.path.join(DESDE, ".env")
    for linea in open(ruta, encoding="utf-8"):
        linea = linea.strip()
        if linea.startswith("ESIOS_TOKEN="):
            return linea.split("=", 1)[1].strip()
    raise SystemExit("falta ESIOS_TOKEN en .env")


def pedir(ind, ini, fin):
    url = "https://api.esios.ree.es/indicators/%d?start_date=%sT00:00&end_date=%sT23:59" % (ind, ini, fin)
    req = urllib.request.Request(url, headers={**UA, "x-api-key": token()})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode("utf-8"))
    vals = d.get("indicator", {}).get("values", [])
    # ESIOS repite valores con distinto geo_id: se deduplica por fecha+hora
    vistos, serie = set(), []
    for v in vals:
        k = v.get("datetime")
        if not k or k in vistos:
            continue
        vistos.add(k)
        serie.append({"t": k, "v": v.get("value")})
    return d.get("indicator", {}).get("name"), serie


def main():
    ayer = (date.today() - timedelta(days=1)).isoformat()
    manana = (date.today() + timedelta(days=1)).isoformat()
    salida = {"generado": date.today().isoformat(), "fuente": "ESIOS (REE)", "series": {}}

    for ind, clave in ((460, "prevision_demanda"), (541, "prevision_eolica")):
        try:
            nombre, serie = pedir(ind, ayer, manana)
        except Exception as e:
            print("  %-18s ERROR %s" % (clave, type(e).__name__))
            continue
        salida["series"][clave] = {"indicador": ind, "nombre": nombre, "valores": serie}
        print("  %-18s %3d valores · %s" % (clave, len(serie), nombre))

    json.dump(salida, open(DEST + "/esios_prevision.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n  -> datos/esios_prevision.json")


if __name__ == "__main__":
    main()
