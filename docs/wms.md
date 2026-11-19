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
