# -*- coding: utf-8 -*-
"""Regenera las cifras de la prosa de los documentos desde el estado real del proyecto.

Problema P1 de la auditoría: el README decía 29 capas, su propia tabla 48 y la biblioteca 28,
mientras el visor tenía 52 y el catálogo 68. Tres universos distintos y ninguna cifra escrita a
mano coincidía con lo medido.

Aquí no hay una cuarta cifra: se cuentan las cosas donde están y se reescriben los documentos.

    python scripts/cifras.py          # reescribe y muestra qué cambió
    python scripts/cifras.py --check  # solo comprueba; rc=1 si algo está desfasado (para el CI)

Universos que se miden, y no se mezclan (la auditoría los separa a propósito):

  capas del visor    ids del array CAPAS de index.html
  grupos             valores distintos de `grupo` en ese array
  entradas catálogo  claves de datos/fuentes.json
  organismos         organismos canónicos de datos/catalogo.json
"""
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")


def medidas():
    html = open(os.path.join(RAIZ, "index.html"), encoding="utf-8").read()
    ini = html.index("const CAPAS = [")
    fin = html.index("];", ini)
    bloque = html[ini:fin]
    ids = re.findall(r'id:"([a-z0-9\-_]+)"', bloque)
    grupos = set(re.findall(r'grupo:"([^"]+)"', bloque))

    fuentes = json.load(open(os.path.join(DATOS, "fuentes.json"), encoding="utf-8"))
    entradas = len(fuentes.get("capas", {}))

    organismos = 0
    cat = os.path.join(DATOS, "catalogo.json")
    if os.path.exists(cat):
        c = json.load(open(cat, encoding="utf-8"))
        organismos = len({v["organismo"] for v in c.get("capas", {}).values()})

    return {
        "capas": len(ids),
        "grupos": len(grupos),
        "entradas": entradas,
        "organismos": organismos,
    }


# cada patrón tiene que casar con lo que hay escrito; el grupo 2 es la cifra vieja y el 3 es lo
# que viene detras (para no comerse la frase)
PATRONES = [
    # README, cabecera de capas
    (r"(\*\*)(\d+)( capas en \d+ grupos temáticos\*\*)",
     lambda m, v: f"{m.group(1)}{v['capas']} capas en {v['grupos']} grupos temáticos**"),
    (r"(Con )(\d+)( capas en \d+\n)", lambda m, v: f"{m.group(1)}{v['capas']} capas en {v['grupos']}\n"),
    # tablas de estado
    (r"(\| Capas en el visor \| \*\*)(\d+)(\*\* \|)",
     lambda m, v: f"{m.group(1)}{v['capas']}{m.group(3)}"),
    (r"(\| Capas documentadas en `fuentes.json` \| \*\*)(\d+)(\*\* \|)",
     lambda m, v: f"{m.group(1)}{v['entradas']}{m.group(3)}"),
    (r"(\| Organismos citados \| \*\*)(\d+)(\*\*)",
     lambda m, v: f"{m.group(1)}{v['organismos']}{m.group(3)}"),
    # biblioteca
    (r"(\*\*)(\d+)( capas en el visor\*\* y \*\*)(\d+)( entradas documentadas\*\*)",
     lambda m, v: f"{m.group(1)}{v['capas']} capas en el visor** y **{v['entradas']} entradas documentadas**"),
    # prosa suelta del README con el total de objetos
    (r"(\| \*\*Total\*\* \| \*\*)(\d+)(\*\* \| \*\*)([\d.]+)(\*\* \|)",
     lambda m, v: f"{m.group(1)}{v['capas']}{m.group(3)}{m.group(4)}{m.group(5)}"),
]

DOCS = ["README.md", os.path.join("docs", "BIBLIOTECA.md"), "PROYECTO.md"]


def main():
    solo_check = "--check" in sys.argv
    v = medidas()
    print("  medido: %d capas · %d grupos · %d entradas de catálogo · %d organismos" % (
        v["capas"], v["grupos"], v["entradas"], v["organismos"]))

    cambios = 0
    desfases = []
    for doc in DOCS:
        ruta = os.path.join(RAIZ, doc)
        if not os.path.exists(ruta):
            continue
        texto = open(ruta, encoding="utf-8").read()
        nuevo = texto
        for patron, construir in PATRONES:
            for m in list(re.finditer(patron, nuevo)):
                reemplazo = construir(m, v)
                if reemplazo != m.group(0):
                    if solo_check:
                        desfases.append("%s: %r -> %r" % (doc, m.group(0)[:60], reemplazo[:60]))
                    nuevo = nuevo.replace(m.group(0), reemplazo, 1)
                    cambios += 1
        if not solo_check and nuevo != texto:
            open(ruta, "w", encoding="utf-8").write(nuevo)
            print("  %-26s actualizado" % doc)

    if solo_check:
        if desfases:
            print("  DESFASADO (%d):" % len(desfases))
            for d in desfases[:10]:
                print("   ", d)
            return 1
        print("  cifras coherentes")
        return 0

    print("  %d cifras reescritas" % cambios)
    return 0


if __name__ == "__main__":
    sys.exit(main())