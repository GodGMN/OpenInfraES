# -*- coding: utf-8 -*-
"""I-ReWater HUB · capas vectoriales del visor de recursos hídricos.

El visor público `i-rewater-hub.com` sirve sus capas como **vector tiles (MVT)** desde un catálogo
abierto, sin clave:

    https://api.i-rewater-hub.com/api/v1/webgis/public          <- catálogo de capas
    https://api.i-rewater-hub.com/api/v1/tiles/<capa>/{z}/{x}/{y}.pbf

No hay endpoint de datos: solo tiles. Se recorren los tiles que cubren España y Portugal, se
decodifican y se deduplican por `id` (un objeto aparece en varios tiles por el solape de bordes).

    uv run --with mapbox-vector-tile python scripts/irewater.py --capa hib_edar
    uv run --with mapbox-vector-tile python scripts/irewater.py --capa hib_uda

Capas disponibles: hib_edar, hib_uda, hib_regadio, hib_regadio_particion, hib_demarcacion,
hib_nuts2, hib_nuts3.

**Origen del dato**: I-ReWater es un proyecto Interreg (España-Portugal-Francia) que agrega
información de fuentes nacionales. El valor está en los campos derivados —volumen reutilizable,
superficie regable, índice de impacto— que no están en ninguna fuente primaria en ese formato.
Se cita I-ReWater como agregador y se declara así en el recibo.
"""
import argparse
import datetime
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

import mapbox_vector_tile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos")
API = "https://api.i-rewater-hub.com/api/v1/tiles"
UA = {"User-Agent": "Mozilla/5.0 (compatible; OpenInfraES/1.0)",
      "Accept": "application/vnd.mapbox-vector-tile"}

# Cajas que cubren el ámbito del proyecto. España peninsular + Baleares, Canarias, Portugal.
CAJAS = [
    ("peninsula", 35.8, 44.0, -9.6, 4.6),
    ("baleares", 38.5, 40.2, 1.0, 4.6),
    ("canarias", 27.5, 29.5, -18.3, -13.3),
    ("portugal", 36.9, 42.2, -9.6, -6.1),
]



# Paleta para capas que se distinguen por polígono: sin color propio, todas se ven igual y no
# hay forma de separarlas en el mapa.
PALETA = ["#00897B", "#1E88E5", "#8E24AA", "#F4511E", "#43A047", "#FB8C00",
          "#5E35B1", "#00ACC1", "#C0CA33", "#D81B60", "#3949AB", "#7CB342",
          "#FDD835", "#6D4C41", "#E53935", "#039BE5", "#7E57C2", "#26A69A"]

def tiles_de(caja, z):
    """Genera los (x, y) de un zoom que cubren la caja."""
    _, lat0, lat1, lon0, lon1 = caja
    n = 2 ** z

    def xt(lon):
        return int((lon + 180) / 360 * n)

    def yt(lat):
        r = math.radians(lat)
        return int((1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * n)

    x0, x1 = xt(lon0), xt(lon1)
    y0, y1 = yt(lat1), yt(lat0)   # lat alta -> y baja
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            yield x, y


def a_lonlat(x, y, px, py, z, extent=4096):
    """Coordenada de tile a lon/lat.

    OJO: `mapbox_vector_tile` devuelve el eje Y HACIA ARRIBA (0 abajo, extent arriba), no hacia
    abajo como el MVT crudo. Sin invertirlo, todo sale desplazado: Besos aparecia 19 km al norte
    y la mediana del error contra las EDAR de OSM era de 10,6 km.
    """
    n = 2 ** z
    lon = (x + px / extent) / n * 360.0 - 180.0
    py = extent - py                      # <- la inversion que faltaba
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + py / extent) / n))))
    return round(lon, 6), round(lat, 6)


def proyecta(coords, x, y, z):
    """Convierte una geometria MVT entera: punto, anillo, lista de anillos o multipoligono."""
    if not coords:
        return None
    if isinstance(coords[0], (int, float)):
        return list(a_lonlat(x, y, coords[0], coords[1], z))
    salida = [proyecta(c, x, y, z) for c in coords]
    return [c for c in salida if c is not None]


def descarga(capa, z, x, y, reintentos=3):
    url = f"{API}/{capa}/{z}/{x}/{y}.pbf"
    for i in range(reintentos):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1.5 * (i + 1))
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None


def main():
    ap = argparse.ArgumentParser(description="I-ReWater HUB · capas vectoriales")
    ap.add_argument("--capa", required=True,
                    help="hib_edar | hib_uda | hib_regadio | hib_regadio_particion | "
                         "hib_demarcacion | hib_nuts2 | hib_nuts3")
    ap.add_argument("--zoom", type=int, default=8, help="zoom de los tiles (8 por defecto)")
    ap.add_argument("--etiqueta", help="nombre del fichero de salida")
    ap.add_argument("--pais", default="ES",
                    help="codigo de pais a conservar (ES por defecto; TODOS para todos)")
    a = ap.parse_args()

    etiqueta = a.etiqueta or a.capa
    z = a.zoom
    vistos = {}
    tiles_ok = tiles_vacios = tiles_error = 0
    total = 0

    for nombre_caja, *caja in CAJAS:
        for x, y in tiles_de((nombre_caja, *caja), z):
            total += 1
            b = descarga(a.capa, z, x, y)
            if not b:
                tiles_vacios += 1
                continue
            try:
                d = mapbox_vector_tile.decode(b)
            except Exception:
                tiles_error += 1
                continue
            tiles_ok += 1
            for capa_mvt, cont in d.items():
                for f in cont.get("features", []):
                    props = dict(f.get("properties") or {})
                    g = f.get("geometry") or {}
                    tipo = g.get("type")
                    coords = g.get("coordinates")
                    if tipo not in ("Point", "LineString", "MultiLineString",
                                    "Polygon", "MultiPolygon"):
                        continue
                    geom = {"type": tipo, "coordinates": proyecta(coords, x, y, z)}
                    if not geom["coordinates"]:
                        continue
                    # clave estable: id del objeto, o su primera coordenada si no hay id
                    clave = props.get("id") or props.get("codigo")
                    if not clave:
                        c0 = geom["coordinates"]
                        while isinstance(c0[0], list):
                            c0 = c0[0]
                        clave = f"{c0[0]},{c0[1]}"
                        if tipo == "Polygon":
                            clave += "|pol"
                    if clave in vistos:
                        continue
                    vistos[clave] = {
                        "type": "Feature", "geometry": geom, "properties": props}

    feats = list(vistos.values())

    # Los polígonos llegan PARTIDOS por el borde de cada tile y con id distinto por trozo
    # (29 objetos para 26 demarcaciones). Se unen por nombre en un MultiPolygon.
    if feats and feats[0]["geometry"]["type"] in ("Polygon", "MultiPolygon"):
        por_nombre = {}
        for f in feats:
            k = str(f["properties"].get("nombre") or f["properties"].get("id") or id(f))
            g = f["geometry"]
            anillos = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
            if k in por_nombre:
                por_nombre[k]["geometry"]["coordinates"].extend(anillos)
            else:
                copia = {"type": "Feature", "geometry": {"type": "MultiPolygon",
                                                         "coordinates": list(anillos)},
                         "properties": dict(f["properties"])}
                por_nombre[k] = copia
        if len(por_nombre) < len(feats):
            print(f"  unidos por nombre: {len(feats)} trozos -> {len(por_nombre)} objetos")
        feats = list(por_nombre.values())

    # color estable por objeto (ordenado por nombre) para las capas de polígonos
    if a.capa in ("hib_demarcacion", "hib_regadio", "hib_uda"):
        feats.sort(key=lambda f: str(f["properties"].get("nombre") or
                                     f["properties"].get("id") or ""))
        for i, f in enumerate(feats):
            f["properties"]["color"] = PALETA[i % len(PALETA)]

    if a.pais and a.pais.upper() != "TODOS":
        antes = len(feats)
        feats = [f for f in feats if str(f["properties"].get("pais", "")).upper() == a.pais.upper()]
        print(f"  filtrado a {a.pais}: {len(feats)} de {antes}")
    salida = os.path.join(DEST, f"irewater_{etiqueta}.geojson")
    json.dump({"type": "FeatureCollection", "features": feats},
              open(salida, "w", encoding="utf-8"), ensure_ascii=False)

    # resumen: distribucion de los campos categoricos mas utiles
    def cuenta(campo, tope=8):
        c = {}
        for f in feats:
            v = f["properties"].get(campo)
            if v not in (None, ""):
                c[str(v)] = c.get(str(v), 0) + 1
        return sorted(c.items(), key=lambda kv: -kv[1])[:tope]

    recibo = {
        "fuente": "I-ReWater HUB (proyecto Interreg)",
        "url_catalogo": "https://api.i-rewater-hub.com/api/v1/webgis/public",
        "capa": a.capa, "zoom": z,
        "features": len(feats), "tiles_leidos": tiles_ok,
        "tiles_vacios": tiles_vacios, "tiles_error": tiles_error,
        "tamano_kb": round(os.path.getsize(salida) / 1024, 1),
        "descargado": datetime.datetime.now().isoformat(timespec="seconds"),
        "pais_filtrado": a.pais,
        "paises": cuenta("pais", 6),
        "impacto": cuenta("indice_impacto_hidrologico", 6),
        "nota": ("Vector tiles MVT decodificados, geometrias reproyectadas de coordenadas de tile "
                 "a lon/lat y deduplicadas por id (o por primera coordenada si no hay id)."),
    }
    json.dump(recibo, open(os.path.join(DEST, f"irewater_{etiqueta}_recibo.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"  {len(feats)} objetos · {tiles_ok} tiles con datos de {total} pedidos")
    print(f"  {recibo['tamano_kb']} KB -> datos/irewater_{etiqueta}.geojson")
    if recibo["paises"]:
        print("   paises:", ", ".join(f"{k} {v}" for k, v in recibo["paises"]))
    if recibo["impacto"]:
        print("   impacto:", ", ".join(f"{k} {v}" for k, v in recibo["impacto"]))


if __name__ == "__main__":
    main()