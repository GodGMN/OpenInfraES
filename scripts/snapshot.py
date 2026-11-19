# -*- coding: utf-8 -*-
"""Archiva una foto de los datos vivos al día, para poder responder «¿cómo ha evolucionado esto?».

Problema P6 de la auditoría: cada capa es una foto y, cuando se regenera, la anterior se pierde.
Sin serie no hay evolución, y la primera pregunta que hace una IA (y una persona) es justo esa.

    python scripts/snapshot.py                 # archiva lo de hoy
    python scripts/snapshot.py --lista         # qué series hay y de cuántos días

Formato: `datos/series/<capa>.json` = { "capa": ..., "dias": [ {fecha, ...valores} ] }

Se guarda **una entrada por día**: si el cron corre cada 30 minutos, el día se actualiza, no se
duplica. El día en curso se sobrescribe hasta que cambia; los anteriores quedan fijos.
"""
import datetime
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
SERIES = os.path.join(DATOS, "series")

# capa -> función que extrae los valores que merece la pena seguir
def _mix(d):
    techs = d.get("tecnologias") or []
    return {"total_mwh": d.get("total_mwh"),
            "tecnologias": {t["nombre"]: t["mwh"] for t in techs}}


def _omie(d):
    return {"media": d.get("media"), "min": d.get("min"), "max": d.get("max"),
            "hora_min": d.get("hora_min"), "hora_max": d.get("hora_max")}


def _vivo(d):
    s = d.get("series") or {}
    salida = {}
    for k, v in s.items():
        if isinstance(v, dict) and v.get("valor") is not None:
            try:
                salida[k] = float(v["valor"])
            except (TypeError, ValueError):
                pass
    return salida


def _geojson_conteo(d):
    return {"objetos": len(d.get("features") or [])}


FUENTES = {
    "entsoe_mix": ("entsoe_mix.json", _mix),
    "omie_precio": ("omie_precio.json", _omie),
    "ree_vivo": ("ree_vivo.json", _vivo),
    "sismos": ("sismos.geojson", _geojson_conteo),
    "aemet_zonas": ("aemet_zonas.geojson", _geojson_conteo),
    "dgt_incidencias": ("dgt_incidencias.geojson", _geojson_conteo),
}


def main():
    hoy = datetime.date.today().isoformat()
    if "--lista" in sys.argv:
        if not os.path.isdir(SERIES):
            print("  no hay series todavía")
            return 0
        for f in sorted(os.listdir(SERIES)):
            if not f.endswith(".json"):
                continue
            d = json.load(open(os.path.join(SERIES, f), encoding="utf-8"))
            dias = d.get("dias", [])
            print("  %-22s %3d días · de %s a %s" % (
                f[:-5], len(dias), dias[0]["fecha"] if dias else "-",
                dias[-1]["fecha"] if dias else "-"))
        return 0

    os.makedirs(SERIES, exist_ok=True)
    archivadas = 0
    for capa, (fichero, extrae) in FUENTES.items():
        ruta = os.path.join(DATOS, fichero)
        if not os.path.exists(ruta):
            continue
        try:
            crudo = json.load(open(ruta, encoding="utf-8"))
            valores = extrae(crudo)
        except Exception as e:
            print("  %-18s no se pudo leer: %s" % (capa, str(e)[:40]))
            continue

        destino = os.path.join(SERIES, capa + ".json")
        serie = {"capa": capa, "dias": []}
        if os.path.exists(destino):
            serie = json.load(open(destino, encoding="utf-8"))

        entrada = {"fecha": hoy, **valores}
        # un registro por día: si ya existe el de hoy, se sustituye
        serie["dias"] = [x for x in serie["dias"] if x.get("fecha") != hoy] + [entrada]
        serie["dias"].sort(key=lambda x: x.get("fecha", ""))

        json.dump(serie, open(destino, "w", encoding="utf-8"), ensure_ascii=False)
        archivadas += 1
        print("  %-18s %d días" % (capa, len(serie["dias"])))

    print("  %d series archivadas en datos/series/" % archivadas)
    return 0


if __name__ == "__main__":
    sys.exit(main())