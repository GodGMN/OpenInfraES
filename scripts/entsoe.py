# -*- coding: utf-8 -*-
"""ENTSO-E Transparency — el único que da generación y previsión POR UNIDAD.

La cuenta de la web NO es la clave de la API. Se pide un token «Restful API» a
transparency@entsoe.eu (asunto: "Restful API access"), indicando el email de la cuenta.
Con él, la API responde XML; aquí se convierte a estructuras simples.

    python scripts/entsoe.py --probar
    python scripts/entsoe.py --dia 2026-11-16
    python scripts/entsoe.py --unidades 2026-11-16

Endpoints usados (dominio España = 10YES-REE------0):
    A75  generación real agregada por tipo
    A73  generación real por unidad (registeredResource)
    A65  demanda total del sistema
    A44  precio del mercado diario
    A71  previsión de generación
    A69  previsión de demanda
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://web-api.tp.entsoe.eu/api"
ES = "10YES-REE------0"
DEST = os.path.join(RAIZ, "datos")


def token():
    t = os.environ.get("ENTSOE_TOKEN")
    if t:
        return t.strip()
    ruta = os.path.join(RAIZ, ".env")
    for linea in open(ruta, encoding="utf-8"):
        if linea.startswith("ENTSOE_TOKEN="):
            return linea.split("=", 1)[1].strip()
    return None


def pedir(params):
    tk = token()
    if not tk:
        raise SystemExit("falta ENTSOE_TOKEN en .env (ver cabecera del script)")
    q = urllib.parse.urlencode({**params, "securityToken": tk})
    req = urllib.request.Request(API + "?" + q, headers={"User-Agent": "OpenInfraES/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode("utf-8", "replace")[:200]
        raise SystemExit("ENTSO-E %s: %s" % (e.code, cuerpo))


NS = {"g": "urn:iec62325.351:tc57wg16:451-6:generationdocument:7:0",
      "g2": "urn:iec62325.351:tc57wg16:451-3:generationdocument:7:0",
      "g3": "urn:iec62325.351:tc57wg16:451-6:publicationdocument:7:3"}


def puntos(root):
    """Extrae (tipo, cantidad, inicio, resolucion) de cualquier documento de publicación."""
    salida = []
    for serie in root.iter():
        if not serie.tag.endswith("TimeSeries"):
            continue
        tipo = None
        for hijo in serie:
            if hijo.tag.endswith("MktPSRType"):
                for h2 in hijo:
                    if h2.tag.endswith("psrType"):
                        tipo = h2.text
        for periodo in serie:
            if not periodo.tag.endswith("Period"):
                continue
            ini = None
            res = None
            for h in periodo:
                if h.tag.endswith("timeInterval"):
                    for h2 in h:
                        if h2.tag.endswith("start"):
                            ini = h2.text
                if h.tag.endswith("resolution"):
                    res = h.text
            for p in periodo:
                if not p.tag.endswith("Point"):
                    continue
                pos = cant = None
                for h in p:
                    if h.tag.endswith("position"):
                        pos = int(h.text)
                    if h.tag.endswith("quantity"):
                        cant = float(h.text)
                salida.append({"tipo": tipo, "posicion": pos, "valor": cant,
                               "inicio": ini, "resolucion": res})
    return salida


def probar():
    root = ET.fromstring(pedir({"documentType": "A75", "processType": "A16",
                                "in_Domain": ES, "out_Domain": ES,
                                "periodStart": "202611160000", "periodEnd": "202611162300"}))
    filas = puntos(root)
    print("  TOKEN OK · %d puntos de generación" % len(filas))
    tipos = {}
    for f in filas:
        if f["valor"]:
            tipos[f["tipo"]] = tipos.get(f["tipo"], 0) + f["valor"]
    for t, v in sorted(tipos.items(), key=lambda kv: -kv[1])[:8]:
        print("   psrType %-6s %10.1f MWh" % (t, v))


def dia(fecha):
    ini = fecha.replace("-", "") + "0000"
    fin = fecha.replace("-", "") + "2300"
    root = ET.fromstring(pedir({"documentType": "A75", "processType": "A16",
                                "in_Domain": ES, "out_Domain": ES,
                                "periodStart": ini, "periodEnd": fin}))
    filas = puntos(root)
    json.dump({"fecha": fecha, "puntos": filas, "fuente": "ENTSO-E Transparency (A75)"},
              open(os.path.join(DEST, "entsoe_generacion.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("  %d puntos -> datos/entsoe_generacion.json" % len(filas))


def unidades(fecha):
    """Generación por unidad: A73 con todos los recursos registrados."""
    ini = fecha.replace("-", "") + "0000"
    fin = fecha.replace("-", "") + "2300"
    root = ET.fromstring(pedir({"documentType": "A73", "processType": "A16",
                                "in_Domain": ES, "out_Domain": ES,
                                "periodStart": ini, "periodEnd": fin}))
    recursos = []
    for serie in root.iter():
        if not serie.tag.endswith("TimeSeries"):
            continue
        nombre = None
        for h in serie:
            if h.tag.endswith("registeredResource"):
                for h2 in h:
                    if h2.tag.endswith("name"):
                        nombre = h2.text
        if nombre:
            recursos.append(nombre)
    print("  unidades con producción: %d" % len(set(recursos)))
    for r in sorted(set(recursos))[:15]:
        print("   ", r)


def main():
    ap = argparse.ArgumentParser(description="ENTSO-E Transparency")
    ap.add_argument("--probar", action="store_true")
    ap.add_argument("--dia", metavar="YYYY-MM-DD")
    ap.add_argument("--unidades", metavar="YYYY-MM-DD")
    a = ap.parse_args()
    if a.probar:
        probar()
    elif a.dia:
        dia(a.dia)
    elif a.unidades:
        unidades(a.unidades)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
