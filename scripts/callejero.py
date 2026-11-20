#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base de códigos postales: CP -> municipio(s) con código INE, población y peso.

UN CP NO ES UN MUNICIPIO
------------------------
Un CP puede bañar varios términos (28914 Getafe / Leganés) y un municipio grande tiene
decenas de CP. Guardar «el municipio del CP» pierde información; guardar «el primero
que devuelva la API» la inventa (el 28760 Tres Cantos salía como Madrid).

El modelo guarda TODOS los municipios de cada CP con su número de direcciones:
`[cod_ine, municipio, provincia, población, año_padrón, n_direcciones]`, ordenados de
más a menos. El primero es el **principal**.

FUENTES (probadas una a una)
----------------------------
* IGN · IDEE — API de Direcciones de CartoCiudad (OGC API Features): **en uso**.
  Responde sin clave y trae CP + municipio + provincia por dirección.
* CNIG · Centro de Descargas (geopackage por provincia): **bloqueada**. Por HTTPS da
  000 (sin conexión); por HTTP solo hace 302 a HTTPS. BigIP delante.
* Catastro (descargadatos / OVC callejero): **404 en todas las rutas probadas**; el
  host responde, el servicio de callejero ya no está donde estaba.
* INE Tempus3: **no existe** el CP (166 operaciones, ninguna; tabla 33583 -> 204 vacío).
* datos.gob.es: **sin resultados** para «códigos postales».

La API es lenta (2-12 s por petición), así que el barrido es **educado y reanudable**:
lotes de CP, pocos hilos, y caché en disco cada oleada. Se puede cortar cuando quieras
y volver a lanzarlo: continúa donde estaba.

    python scripts/callejero.py                    # barrido completo, por provincias
    python scripts/callejero.py --desde 28 --hasta 28
    python scripts/callejero.py --unir             # junta las cachés y escribe la tabla
    python scripts/callejero.py --control          # contrasta con el testigo DGT
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
API = "https://api-features.idee.es/collections/address/items"
SALIDA = os.path.join(DATOS, "cp_municipios.json")
TESTIGO = os.path.join(DATOS, "cp_testigo_dgt.json")
CAMPOS = "component_PostalDescriptor,component_AdminUnitName_4,component_AdminUnitName_3"
RUIDO = {"de", "del", "la", "el", "los", "las", "y", "e", "en", "a", "o", "as", "os", "d", "l"}
LIMITE = [5000]


def norm(t):
    t = unicodedata.normalize("NFD", t or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return " ".join(p for p in t.split() if p and p not in RUIDO)


def consulta(cps, intentos=4):
    lista = ",".join("'%s'" % c for c in cps)
    url = ("%s?f=json&limit=%d&properties=%s&filter=%s"
           % (API, LIMITE[0], urllib.parse.quote(CAMPOS),
              urllib.parse.quote("component_PostalDescriptor IN (%s)" % lista)))
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OpenInfraES/1.0 (datos abiertos)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode("utf-8"))
            out = {}
            for f in d.get("features", []):
                p = f.get("properties") or {}
                cp = str(p.get("component_PostalDescriptor") or "").strip()
                mun = (p.get("component_AdminUnitName_4") or "").strip()
                prov = (p.get("component_AdminUnitName_3") or "").strip()
                if re.match(r"^[0-5][0-9]{4}$", cp) and mun:
                    k = (cp, mun, prov)
                    out[k] = out.get(k, 0) + 1
            return out
        except Exception:
            time.sleep(3 * (i + 1))
    return {}


def cache_de(desde, hasta):
    return os.path.join(DATOS, ".cp_api_cache_%02d_%02d.json" % (desde, hasta))


def guardar(cuenta, desde, hasta):
    json.dump({"%s|%s|%s" % k: v for k, v in cuenta.items()},
              open(cache_de(desde, hasta), "w", encoding="utf-8"), ensure_ascii=False)


def barrido(cps, cuenta, por_lote, hilos, etiqueta, desde, hasta, prof=0, max_prof=5):
    vistos = {k[0] for k in cuenta}
    pendientes = [c for c in cps if c not in vistos]
    if not pendientes:
        return
    grupos = [pendientes[i:i + por_lote] for i in range(0, len(pendientes), por_lote)]
    with ThreadPoolExecutor(max_workers=hilos) as ex:
        for res in ex.map(consulta, grupos):
            for k, n in res.items():
                cuenta[k] = cuenta.get(k, 0) + n
    guardar(cuenta, desde, hasta)          # caché incremental: se puede cortar aquí
    vistos = {k[0] for k in cuenta}
    quedan = [c for c in pendientes if c not in vistos]
    print("    %s lote %d: %d/%d nuevos (faltan %d) · %d CP en caché"
          % (etiqueta, por_lote, len(pendientes) - len(quedan), len(pendientes),
             len(quedan), len(vistos)), flush=True)
    if quedan and prof < max_prof and len(quedan) < len(pendientes):
        barrido(quedan, cuenta, max(2, por_lote // 3), hilos, etiqueta, desde, hasta,
                prof + 1, max_prof)


def municipios():
    d = json.load(open(os.path.join(DATOS, "municipios.geojson"), encoding="utf-8"))
    idx = {}
    for f in d["features"]:
        p = f["properties"]
        cod = str(p.get("cod_ine"))
        idx.setdefault(norm(p.get("nombre")), []).append(
            (cod, p.get("nombre"), cod[:2], p.get("provincia_nombre"),
             p.get("poblacion"), p.get("anio_poblacion")))
    return idx


def cargar_cuenta():
    cuenta = {}
    for f in glob.glob(os.path.join(DATOS, ".cp_api_cache_*.json")):
        for k, n in json.load(open(f, encoding="utf-8")).items():
            cp, mun, prov = k.split("|")
            clave = (cp, mun, prov)
            cuenta[clave] = cuenta.get(clave, 0) + n
    return cuenta


def construir(cuenta):
    por_cp = {}
    for (cp, mun, prov), n in cuenta.items():
        por_cp.setdefault(cp, []).append([mun, prov, n])
    mun_idx = municipios()
    tabla, homonimos, sin_codigo = {}, {}, {}
    for cp, lista in sorted(por_cp.items()):
        lista.sort(key=lambda x: -x[2])
        filas, sin = [], []
        for mun, prov, n in lista:
            cands = [c for c in mun_idx.get(norm(mun), []) if c[2] == cp[:2]]
            if len(cands) == 1:
                c = cands[0]
                filas.append([c[0], c[1], c[3], c[4], c[5], n])
            elif len(cands) > 1:
                homonimos.setdefault(cp, []).append({
                    "municipio": mun,
                    "candidatos": [{"cod_ine": c[0], "nombre": c[1]} for c in cands]})
                for c in cands:
                    filas.append([c[0], c[1], c[3], c[4], c[5], n])
            else:
                sin.append(mun)
        if filas:
            filas.sort(key=lambda x: -x[5])
            tabla[cp] = filas
        if sin:
            sin_codigo[cp] = sin
    return tabla, homonimos, sin_codigo


def escribir(tabla, homonimos, sin_codigo):
    testigo = {}
    if os.path.exists(TESTIGO):
        testigo = json.load(open(TESTIGO, encoding="utf-8")).get("cps", {})
    coinciden = discrepan = fuera = 0
    for cp, filas in testigo.items():
        if cp not in tabla:
            fuera += 1
        elif any(f[0] == filas[0][0] for f in tabla[cp]):
            coinciden += 1
        else:
            discrepan += 1
    multi = sum(1 for f in tabla.values() if len(f) > 1)
    salida = {
        "generado": datetime.datetime.now().isoformat(timespec="seconds"),
        "fuente": "IGN · IDEE — API de Direcciones de CartoCiudad (OGC API Features)",
        "fuente_url": API,
        "modelo": ("[cod_ine, municipio, provincia, población, año_padrón, n_direcciones] por cada "
                   "municipio que toca el CP, de más a menos direcciones; el primero es el principal"),
        "bloqueo_documentado": {
            "CNIG centro de descargas (geopackage por provincia)": "HTTPS -> 000 sin conexión; HTTP -> 302 a HTTPS (BigIP)",
            "Catastro descargadatos / OVC callejero": "404 en todas las rutas probadas",
            "INE Tempus3": "sin operación ni tabla de CP (33583 -> 204 vacío)",
            "datos.gob.es": "0 resultados para 'códigos postales'"},
        "cobertura": {"cps": len(tabla), "estimado_espana": 11700,
                      "pct": round(100 * len(tabla) / 11700, 1),
                      "cps_multimunicipio": multi},
        "control": {"testigo": len(testigo), "coinciden": coinciden,
                    "discrepan": discrepan, "no_aparecen": fuera},
        "cp_sin_codigo": dict(list(sin_codigo.items())[:200]),
        "cps": tabla,
    }
    if homonimos:
        salida["homonimos"] = dict(list(homonimos.items())[:200])
    json.dump(salida, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("  %d CP (%.1f %%) · multimunicipio %d · homónimos %d · sin código %d"
          % (len(tabla), salida["cobertura"]["pct"], multi, len(homonimos), len(sin_codigo)))
    print("  control testigo: %d coinciden · %d discrepan · %d no aparecen (de %d)"
          % (coinciden, discrepan, fuera, len(testigo)))
    print("  %s (%.0f KB)" % (SALIDA, os.path.getsize(SALIDA) / 1024))
    return discrepan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--por-lote", type=int, default=25)
    ap.add_argument("--hilos", type=int, default=4)
    ap.add_argument("--limite", type=int, default=5000)
    ap.add_argument("--desde", type=int, default=1)
    ap.add_argument("--hasta", type=int, default=52)
    ap.add_argument("--unir", action="store_true", help="junta las cachés y escribe la tabla")
    ap.add_argument("--control", action="store_true", help="solo informa del testigo")
    a = ap.parse_args()
    LIMITE[0] = a.limite

    if a.control:
        testigo = json.load(open(TESTIGO, encoding="utf-8")) if os.path.exists(TESTIGO) else {"cps": {}}
        print("  testigo: %d CP" % len(testigo.get("cps", {})))
        return 0

    if a.unir:
        cuenta = cargar_cuenta()
        print("  cachés juntadas: %d parejas CP–municipio" % len(cuenta))
        return 1 if escribir(*construir(cuenta)) else 0

    cuenta = {}
    f = cache_de(a.desde, a.hasta)
    if os.path.exists(f):
        for k, n in json.load(open(f, encoding="utf-8")).items():
            cp, mun, prov = k.split("|")
            cuenta[(cp, mun, prov)] = n
        print("  caché %02d-%02d: %d parejas ya contadas" % (a.desde, a.hasta, len(cuenta)))

    candidatos = ["%02d%03d" % (prov, n) for prov in range(a.desde, a.hasta + 1) for n in range(1000)]
    print("  candidatos: %d · lotes de %d · %d hilos" % (len(candidatos), a.por_lote, a.hilos))
    t0 = time.time()
    etiqueta = "%02d-%02d" % (a.desde, a.hasta)
    barrido(candidatos, cuenta, a.por_lote, a.hilos, etiqueta, a.desde, a.hasta)
    print("  barrido %s: %.0f s · %d CP" % (etiqueta, time.time() - t0, len({k[0] for k in cuenta})))
    return 0


if __name__ == "__main__":
    sys.exit(main())
