# -*- coding: utf-8 -*-
"""Normaliza provincias y comunidades con su CÓDIGO OFICIAL.

Regla del proyecto: **una provincia o una comunidad autónoma nunca se identifica por su nombre**,
siempre por código. El nombre cambia (`Coruña` / `A Coruña` / `La Coruña`, `Alacant` / `Alicante`,
`Illes Balears` / `Baleares`) y cualquier cruce por texto acaba en pérdidas silenciosas.

Se añaden tres campos a cada polígono:

| Campo | Qué es | Ejemplo (Salamanca) |
|---|---|---|
| `cod_ine` | Código INE de 2 dígitos | `37` |
| `nuts` | Código NUTS de Eurostat | `ES415` |
| `slug` | Identificador estable para URLs | `salamanca` |

    python scripts/normaliza.py

Las tablas son las oficiales del INE (provincias 01-52 y comunidades 01-19) y de Eurostat (NUTS
2021). Se cruzan por nombre normalizado solo UNA vez, aquí; a partir de este punto todo el visor
usa `cod_ine`.
"""
import json
import os
import re
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")

# Código INE de provincia -> (nombre oficial, código NUTS3)
PROVINCIAS = {
    "01": ("Álava", "ES211"), "02": ("Albacete", "ES421"), "03": ("Alicante", "ES521"),
    "04": ("Almería", "ES611"), "05": ("Ávila", "ES411"), "06": ("Badajoz", "ES431"),
    "07": ("Baleares", "ES532"), "08": ("Barcelona", "ES511"), "09": ("Burgos", "ES412"),
    "10": ("Cáceres", "ES432"), "11": ("Cádiz", "ES612"), "12": ("Castellón", "ES522"),
    "13": ("Ciudad Real", "ES422"), "14": ("Córdoba", "ES613"), "15": ("A Coruña", "ES111"),
    "16": ("Cuenca", "ES423"), "17": ("Girona", "ES512"), "18": ("Granada", "ES614"),
    "19": ("Guadalajara", "ES424"), "20": ("Gipuzkoa", "ES212"), "21": ("Huelva", "ES615"),
    "22": ("Huesca", "ES241"), "23": ("Jaén", "ES616"), "24": ("León", "ES413"),
    "25": ("Lleida", "ES513"), "26": ("La Rioja", "ES230"), "27": ("Lugo", "ES112"),
    "28": ("Madrid", "ES300"), "29": ("Málaga", "ES617"), "30": ("Murcia", "ES620"),
    "31": ("Navarra", "ES220"), "32": ("Ourense", "ES113"), "33": ("Asturias", "ES120"),
    "34": ("Palencia", "ES414"), "35": ("Las Palmas", "ES701"), "36": ("Pontevedra", "ES114"),
    "37": ("Salamanca", "ES415"), "38": ("Santa Cruz de Tenerife", "ES702"),
    "39": ("Cantabria", "ES130"), "40": ("Segovia", "ES416"), "41": ("Sevilla", "ES618"),
    "42": ("Soria", "ES417"), "43": ("Tarragona", "ES514"), "44": ("Teruel", "ES242"),
    "45": ("Toledo", "ES425"), "46": ("Valencia", "ES523"), "47": ("Valladolid", "ES418"),
    "48": ("Bizkaia", "ES213"), "49": ("Zamora", "ES419"), "50": ("Zaragoza", "ES243"),
    "51": ("Ceuta", "ES630"), "52": ("Melilla", "ES640"),
}

# Código INE de comunidad -> (nombre oficial, código NUTS2)
CCAA = {
    "01": ("Andalucía", "ES61"), "02": ("Aragón", "ES24"), "03": ("Asturias", "ES12"),
    "04": ("Baleares", "ES53"), "05": ("Canarias", "ES70"), "06": ("Cantabria", "ES13"),
    "07": ("Castilla y León", "ES41"), "08": ("Castilla-La Mancha", "ES42"),
    "09": ("Cataluña", "ES51"), "10": ("Extremadura", "ES43"), "11": ("Galicia", "ES11"),
    "12": ("Madrid", "ES30"), "13": ("Murcia", "ES62"), "14": ("Navarra", "ES22"),
    "15": ("País Vasco", "ES21"), "16": ("La Rioja", "ES23"), "17": ("Valencia", "ES52"),
    "18": ("Ceuta", "ES63"), "19": ("Melilla", "ES64"),
}

RUIDO = {"a", "el", "la", "los", "las", "o", "os", "as", "illes", "islas", "de", "del",
         "foral", "principado", "comunidad", "comunitat", "region", "ciudad", "autonoma",
         "autonomas"}

# Variantes que el normalizador no resuelve. VAN SEPARADAS: el código de provincia y el de
# comunidad NO coinciden (Baleares es 07 como provincia y 04 como comunidad; Madrid 28 / 12;
# Murcia 30 / 13; Asturias 33 / 03; Cantabria 39 / 06; Navarra 31 / 14; La Rioja 26 / 16).
EXTRA_PROV = {
    "coruna": "15", "lacoruna": "15", "araba": "01", "alava": "01", "araba alava": "01",
    "alicante alacant": "03", "alacant": "03", "alicante": "03",
    "castellon": "12", "castello": "12", "castello castellan": "12",
    "valencia": "46", "valenciana": "46", "valencia valenciana": "46",
    "baleares": "07", "balears": "07", "illes balears": "07",
    "rioja": "26", "gipuzkoa": "20", "guipuzcoa": "20", "bizkaia": "48", "vizcaya": "48",
    "ourense": "32", "orense": "32", "gerona": "17", "girona": "17", "lerida": "25",
    "lleida": "25", "asturias": "33", "cantabria": "39", "madrid": "28", "murcia": "30",
    "navarra": "31",
    "santa cruz tenerife": "38", "las palmas": "35", "ciudad real": "13",
}

EXTRA_CCAA = {
    "galicia": "11", "andalucia": "01", "aragon": "02", "cataluna": "09", "extremadura": "10",
    "canarias": "05", "castilla leon": "07", "castilla mancha": "08", "pais vasco": "15",
    "euskadi": "15", "ceuta": "18", "melilla": "19",
    "asturias": "03", "cantabria": "06", "madrid": "12", "murcia": "13", "navarra": "14",
    "rioja": "16", "baleares": "04", "balears": "04", "illes balears": "04",
    "valencia": "17", "valenciana": "17", "valencia valenciana": "17",
}


def normaliza(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace(",", " ").replace("/", " ")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return " ".join(p for p in s.split() if p not in RUIDO)


def slug(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def indice(tabla):
    """nombre normalizado -> código, desde la tabla oficial."""
    return {normaliza(nom): cod for cod, (nom, _) in tabla.items()}


def aplica(fichero, tabla, etiqueta):
    ruta = os.path.join(DATOS, fichero)
    if not os.path.exists(ruta):
        print("  falta", fichero)
        return
    d = json.load(open(ruta, encoding="utf-8"))
    idx = indice(tabla)
    puestos, faltan = 0, []
    for f in d["features"]:
        p = f["properties"]
        nom = p.get("nombre") or ""
        clave = normaliza(nom)
        extra = EXTRA_PROV if tabla is PROVINCIAS else EXTRA_CCAA
        cod = idx.get(clave) or extra.get(clave)
        # último recurso: probar cada palabra del nombre contra los alias
        if not cod:
            for trozo in re.split(r"[/,]", nom):
                cod = idx.get(normaliza(trozo)) or extra.get(normaliza(trozo))
                if cod:
                    break
        if cod and cod in tabla:
            p["cod_ine"] = cod
            p["codigo"] = cod                       # alias corto, mismo valor
            p["nuts"] = tabla[cod][1]
            p["nombre_oficial"] = tabla[cod][0]
            p["slug"] = slug(tabla[cod][0])
            puestos += 1
        else:
            faltan.append(nom)
    json.dump(d, open(ruta, "w", encoding="utf-8"), ensure_ascii=False)
    print("  %-14s %2d con código · %d sin código%s" % (
        etiqueta, puestos, len(faltan), (" -> " + ", ".join(map(str, faltan[:6]))) if faltan else ""))


def main():
    print("  normalización por código oficial (INE + NUTS)")
    aplica("irewater_hib_nuts3.geojson", PROVINCIAS, "provincias")
    aplica("irewater_hib_nuts2.geojson", CCAA, "comunidades")

    recibo = {
        "fuente": "Tablas oficiales INE (provincias 01-52, comunidades 01-19) y Eurostat NUTS 2021",
        "regla": "provincia y comunidad se identifican por cod_ine, nunca por nombre",
        "campos": ["cod_ine", "codigo", "nuts", "nombre_oficial", "slug"],
    }
    json.dump(recibo, open(os.path.join(DATOS, "normalizacion_recibo.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)
    print("  recibo -> datos/normalizacion_recibo.json")


if __name__ == "__main__":
    main()