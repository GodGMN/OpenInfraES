#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base local de codigos postales: CP -> municipio (por CODIGO) + poblacion.

No existe una API abierta del CP completo (probado: API del INE, datos.gob.es y el
geocodificador de CartoCiudad). Lo que si hay son capas oficiales que traen el CP junto
al municipio ya cruzado por codigo; este script las recorre TODAS, construye la tabla y
declara la cobertura. Cuando aparezca una fuente completa (callejero del Catastro o del
CNIG), se anade aqui y la tabla se regenera sin tocar el visor.

    python scripts/cp.py            # escribe datos/cp_municipios.json + recibo
    python scripts/cp.py --listar   # solo informa de la cobertura

El fichero ocupa poco (~100 KB) y va al repo: es dato de base, no un cache.
"""
import argparse
import glob
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
SALIDA = os.path.join(DATOS, "cp_municipios.json")

CP = re.compile(r"^[0-5][0-9]{4}$")


def capas():
    for pat in ("*.geojson", "simplificado/*.geojson", "oficial/*.geojson", "hermes/*.geojson"):
        for ruta in glob.glob(os.path.join(DATOS, pat.replace("/", os.sep))):
            yield ruta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listar", action="store_true")
    a = ap.parse_args()

    tabla, fuentes, campos = {}, {}, {}
    for ruta in capas():
        try:
            d = json.load(open(ruta, encoding="utf-8"))
        except Exception:
            continue
        fs = d.get("features") or []
        if not fs:
            continue
        p0 = fs[0].get("properties") or {}
        campo_cp = next((k for k in p0 if k.lower() in ("codigo_postal", "cod_postal", "cp",
                                                        "c.p.", "postal_code", "codigopostal")), None)
        if not campo_cp or "cod_ine_municipio" not in p0:
            continue
        campos[os.path.basename(ruta)] = campo_cp
        n = 0
        for f in fs:
            pr = f.get("properties") or {}
            cp = str(pr.get(campo_cp) or "").strip().zfill(5)
            cod = pr.get("cod_ine_municipio")
            if not CP.match(cp) or not cod:
                continue
            fila = tabla.setdefault(cp, {"municipios": {}, "poblacion": 0})
            fila["municipios"][str(cod)] = {
                "nombre": pr.get("municipio_ine"),
                "provincia": pr.get("provincia_municipio"),
                "poblacion": pr.get("poblacion_municipio"),
                "anio": pr.get("anio_poblacion_municipio"),
            }
            fuentes.setdefault(cp, set()).add(os.path.basename(ruta))
            n += 1
        print("  %-34s %6d puntos con CP (%s)" % (os.path.basename(ruta), n, campo_cp))

    # CP que caen en más de un municipio: se declaran, no se elige uno al azar
    ambiguos = {cp: sorted(v["municipios"].items()) for cp, v in tabla.items() if len(v["municipios"]) > 1}
    # población del CP = suma de sus municipios (solo si el CP no cruza municipios)
    for cp, v in tabla.items():
        if len(v["municipios"]) == 1:
            m = next(iter(v["municipios"].values()))
            v["poblacion"] = m.get("poblacion") or 0
            v["anio"] = m.get("anio")
    salida = {
        "generado": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "nota": ("tabla CP -> municipio construida desde las capas oficiales que traen CP y municipio "
                 "cruzado por código. Cobertura parcial y declarada: no existe API abierta del CP completo."),
        "cobertura": {"cps": len(tabla), "estimado_espana": 11700,
                      "pct": round(100 * len(tabla) / 11700, 1)},
        "fuentes": {k: v for k, v in sorted(campos.items())},
        "cp_ambiguos": len(ambiguos),
        # compacto: [cod_ine, municipio, provincia, poblacion, año] por municipio del CP
        "cps": {cp: [[c, d.get("nombre"), d.get("provincia"), d.get("poblacion"), d.get("anio")]
                     for c, d in sorted(v["municipios"].items())]
                for cp, v in sorted(tabla.items())},
    }
    print("\n  CP distintos: %d (%.1f %% de ~11.700) · CP en más de un municipio: %d"
          % (len(tabla), salida["cobertura"]["pct"], len(ambiguos)))
    if a.listar:
        return 0
    json.dump(salida, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("  %s (%.0f KB)" % (SALIDA, os.path.getsize(SALIDA) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
