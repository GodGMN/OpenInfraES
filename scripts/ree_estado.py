# -*- coding: utf-8 -*-
"""Foto del sistema eléctrico con la API pública de REE (apidatos, sin clave).

Ojo con el formato: el JSON es JSON:API y los valores NO están en
data.attributes.values, sino en la lista `included[]`, un objeto por tecnología.

Deja datos/ree_estado.json con generación por tecnología, demanda y balance del día.
"""
import os
import json
import urllib.request
from datetime import date, timedelta

UA = {"User-Agent": "Mozilla/5.0 (compatible; OpenInfraES/1.0)", "Accept": "application/json"}
BASE = "https://apidatos.ree.es/es/datos/"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "datos")


def pedir(categoria, widget, dia):
    url = "%s%s/%s?start_date=%sT00:00&end_date=%sT23:59&time_trunc=day" % (
        BASE, categoria, widget, dia, dia)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8")), url


def serie(d):
    """Devuelve [(titulo, valor, tipo, color)] desde `included`."""
    salida = []
    for item in d.get("included", []):
        a = item.get("attributes", {})
        vals = a.get("values") or []
        if not vals:
            continue
        salida.append((a.get("title") or item.get("type"), vals[0]["value"],
                       a.get("type"), a.get("color")))
    return salida


def main():
    ayer = (date.today() - timedelta(days=1)).isoformat()
    salida = {"fecha": ayer, "fuente": "REE apidatos (público, sin clave)",
              "formato": "JSON:API — los valores van en included[]", "series": {}, "urls": {}}

    for nombre, cat, wid in (("generacion", "generacion", "estructura-generacion"),
                             ("demanda", "demanda", "evolucion"),
                             ("balance", "balance", "balance-electrico")):
        try:
            d, url = pedir(cat, wid, ayer)
        except Exception as e:
            print("  %-12s ERROR %s" % (nombre, type(e).__name__))
            continue
        filas = serie(d)
        salida["series"][nombre] = [{"titulo": t, "valor": round(v, 1), "tipo": ti, "color": c}
                                    for t, v, ti, c in filas]
        salida["urls"][nombre] = url
        print("  %-12s %2d series · actualizado %s" % (
            nombre, len(filas), d.get("data", {}).get("attributes", {}).get("last-update", "—")))

    gen = salida["series"].get("generacion", [])
    total = next((s["valor"] for s in gen if s["titulo"].lower().startswith("generación total")), 0)
    print("\n  Generación por tecnología (%s) — total %s MWh" % (ayer, format(total, ",.0f")))
    for s in sorted(gen, key=lambda x: -x["valor"])[:12]:
        if s["titulo"].lower().startswith("generación total"):
            continue
        pct = 100 * s["valor"] / total if total else 0
        print("   %-30s %11s MWh  %5.1f%%" % (s["titulo"][:30], format(s["valor"], ",.0f"), pct))

    json.dump(salida, open(DEST + "/ree_estado.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n  -> datos/ree_estado.json")


if __name__ == "__main__":
    main()
