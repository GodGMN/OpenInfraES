#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Barrido: donde se cruza por TEXTO y donde ya se cruza por CÓDIGO.

Regla del proyecto: un dato se cruza por su código oficial; el nombre se normaliza solo
para buscar y mostrar. Este script lo comprueba en el código y en los datos.

    python scripts/auditar_cruces.py
"""
import glob
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")

SOSPECHOSO = [
    (r"normaliza\(|norm_nombre\(|match\(r?[\"']\.\*\$(?!.*cod)", "cruza por texto normalizado"),
    (r"\.lower\(\)\s*==|\.strip\(\)\s*==", "compara cadenas"),
    (r"for .* in .*features.*if .*nombre", "filtra features por nombre"),
]


def main():
    print("== scripts que cruzan por texto ==")
    hallados = 0
    for f in sorted(glob.glob(os.path.join(RAIZ, "scripts", "*.py"))):
        txt = open(f, encoding="utf-8").read()
        for pat, por in SOSPECHOSO:
            for m in re.finditer(pat, txt):
                linea = txt[:m.start()].count("\n") + 1
                print("  %-26s L%-4d %s" % (os.path.basename(f), linea, por))
                hallados += 1
                break
    print("  total: %d" % hallados)

    print("\n== capas del visor: ¿tienen código? ==")
    html = open(os.path.join(RAIZ, "index.html"), encoding="utf-8").read()
    import sys as _s
    _s.path.insert(0, os.path.join(RAIZ, "scripts"))
    from cifras import leer_array_capas
    for c in leer_array_capas(html):
        f = c.get("fichero")
        if not f:
            continue
        ruta = os.path.join(RAIZ, f.replace("/", os.sep))
        if not os.path.exists(ruta):
            continue
        try:
            d = json.load(open(ruta, encoding="utf-8"))
        except Exception:
            continue
        fs = d.get("features") or []
        if not fs:
            continue
        props = fs[0].get("properties") or {}
        codigos = [k for k in props if k in ("cod_ine", "cod_ine_municipio", "cod_demar",
                                             "codigo", "id", "LAU_ID", "osm_id", "objectid", "OBJECTID")]
        estado = "código: " + ", ".join(codigos[:3]) if codigos else "SIN CÓDIGO"
        print("  %-22s %-46s %s" % (c["id"], estado, "con municipio" if "cod_ine_municipio" in props else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
