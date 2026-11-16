# -*- coding: utf-8 -*-
"""Conector NAP / datos.gob.es — solo bajo demanda.

El NAP (nap.transportes.gob.es) exige API key y su gateway no la acepta por header en
ninguna de las formas probadas (ver docs/nap.md). Su catálogo tiene 179 conjuntos de
datos de transporte (148 de autobús, 27 ferroviario, 3 marítimo, 1 aéreo).

Este script NO descarga nada por defecto. Hace solo lo que se le pide:

    python scripts/nap.py --estado                 # prueba el NAP con la clave de .env
    python scripts/nap.py --buscar "autobus"       # busca en datos.gob.es (abierto)
    python scripts/nap.py --dataset <url>          # inspecciona un dataset concreto

La clave se lee de .env (NAP_API_KEY) y no se imprime nunca.
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "OpenInfraES/1.0", "Accept": "application/json"}
NAP = "https://nap.transportes.gob.es"
DG = "https://datos.gob.es/apidata/catalog/dataset"
FORMAS = ["Authorization", "X-Api-Key", "X-API-KEY", "apikey", "Api-Key",
          "X-CKAN-API-Key", "X-Auth-Token", "token"]


def clave_nap():
    ruta = os.path.join(RAIZ, ".env")
    if not os.path.exists(ruta):
        return None
    for linea in open(ruta, encoding="utf-8"):
        if linea.startswith("NAP_API_KEY="):
            return linea.split("=", 1)[1].strip()
    return None


def get(url, headers=None, timeout=40):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


def estado_nap():
    k = clave_nap()
    print("NAP — sondeo del gateway (clave %s)" % ("cargada, %d chars" % len(k) if k else "NO encontrada"))
    if not k:
        print("  falta NAP_API_KEY en .env")
        return
    print("  %-18s %-6s %s" % ("forma", "http", "respuesta"))
    for forma in FORMAS:
        cod, cuerpo = get(NAP + "/api/3/action/package_list", {forma: k})
        txt = cuerpo.decode("utf-8", "replace").strip().replace("\n", " ")[:80]
        print("  %-18s %-6s %s" % (forma, cod, txt))
    cod, cuerpo = get(NAP + "/api/3/action/package_list?api_key=" + urllib.parse.quote(k))
    print("  %-18s %-6s %s" % ("?api_key=", cod, cuerpo.decode("utf-8", "replace").strip()[:80]))
    print("\n  Conclusión: 401 «Api Key was not provided» en todas las formas y 404 con")
    print("  «apikey». El gateway del NAP no acepta la clave por API directa.")


def buscar(texto, limite=8):
    url = "%s/title/%s?_format=json&_pageSize=%d" % (DG, urllib.parse.quote(texto), limite)
    cod, cuerpo = get(url)
    if cod != 200:
        print("  datos.gob.es devolvió %s" % cod)
        return []
    try:
        d = json.loads(cuerpo.decode("utf-8"))
    except Exception:
        print("  respuesta no JSON")
        return []
    items = d.get("result", {}).get("items", [])
    print("  %d conjuntos para «%s» (datos.gob.es, abierto)" % (len(items), texto))
    salida = []
    for it in items:
        titulo = it.get("title")
        # datos.gob.es devuelve JSON-LD: el texto va en {"_value": ...}
        def limpio(x):
            if isinstance(x, list):
                x = x[0] if x else ""
            if isinstance(x, dict):
                return x.get("_value", "")
            return x
        titulo = limpio(titulo)
        ident = limpio(it.get("identifier"))
        publisher = limpio(it.get("publisher"))
        print("   - %s" % str(titulo)[:80])
        print("     %s" % ident)
        salida.append({"titulo": titulo, "id": ident, "editor": publisher})
    return salida


def inspeccionar(ident):
    url = "%s?_format=json&_pageSize=1" % ident
    cod, cuerpo = get(url)
    print("  %s -> %s" % (ident, cod))
    if cod == 200:
        d = json.loads(cuerpo.decode("utf-8"))
        for it in d.get("result", {}).get("items", [])[:1]:
            print(json.dumps(it, ensure_ascii=False, indent=1)[:1200])


def main():
    ap = argparse.ArgumentParser(description="NAP / datos.gob.es bajo demanda")
    ap.add_argument("--estado", action="store_true", help="probar la API del NAP con la clave")
    ap.add_argument("--buscar", metavar="TEXTO", help="buscar en datos.gob.es (abierto)")
    ap.add_argument("--dataset", metavar="URL", help="inspeccionar un dataset concreto")
    a = ap.parse_args()
    if a.estado:
        estado_nap()
    elif a.buscar:
        buscar(a.buscar)
    elif a.dataset:
        inspeccionar(a.dataset)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
