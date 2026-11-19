# Servicios ráster oficiales: por qué solo entra el PNOA

Probé a superponer los WMS oficiales que usa el visor de I-ReWater (SIGPAC, Catastro, red
hidrográfica del IDEe). **Solo el PNOA acaba viéndose**, y por tres motivos distintos que conviene
tener escritos.

## 1. El CRS: ninguno soporta EPSG:3857

El mapa usa **EPSG:3857** (Web Mercator). Consultados los `GetCapabilities`:

| Servicio | CRS disponibles |
|---|---|
| Hidrografía (IDEe) | 25828-25831, 3035, 32628-32629, CRS:84 |
| Catastro | 23029-23031, 25829-25831, 32627... |
| PNOA | los mismos + **3857** |
| SIGPAC | 25829-25831, **3857**, 4326 |

Leaflet pide el `BBOX` en el CRS del mapa. Si se le fuerza `crs: L.CRS.EPSG4326`, la petición sale
con el bbox correcto —**comprobado: `SRS=EPSG:4326&BBOX=-3.718,40.426,...`**— pero el tile se
coloca en la rejilla del 3857, así que **el contenido corresponde a otra zona** y aparecen parches
del mapa equivocado en las esquinas.

**Mezclar CRS en `L.tileLayer.wms` no funciona.** No es un bug de configuración: es que la rejilla
de teselas y el bbox tienen que hablar el mismo idioma.

## 2. El filtro del tema: la ortofoto salía en blanco y negro

Con el PNOA ya en teselas 3857, seguía sin vérsele el color. La causa estaba en el CSS:

```css
html[data-base="radar"] .leaflet-tile-pane {
  filter: invert(1) brightness(2.15) contrast(1.22) saturate(0);
}
```

Ese filtro, que da el aspecto radar al mapa base, **se aplica a todas las teselas del pane**,
ortofoto incluida. `saturate(0)` la dejaba en gris.

**Solución**: un pane propio (`rasterPane`) fuera del `tile-pane`, con z-index 250:

```js
mapa.createPane("rasterPane");
mapa.getPane("rasterPane").style.zIndex = 250;
// y en la capa: { pane: "rasterPane" }
```

## 3. La que sí entra: PNOA por WMTS

El IGN publica el PNOA como **WMTS con `EPSG:3857`**, que es tesela nativa y no necesita
reproyección:

```
https://www.ign.es/wmts/pnoa-ma?layer=OI.OrthoimageCoverage&style=default
  &tilematrixset=EPSG:3857&Service=WMTS&Request=GetTile&Version=1.0.0
  &Format=image/jpeg&TileMatrix={z}&TileCol={x}&TileRow={y}
```

Verificado: tesela de Madrid z16 (32094/24710) → 23 KB de JPEG con los tejados a color.

## Lo que queda fuera, y por qué

- **SIGPAC**: soporta 3857 y responde 200, pero devuelve **120 bytes** (PNG vacío) en todos los
  bbox probados. No publica datos por esta vía.
- **Catastro**: WMS en 4326/25830. Sus teselas (`/Cartografia/Tiles/...`) dan 404.
- **Hidrografía (IDEe)**: WMS en 4326/25830, sin WMTS. Su conexión al puerto WMTS se corta.

Para estos tres la vía sería **descargar el vectorial por WFS** y pintarlo como GeoJSON. La
hidrografía ya está cubierta por OSM (`rios.geojson`, 260 ríos) y el Catastro es un servicio
por referencia catastral, no una capa de infraestructura.

## Ficheros

- Capa `pnoa` (`tipo:"xyz"`) en `index.html`.
- Constante `BASES_PNOA` con la misma plantilla, para el selector de mapa base.

## Servicios probados el 19-11-2026: por qué NO se integran todavía

Cuatro servicios responden con `GetCapabilities` y con **imagen válida pedida a mano**, y ninguno se
pinta bien dentro de Leaflet. Es el mismo fallo del PNOA de arriba, y merece quedar escrito con la
medida, no con un «no funciona».

| Servicio | GetCapabilities | GetMap directo | En Leaflet |
|---|---|---|---|
| **IGME** — `mapas.igme.es/gis/services/Cartografia_Geologica/IGME_GEODE_50/MapServer/WMSServer` | 200, 37 KB, 20 capas | — | pide teselas, no pinta |
| **EMODnet** — `ows.emodnet-bathymetry.eu/wms` | 200, 51 KB, 53 capas | **200, 84 KB, PNG con batimetría real** | pide teselas, no pinta |
| **Catastro** — `ovc.catastro.meh.es/Cartografia/WMS/ServidorWMS.aspx` | 200, 28 KB, 27 capas | — | desalineado |
| **Adif IDEADIF** — `ideadif.adif.es/services/wfs` | **403 (Akamai)** | — | no aplica |

**La causa, medida dos veces y con la misma firma que el PNOA:** el mapa base está en
**EPSG:3857** y estos servicios piden el bbox en **EPSG:4326**. Forzar `crs: L.CRS.EPSG4326` hace
que Leaflet cambie la proyección del *tile layer*, y entonces las teselas se piden con un bbox que
el servicio devuelve correcto **pero referido a otra retícula**: la imagen llega (se ve en el
contador de teselas) y aterriza desplazada o en parches.

**Lo probado para arreglarlo y descartado:**

- `version:"1.3.0"` con `crs: CRS:84` — la 1.3.0 invierte el orden de ejes (`lat,lon`) y Leaflet
  no lo compensa. Fue la primera prueba de EMODnet: la capa pidió teselas y el mar salió blanco.
- `version:"1.1.1"` con `SRS` y `lon,lat` — el orden de ejes es el correcto, la capa siguió sin
  cuadrar con la costa. Segunda prueba, mismo resultado visual.
- `uppercase:true` + `zIndex` — no afecta a la geometría, solo al estilo de la petición.

**Lo que sí funciona y es la vía:** pedir el **GetMap completo** con el bbox del encuadre y pintarlo
como `L.imageOverlay` con las esquinas en 4326, en vez de teselar. Un solo `GetMap` por movimiento
de mapa, sin retícula de teselas que desalinear. No se ha implementado porque exige recalcular en
`moveend` y probar el coste en un mapa que ya carga 5.800 puntos; queda como la vía para la próxima
tanda, no como un «casi».

**Y la lección que sí queda cerrada:** un `Content-Type: image/png` de 200 no significa que la capa
esté bien puesta. La prueba de fuego es **mirar la captura**, no el contador de teselas. Las dos
veces que di la capa por buena fue con 143 teselas en el DOM y el mar en blanco.
