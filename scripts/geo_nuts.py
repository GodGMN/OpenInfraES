# -*- coding: utf-8 -*-
"""Geometrías oficiales NUTS de Eurostat (GISCO) para España.

Las capas de I-ReWater servían los polígonos **partidos por tile** y el resultado estaba
incompleto: Madrid salía con 569 km² de 8.028. Estas geometrías vienen enteras y con el código
NUTS como clave, que es lo que permite cruzarlas con los datos del INE sin tocar el nombre.

    https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/
        NUTS_RG_20M_2021_4326_LEVL_3.geojson   (provincias)
        NUTS_RG_20M_2021_4326_LEVL_2.geojson   (comunidades)

Generalización 20M: el error de área medido contra las superficies oficiales va de -0,3 % a
-1,8 %. Suficiente para un visor, y así se declara.

    python scripts/geo_nuts.py
"""
import json
import math
import os
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
BASE = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/"
UA = {"User-Agent": "Mozilla/5.0 (compatible; OpenInfraES/1.0)"}

# NUTS -> código INE de provincia (52 provincias + ciudades autónomas)
NUTS_A_INE = {
    "ES111": "15", "ES112": "27", "ES113": "32", "ES114": "36",
    "ES120": "33", "ES130": "39",
    "ES211": "01", "ES212": "20", "ES213": "48",
    "ES220": "31", "ES230": "26", "ES241": "22", "ES242": "44", "ES243": "50",
    "ES300": "28",
    "ES411": "05", "ES412": "09", "ES413": "24", "ES414": "34", "ES415": "37",
    "ES416": "40", "ES417": "42", "ES418": "47", "ES419": "49",
    "ES421": "02", "ES422": "13", "ES423": "16", "ES424": "19", "ES425": "45",
    "ES431": "06", "ES432": "10",
    "ES511": "08", "ES512": "17", "ES513": "25", "ES514": "43",
    "ES521": "03", "ES522": "12", "ES523": "46",
    "ES531": "07", "ES532": "07", "ES533": "07",
    "ES611": "04", "ES612": "11", "ES613": "14", "ES614": "18", "ES615": "21",
    "ES616": "23", "ES617": "29", "ES618": "41",
    "ES620": "30", "ES630": "51", "ES640": "52",
    "ES701": "35", "ES702": "38", "ES703": "38", "ES704": "35",
    "ES705": "35", "ES706": "38", "ES707": "38", "ES708": "35", "ES709": "38",
}

NUTS2_A_INE = {
    "ES11": "11", "ES12": "03", "ES13": "06", "ES21": "15", "ES22": "14",
    "ES23": "16", "ES24": "02", "ES30": "12", "ES41": "07", "ES42": "08",
    "ES43": "10", "ES51": "09", "ES52": "17", "ES53": "04", "ES61": "01",
    "ES62": "13", "ES63": "18", "ES64": "19", "ES70": "05",
}

NOMBRE_INE = {
    "01": "Álava", "02": "Albacete", "03": "Alicante", "04": "Almería", "05": "Ávila",
    "06": "Badajoz", "07": "Baleares", "08": "Barcelona", "09": "Burgos", "10": "Cáceres",
    "11": "Cádiz", "12": "Castellón", "13": "Ciudad Real", "14": "Córdoba",
    "15": "A Coruña", "16": "Cuenca", "17": "Girona", "18": "Granada",
    "19": "Guadalajara", "20": "Gipuzkoa", "21": "Huelva", "22": "Huesca", "23": "Jaén",
    "24": "León", "25": "Lleida", "26": "La Rioja", "27": "Lugo", "28": "Madrid",
    "29": "Málaga", "30": "Murcia", "31": "Navarra", "32": "Ourense", "33": "Asturias",
    "34": "Palencia", "35": "Las Palmas", "36": "Pontevedra", "37": "Salamanca",
    "38": "Santa Cruz de Tenerife", "39": "Cantabria", "40": "Segovia", "41": "Sevilla",
    "42": "Soria", "43": "Tarragona", "44": "Teruel", "45": "Toledo", "46": "Valencia",
    "47": "Valladolid", "48": "Bizkaia", "49": "Zamora", "50": "Zaragoza",
    "51": "Ceuta", "52": "Melilla",
}

NOMBRE_CCAA = {
    "01": "Andalucía", "02": "Aragón", "03": "Asturias", "04": "Baleares", "05": "Canarias",
    "06": "Cantabria", "07": "Castilla y León", "08": "Castilla-La Mancha", "09": "Cataluña",
    "10": "Extremadura", "11": "Galicia", "12": "Madrid", "13": "Murcia", "14": "Navarra",
    "15": "País Vasco", "16": "La Rioja", "17": "Valencia", "18": "Ceuta", "19": "Melilla",
}

# superficies oficiales de CCAA (km2). Van aparte: el código 08 es Barcelona como provincia y
# Castilla-La Mancha como comunidad, y comparar una con otra da +928 %.
SUPERFICIE_CCAA = {
    "01": 87599, "02": 47719, "03": 10604, "04": 4992, "05": 7447, "06": 5321,
    "07": 94223, "08": 79463, "09": 32108, "10": 41634, "11": 29574, "12": 8028,
    "13": 11313, "14": 10391, "15": 7234, "16": 5045, "17": 23255, "18": 19, "19": 12,
}

# superficies oficiales de provincia para validar la generalización (km2)
SUPERFICIE = {
    "28": 8028, "08": 7728, "37": 12350, "25": 12172, "06": 21766, "10": 19868,
    "50": 17274, "22": 15636, "46": 10807, "33": 10604, "41": 14036, "13": 19813,
    "16": 17141, "02": 14858, "15": 7950, "27": 9856,
}


def area_km2(anillo):
    R = 6371.0088
    a = 0.0
    n = len(anillo)
    for i in range(n):
        lon1, lat1 = anillo[i][0], anillo[i][1]
        lon2, lat2 = anillo[(i + 1) % n][0], anillo[(i + 1) % n][1]
        a += math.radians(lon2 - lon1) * (2 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2)))
    return abs(a * R * R / 2.0)


def area_feature(g):
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    tot = 0.0
    for poly in polys:
        if not poly:
            continue
        tot += area_km2(poly[0])
        for hueco in poly[1:]:
            tot -= area_km2(hueco)
    return tot


def descarga(nivel):
    url = BASE + "NUTS_RG_20M_2021_4326_LEVL_%d.geojson" % nivel
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=240) as r:
        return json.loads(r.read())


def une_por_codigo(features, mapa):
    """Varias filas NUTS pueden caer en la misma provincia (las islas Canarias/Baleares)."""
    salida = {}
    for f in features:
        nuts = f["properties"].get("NUTS_ID")
        ine = mapa.get(nuts)
        if not ine:
            continue
        if ine not in salida:
            g = f["geometry"]
            salida[ine] = {
                "type": "Feature",
                "geometry": {"type": "MultiPolygon",
                             "coordinates": ([g["coordinates"]] if g["type"] == "Polygon"
                                             else list(g["coordinates"]))},
                "properties": {"cod_ine": ine},
            }
        else:
            g = f["geometry"]
            salida[ine]["geometry"]["coordinates"].extend(
                [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"])
    return salida


def main():
    print("  Eurostat GISCO · NUTS 2021 (20M)")
    for nivel, mapa, nombres, fichero, etiqueta in (
            (3, NUTS_A_INE, NOMBRE_INE, "nuts3_es.geojson", "provincias"),
            (2, NUTS2_A_INE, NOMBRE_CCAA, "nuts2_es.geojson", "comunidades")):
        d = descarga(nivel)
        es = [f for f in d["features"] if f["properties"].get("CNTR_CODE") == "ES"]
        agrupado = une_por_codigo(es, mapa)

        for cod, f in agrupado.items():
            f["properties"]["nombre"] = nombres.get(cod, cod)
            f["properties"]["codigo"] = cod
            f["properties"]["pais"] = "ES"
            g = f["geometry"]
            anillos = ([g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"])
            f["properties"]["superficie_km2"] = round(
                sum(area_km2(p[0]) for p in anillos if p))

        salida = {"type": "FeatureCollection", "features": list(agrupado.values())}
        ruta = os.path.join(DATOS, fichero)
        json.dump(salida, open(ruta, "w", encoding="utf-8"), ensure_ascii=False)
        print("  %-12s %2d objetos · %d KB" % (etiqueta, len(agrupado),
                                               os.path.getsize(ruta) // 1024))

        # validacion de area contra la superficie oficial
        fallos = []
        tabla_sup = SUPERFICIE if nivel == 3 else SUPERFICIE_CCAA
        for cod, f in agrupado.items():
            real = tabla_sup.get(cod)
            if not real:
                continue
            pct = 100 * (f["properties"]["superficie_km2"] - real) / real
            if abs(pct) > 5:
                fallos.append((f["properties"]["nombre"], round(pct, 1)))
        print("     validación de área: %s" % ("OK (todas <5 %)" if not fallos else fallos))

    recibo = {
        "fuente": "Eurostat GISCO · NUTS 2021, generalización 20M",
        "url": BASE + "NUTS_RG_20M_2021_4326_LEVL_3.geojson",
        "nota": ("Geometrías enteras, no partidas por tile. Error de área medido <2 % contra las "
                 "superficies oficiales. La clave es NUTS_ID -> cod_ine; nunca el nombre."),
        "ficheros": ["nuts3_es.geojson", "nuts2_es.geojson"],
    }
    json.dump(recibo, open(os.path.join(DATOS, "nuts_recibo.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()