import math, urllib.request, json, sys
import mapbox_vector_tile

def t(lat, lon, z):
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    y = (1 - math.log(math.tan(math.radians(lat)) + 1/math.cos(math.radians(lat)))/math.pi)/2 * n
    return x, int(y)

UA = {"User-Agent": "Mozilla/5.0"}
z = 8
x, y = t(40.4, -3.7, z)
u = f"https://api.i-rewater-hub.com/api/v1/tiles/hib_edar/{z}/{x}/{y}.pbf"
b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read()
print("  bytes:", len(b))
d = mapbox_vector_tile.decode(b)
for capa, cont in d.items():
    f = cont.get("features", [])
    print(f"  capa '{capa}': {len(f)} features")
    if f:
        print("   propiedades de la primera:")
        for k, v in list(f[0]["properties"].items()):
            print(f"     {k}: {str(v)[:70]}")
        print("   geometria:", f[0]["geometry"]["type"])
