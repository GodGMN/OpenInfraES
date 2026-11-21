# -*- coding: utf-8 -*-
"""Alertas de desastre con lugar en España (GDACS — Comisión Europea / JRC).

Fuente: https://www.gdacs.org/xml/rss.xml (RSS público, sin clave)
Qué trae: alertas activas y recientes de inundación (FL), terremoto (EQ), ciclón (TC), volcán (VO),
         sequía (DR) e incendio (WF), con nivel de alerta (verde/amarillo/naranja/rojo) y su fecha.

El RSS solo publica lo que está activo ahora, así que esta capa **acumula**: se lee el fichero
anterior, se añaden los eventos nuevos por (tipo, id) y se descartan los que ya salen de la ventana.
Sin acumular, la capa estaría vacía la mayoría de los días y una capa vacía no es una capa.

Salida: datos/alertas-gdacs.geojson + datos/alertas-gdacs_recibo.json
"""
import email.utils
import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone

UA = {"User-Agent": "OpenInfraES/1.0", "Accept": "application/xml,text/xml,*/*;q=0.8"}
URL = "https://www.gdacs.org/xml/rss.xml"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos", "alertas-gdacs.geojson")
VENTANA_DIAS = 120

NS = {"gdacs": "http://www.gdacs.org", "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#",
      "georss": "http://www.georss.org/georss"}
BBOX = (27.0, 44.5, -19.5, 5.0)          # Sur, Norte, Oeste, Este: España + islas

TIPOS = {"FL": "Inundación", "EQ": "Terremoto", "TC": "Ciclón tropical", "VO": "Volcán",
         "DR": "Sequía", "WF": "Incendio forestal", "TS": "Tsunami"}
NIVELES = {"Green": "Verde", "Yellow": "Amarillo", "Orange": "Naranja", "Red": "Rojo"}
COLORES = {"Verde": "#22c55e", "Amarillo": "#facc15", "Naranja": "#fb923c", "Rojo": "#ef4444"}


def texto(el, ruta):
    v = el.findtext(ruta, namespaces=NS)
    return v.strip() if isinstance(v, str) and v.strip() else None


def leer_previos():
    if not os.path.exists(DEST):
        return []
    try:
        return json.load(open(DEST, encoding="utf-8")).get("features") or []
    except Exception:
        return []


def fecha_iso(txt):
    """Las fechas del RSS vienen en RFC 822 ('Sun, 15 Nov 2026 01:33:00 GMT'): se convierten."""
    if not txt:
        return None
    try:
        return email.utils.parsedate_to_datetime(txt).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return txt[:25]


def coordenadas(item):
    """GDACS no es constante: unas veces da geo:lat/geo:long y otras georss:point (lat lon)."""
    try:
        return float(texto(item, "geo:lat")), float(texto(item, "geo:long"))
    except (TypeError, ValueError):
        pass
    p = texto(item, "georss:point")
    if p and len(p.split()) >= 2:
        try:
            lat, lon = p.split()[:2]
            return float(lat), float(lon)
        except ValueError:
            return None
    return None


def main():
    req = urllib.request.Request(URL, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        raiz = ET.fromstring(r.read())

    limite = date.today() - timedelta(days=VENTANA_DIAS)
    previos = {f["properties"]["id"]: f for f in leer_previos()}
    nuevos = 0

    for item in raiz.iter("item"):
        et = texto(item, "gdacs:eventtype")
        eid = texto(item, "gdacs:eventid") or (texto(item, "guid") or "").replace(et or "", "", 1)
        if not et or not eid:
            continue
        coords = coordenadas(item)
        if not coords:
            continue
        lat, lon = coords
        if not (BBOX[0] <= lat <= BBOX[1] and BBOX[2] <= lon <= BBOX[3]):
            continue

        clave = "%s:%s" % (et, eid)
        nivel = NIVELES.get(texto(item, "gdacs:alertlevel"), texto(item, "gdacs:alertlevel") or "—")
        inicio = fecha_iso(texto(item, "gdacs:fromdate") or texto(item, "pubDate"))
        fin = fecha_iso(texto(item, "gdacs:todate"))
        tipo_es = TIPOS.get(et, et)
        pais = texto(item, "gdacs:country") or "España"
        if pais in ("Spain", "España"):
            pais = "España"
        dia = (inicio or "")[:10]
        titulo = "%s %s · %s · %s" % (tipo_es, nivel.lower(), pais, dia) if dia else "%s %s" % (tipo_es, nivel.lower())
        previos[clave] = {
            "type": "Feature",
            "properties": {
                "id": clave,
                "titulo": titulo,
                "tipo_evento": tipo_es,
                "nivel": nivel,
                "color": COLORES.get(nivel, "#94a3b8"),
                "pais": pais,
                "desde": inicio,
                "hasta": fin,
                "publicado": fecha_iso(texto(item, "pubDate")),
                "enlace": texto(item, "link"),
                "fuente": "GDACS — Comisión Europea (JRC)",
            },
            "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
        }
        nuevos += 1

    # fuera de la ventana: se van (una alerta de hace un año no es una alerta)
    feats, caducados = [], 0
    for f in previos.values():
        desde = (f["properties"].get("desde") or "")[:10]
        try:
            if desde and datetime.strptime(desde, "%Y-%m-%d").date() < limite:
                caducados += 1
                continue
        except ValueError:
            pass
        feats.append(f)

    orden = {"Rojo": 0, "Naranja": 1, "Amarillo": 2, "Verde": 3}
    feats.sort(key=lambda f: (orden.get(f["properties"]["nivel"], 9), f["properties"]["desde"]), reverse=False)
    json.dump({"type": "FeatureCollection", "features": feats},
              open(DEST, "w", encoding="utf-8"), ensure_ascii=False)

    por_tipo = {}
    for f in feats:
        por_tipo[f["properties"]["tipo_evento"]] = por_tipo.get(f["properties"]["tipo_evento"], 0) + 1
    recibo = {
        "features": len(feats),
        "por_tipo": por_tipo,
        "nuevos_en_esta_lectura": sum(1 for f in feats if f["properties"]["publicado"]),
        "leidos_del_rss": nuevos,
        "ventana_dias": VENTANA_DIAS,
        "desde": limite.isoformat(),
        "fecha_dato": max((f["properties"]["publicado"] or "")[:16] for f in feats) if feats else None,
        "fuente": "GDACS (Comisión Europea · JRC)",
        "url": URL,
        "fichero": "alertas-gdacs.geojson",
        "acumulativa": True,
        "caducados_retirados": caducados,
    }
    json.dump(recibo, open(DEST.replace(".geojson", "_recibo.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("  alertas GDACS en España: %d (ventana %d días) · %s"
          % (len(feats), VENTANA_DIAS, ", ".join("%s %d" % (k, v) for k, v in por_tipo.items())))
    for f in feats[:6]:
        p = f["properties"]
        print("   %-8s %-18s %s" % (p["nivel"], p["tipo_evento"], (p["titulo"] or "")[:58]))


if __name__ == "__main__":
    main()
