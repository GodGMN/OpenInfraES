# -*- coding: utf-8 -*-
"""OMIE · precio del mercado diario de electricidad (España y Portugal).

El operador del mercado (OMIE) publica el resultado de la subasta diaria como **CSV abierto**, sin
clave, una vez casada la subasta del día siguiente (≈13:00).

    https://www.omie.es/es/file-download?parents%5B0%5D=marginalpdbc&filename=marginalpdbc_YYYYMMDD.1

Formato (una fila por hora, 25 si hay cambio de hora):

    MARGINALPDBC;
    2026;11;18;1;12.17;12.17;
     año mes dia hora precio_ES precio_PT

    python scripts/omie.py                  # hoy
    python scripts/omie.py --fecha 2026-11-19    # el de mañana, en cuanto se case la subasta

El precio es **€/MWh** y el de Portugal es el mismo salvo en las horas en que el mercado se separa.
"""
import argparse
import datetime
import json
import os
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos")
# ojo: la URL lleva %5B (corchete codificado) y choca con el formateo %, asi que se concatena
BASE = ("https://www.omie.es/es/file-download?parents%5B0%5D=marginalpdbc"
        "&filename=marginalpdbc_")
UA = {"User-Agent": "Mozilla/5.0 (compatible; OpenInfraES/1.0)",
      "Accept": "text/csv,*/*"}


def baja(fecha):
    url = BASE + fecha.strftime("%Y%m%d") + ".1"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("latin-1", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", help="YYYY-MM-DD; por defecto hoy")
    a = ap.parse_args()
    fecha = datetime.date.fromisoformat(a.fecha) if a.fecha else datetime.date.today()

    txt = baja(fecha)
    horas = []
    filas_fichero = 0
    for linea in txt.splitlines():
        campos = [c.strip() for c in linea.split(";") if c.strip() != ""]
        if len(campos) < 5 or not campos[0].isdigit():
            continue
        filas_fichero += 1
        # El fichero trae 96 filas con el MISMO día, en cuatro bloques de 24 con precios
        # distintos. No está documentado qué son los bloques 2-4, así que se usan las 24
        # primeras horas (el mercado diario) y se declara en el recibo.
        try:
            if (int(campos[0]), int(campos[1]), int(campos[2])) != (fecha.year, fecha.month, fecha.day):
                continue
        except ValueError:
            continue
        try:
            hora = int(campos[3])
            if hora > 24:
                continue
            es = float(campos[4].replace(",", "."))
            pt = float(campos[5].replace(",", ".")) if len(campos) > 5 else es
        except (ValueError, IndexError):
            continue
        horas.append({"hora": hora, "es": round(es, 2), "pt": round(pt, 2)})

    if not horas:
        raise SystemExit("OMIE no devolvió filas para %s (¿subasta aún no casada?)" % fecha)

    precios = [h["es"] for h in horas]
    barata = min(horas, key=lambda h: h["es"])
    cara = max(horas, key=lambda h: h["es"])
    separadas = [h["hora"] for h in horas if abs(h["es"] - h["pt"]) > 0.01]

    salida = {
        "fuente": "OMIE", "mercado": "diario (MARGINALPDBC)",
        "url": BASE + fecha.strftime("%Y%m%d") + ".1",
        "fecha": fecha.isoformat(),
        "unidad": "€/MWh",
        "horas": horas,
        "min": barata["es"], "hora_min": barata["hora"],
        "max": cara["es"], "hora_max": cara["hora"],
        "media": round(sum(precios) / len(precios), 2),
        "horas_separadas_es_pt": separadas,
        "filas_en_fichero": filas_fichero,
        "nota_bloques": ("El fichero de OMIE trae 96 filas (4 bloques de 24) con la misma fecha "
                         "y precios distintos. Se publican las 24 primeras; los bloques 2-4 no "
                         "están identificados en la documentación de OMIE."),
        "descargado": datetime.datetime.now().isoformat(timespec="seconds"),
        "nota": ("Precio del mercado mayorista, no el precio final del consumidor: faltan peajes, "
                 "cargos e impuestos. Portugal comparte precio salvo en las horas de separación."),
    }
    json.dump(salida, open(os.path.join(DEST, "omie_precio.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("  %s · %d horas" % (fecha, len(horas)))
    print("   media %.2f · mín %.2f (h%d) · máx %.2f (h%d) €/MWh"
          % (salida["media"], salida["min"], barata["hora"], salida["max"], cara["hora"]))
    if separadas:
        print("   horas con precio distinto ES/PT: %s" % ", ".join(map(str, separadas)))
    for h in horas[:6]:
        print("   %02dh  %6.2f" % (h["hora"], h["es"]))


if __name__ == "__main__":
    main()