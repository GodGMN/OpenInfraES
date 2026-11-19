# -*- coding: utf-8 -*-
"""INE · población oficial por provincia y comunidad, cruzada con las capas del visor.

Datos de la API Tempus3 del INE (`servicios.ine.es/wstempus/js/ES`), sin clave:

    2852  Población por provincias y sexo      (Cifras oficiales del padrón)
    2853  Población por comunidades y ciudades autónomas y sexo

Se cruzan por nombre con los polígonos NUTS3/NUTS2 que ya tiene el visor y se les añade
`poblacion` y una coropleta por habitantes.

    python scripts/ine.py

El cruce es por nombre normalizado: el INE y la capa no siempre coinciden (`A Coruña` /
`Coruña`, `Araba/Álava`), así que el script declara cuántas provincias cruzan y cuáles no.
"""
import json
import os
import re
import unicodedata
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
API = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/%s?nult=1"
UA = {"User-Agent": "Mozilla/5.0 (compatible; OpenInfraES/1.0)", "Accept": "application/json"}


ART = {"a", "el", "la", "los", "las", "o", "os", "as", "illes", "islas"}
# Palabras que no distinguen: el INE escribe "Asturias, Principado de" y "Madrid, Comunidad de",
# la capa escribe "Principado de Asturias". Comparando solo las palabras significativas, ambas
# formas dan lo mismo.
RUIDO = ART | {"de", "del", "foral", "principado", "comunidad", "region", "ciudad",
               "autonoma", "autonomas", "uniprovincial"}


def normaliza(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace(",", " ")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    palabras = [p for p in s.split() if p and p not in RUIDO]
    return " ".join(sorted(palabras))


def candidatos(s):
    """Claves posibles: el nombre entero, cada mitad de un 'X/Y' y cada variante sin ruido."""
    salida = []
    for trozo in [str(s or "")] + re.split(r"/", str(s or "")):
        n = normaliza(trozo)
        if n and n not in salida:
            salida.append(n)
    return salida


def descarga(tabla):
    url = API % tabla
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
        return json.loads(r.read())


def poblacion(tabla):
    """Devuelve {nombre_normalizado: habitantes} usando la serie 'Total habitantes'."""
    salida = {}
    for reg in descarga(tabla):
        nom = reg.get("Nombre") or ""
        # 'Albacete. Total. Total habitantes. Personas.'
        if "Total habitantes" not in nom:
            continue
        partes = [p.strip() for p in nom.split(".")]
        if len(partes) < 2 or partes[1].lower() != "total":
            continue
        clave_nom = partes[0]
        valor = (reg.get("Data") or [{}])[0].get("Valor")
        if valor is None:
            continue
        if clave_nom.lower().startswith("total nacional"):
            salida["__total__"] = int(valor)
            continue
        for k in candidatos(clave_nom):
            salida[k] = int(valor)
    return salida


def aplica(fichero, pobl, etiqueta):
    ruta = os.path.join(DATOS, fichero)
    if not os.path.exists(ruta):
        print("  falta %s" % fichero)
        return None
    d = json.load(open(ruta, encoding="utf-8"))
    puestos = sin = 0
    faltan = []
    for f in d["features"]:
        p = f["properties"]
        hallado = None
        for clave in candidatos(p.get("nombre") or p.get("nom_demar")):
            if clave in pobl:
                hallado = pobl[clave]
                break
        if hallado is not None:
            p["poblacion"] = hallado
            puestos += 1
        else:
            sin += 1
            faltan.append(p.get("nombre"))
    if not puestos:
        print("  %s: ninguna coincidencia" % etiqueta)
        return None
    # coropleta por habitantes (cuartiles)
    vals = sorted(f["properties"]["poblacion"] for f in d["features"]
                  if f["properties"].get("poblacion"))
    cortes = [vals[int(len(vals) * q)] for q in (0.25, 0.5, 0.75)]
    tramos = ["#fef3c7", "#fbbf24", "#f59e0b", "#b45309"]
    nombres = ["baja", "media-baja", "media-alta", "alta"]
    for f in d["features"]:
        v = f["properties"].get("poblacion")
        if v is None:
            continue
        i = sum(1 for c in cortes if v >= c)
        f["properties"]["color"] = tramos[i]
        f["properties"]["tramo_poblacion"] = nombres[i]
    json.dump(d, open(ruta, "w", encoding="utf-8"), ensure_ascii=False)
    print("  %s: %d con población · %d sin cruzar · %d KB" % (
        etiqueta, puestos, sin, os.path.getsize(ruta) // 1024))
    if faltan:
        print("   sin cruzar: %s" % ", ".join(str(x) for x in faltan[:8]))
    return puestos


def main():
    print("  INE · Cifras oficiales del padrón")
    prov = poblacion(2852)
    com = poblacion(2853)
    print("  España: %s habitantes" % f"{prov.get('__total__', 0):,}".replace(",", "."))
    print("  provincias con dato: %d · comunidades: %d" % (
        len([k for k in prov if k != "__total__"]), len([k for k in com if k != "__total__"])))

    aplica("irewater_hib_nuts3.geojson", prov, "provincias (NUTS3)")
    aplica("irewater_hib_nuts2.geojson", com, "comunidades (NUTS2)")

    recibo = {
        "fuente": "INE · Cifras Oficiales de Población (padrón)",
        "url": "https://www.ine.es/jaxiT3/Tabla.htm?t=2852",
        "api": "servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2852",
        "tablas": {"provincias": 2852, "comunidades": 2853},
        "total_nacional": prov.get("__total__"),
        "provincias_con_dato": len([k for k in prov if k != "__total__"]),
        "nota": "Cruce por nombre normalizado; el INE no da código de municipio en esta tabla.",
    }
    json.dump(recibo, open(os.path.join(DATOS, "ine_recibo.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("  recibo -> datos/ine_recibo.json")


if __name__ == "__main__":
    main()