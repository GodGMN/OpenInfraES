# -*- coding: utf-8 -*-
"""REE en vivo — los indicadores de ESIOS que están ABIERTOS sin token.

Se probaron los 29 indicadores que usa el MCP ree-mcp: **19 responden 200 sin clave**
(demanda, generación por tecnología, emisiones, intercambios y bombeo). Los de precio,
PVPC y demanda peninsular de 5 min devuelven 403 y sí necesitan token.

Granularidad real: 5 minutos. Demanda nacional trae 224 valores al día.

    python scripts/ree_vivo.py                 # hoy
    python scripts/ree_vivo.py --fecha 2026-11-15

Salida: datos/ree_vivo.json (estado actual + series de 24 h) y datos/ree_vivo_recibo.json
"""
import argparse
import datetime
import json
import os
import time
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos")
BASE = "https://api.esios.ree.es/indicators"

# unidad real de cada magnitud (ESIOS no la declara en `unit`)
UNIDADES = {10355: "tCO₂/MW", 1294: "MW", 10004: "MW"}

# id -> (clave, etiqueta, grupo)
ABIERTOS = {
    2037: ("demanda", "Demanda real nacional", "demanda"),
    10004: ("demanda_gen", "Demanda real (suma de generación)", "demanda"),
    2041: ("ciclo", "Ciclo combinado", "generacion"),
    2042: ("hidro", "Hidráulica", "generacion"),
    2038: ("eolica", "Eólica", "generacion"),
    2044: ("solar_fv", "Solar fotovoltaica", "generacion"),
    2045: ("solar_ter", "Solar térmica", "generacion"),
    1294: ("solar_ter_pen", "Solar térmica (peninsular)", "generacion"),
    10355: ("co2", "CO₂ asociado a la generación", "emisiones"),
    2068: ("exp_andorra", "Exportación a Andorra", "intercambios"),
    2073: ("imp_andorra", "Importación de Andorra", "intercambios"),
    2069: ("exp_marruecos", "Exportación a Marruecos", "intercambios"),
    2074: ("imp_marruecos", "Importación de Marruecos", "intercambios"),
    2070: ("exp_portugal", "Exportación a Portugal", "intercambios"),
    2075: ("imp_portugal", "Importación de Portugal", "intercambios"),
    2071: ("exp_francia", "Exportación a Francia", "intercambios"),
    2076: ("imp_francia", "Importación de Francia", "intercambios"),
    2078: ("bombeo_cons", "Consumo de bombeo", "almacenamiento"),
    2079: ("bombeo_turb", "Turbinado de bombeo", "almacenamiento"),
}


def trae(ind):
    req = urllib.request.Request("%s/%s" % (BASE, ind),
                                 headers={"Accept": "application/json",
                                          "User-Agent": "OpenInfraES/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def limpia(v):
    """(hora, valor) con la hora local de Madrid y sin nulos."""
    salida = []
    for p in v:
        if p.get("value") is None:
            continue
        salida.append([p["datetime"][11:16], round(float(p["value"]), 2)])
    return salida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha")
    a = ap.parse_args()
    fecha = a.fecha or datetime.date.today().isoformat()

    series = {}
    estado = {}
    fallos = []
    for ind, (clave, etiqueta, grupo) in ABIERTOS.items():
        try:
            d = trae(ind)["indicator"]
            vals = limpia(d.get("values", []))
            if not vals:
                fallos.append({"id": ind, "clave": clave, "motivo": "sin valores"})
                continue
            series[clave] = {"etiqueta": etiqueta, "grupo": grupo, "id": ind,
                             "unidad": UNIDADES.get(ind, "MW"),
                             "hora": vals[-1][0], "valor": vals[-1][1],
                             "serie": vals[-72:]}   # últimas ~6 h a 5 min
            estado[clave] = vals[-1][1]
        except Exception as e:
            fallos.append({"id": ind, "clave": clave, "motivo": str(e)[:90]})
        time.sleep(0.35)

    salida = {
        "fecha": fecha,
        "actualizado": datetime.datetime.now().isoformat(timespec="seconds"),
        "fuente": "REE · ESIOS (indicadores abiertos, sin clave)",
        "resolucion": "5 minutos",
        "estado": estado,
        "series": series,
        "fallos": fallos,
    }
    ruta = os.path.join(DEST, "ree_vivo.json")
    json.dump(salida, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    recibo = {
        "fuente": "REE · ESIOS",
        "url": BASE,
        "fecha": fecha,
        "descargado": salida["actualizado"],
        "indicadores_ok": len(series),
        "indicadores_probados": len(ABIERTOS),
        "series": {k: {"id": v["id"], "puntos": len(v["serie"]),
                       "ultimo": v["valor"], "hora": v["hora"]} for k, v in series.items()},
        "fallos": fallos,
    }
    json.dump(recibo, open(os.path.join(DEST, "ree_vivo_recibo.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("  %d de %d indicadores · %s" % (len(series), len(ABIERTOS), fecha))
    for k in ("demanda", "eolica", "solar_fv", "hidro", "ciclo", "co2"):
        if k in series:
            v = series[k]
            print("   %-12s %10.1f %-6s  %s" % (v["etiqueta"][:12], v["valor"], v["unidad"], v["hora"]))
    if fallos:
        print("   fallos: %s" % ", ".join(f["clave"] for f in fallos))


if __name__ == "__main__":
    main()
