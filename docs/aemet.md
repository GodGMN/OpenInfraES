---
titulo: AEMET — avisos meteorológicos, con y sin geometría
fecha: 2026-11-16
ambito: riesgo
estado: publicado
---

# AEMET — avisos meteorológicos

Hay **dos vías** para los mismos avisos, y dan cosas distintas. Conviene saber cuál usar.

## Vía 1 — Meteoalerta con geometría (la buena)

AEMET publica las **zonas de aviso como polígonos**, sin clave, en la propia página de avisos.

```
https://www.aemet.es/es/eltiempo/prediccion/avisos
  -> /es/geojson/download/avisos/geojson_<epoch>.tar.gz     (~2,2 MB)
      r_D+0_<elaborado>_penbal_<...>.geojson   península y Baleares
      r_D+0_<elaborado>_can_<...>.geojson      Canarias
```

El tar se **regenera cada hora** y trae D+0 (hoy), D+1 y D+2; `penbal` y `can` separan los dos ámbitos.
Los ficheros de **menos de 300 bytes van vacíos**: esa área no tiene avisos.

```bash
python scripts/aemet_geo.py
```

Salida: `datos/aemet_zonas.geojson` (zonas con aviso, como polígonos) y su recibo.

**Medido el 2026-11-18 (elaborado 17:57):** **70 zonas con aviso — 59 rojas y 11 naranjas.** Cada zona
trae `zona`, `provincia`, `codigo`, `nivel`, `nivel_txt`, los fenómenos y la descripción de cada aviso con
sus horas de inicio y fin.

Capa **«Avisos AEMET (zonas)»** en el grupo Riesgo, con el relleno coloreado por nivel: amarillo, naranja
y rojo. Es la única capa del visor que cambia de color por feature.

## Vía 2 — Meteoalarm sin geometría

`https://feeds.meteoalarm.org/api/v1/warnings/feeds-spain` (EUMETNET, AEMET es el nodo español) da los
avisos en JSON, en abierto y sin clave: **351 avisos, 177 vigentes** el 2026-11-16.

Pero **no trae coordenadas ni polígono**: las áreas son **comarcas** («Interior de Pontevedra»,
«Albarracín y Jiloca»), 233 distintas, sin geometría. Por eso este feed **no se pinta**: se muestra como
lista en el panel de Riesgo, junto a la capa de zonas.

```bash
python scripts/aemet.py     # -> datos/aemet_avisos.json
```

## Trampas

- **El CAP de Meteoalarm viene en español y en inglés.** Sin filtrar por `language`, cada aviso se cuenta
  **dos veces**: 702 en vez de 351. Y el «evento» sale duplicado («vientos de nivel amarillo» y «Moderate
  wind warning» en la misma lista).
- **El tar.gz hay que buscarlo en el HTML de la página de avisos**, con su nombre exacto:
  `geojson_\d+\.tar\.gz`. La URL lleva un epoch que cambia en cada regeneración, así que no se puede
  construir a mano.
- **El HTML de AEMET viene en `iso-8859-15`, no en UTF-8.** Decodificarlo como UTF-8 destroza los acentos
  y el regex del enlace sigue funcionando, así que el fallo no se nota hasta que lees los nombres.
- **Los ficheros vacíos pesan menos de 300 bytes**, no cero. Comprobar `> 300` y no `> 0`, o se intenta
  parsear un GeoJSON de 200 bytes y salta una excepción que tumba el bucle.
- **AEMET OpenData (`opendata.aemet.es`) exige clave** para `avisos_cap`. Ese camino no hace falta: el
  `tar.gz` de la web es el mismo dato con geometría y sin registro.

## Lo que hay en el repo de kit72h

El mecanismo salió de `scripts/noticias.py` de **`Ntizar/kit72h`**, que ya lo tenía resuelto para su cron
de noticias. Es el segundo caso en este proyecto donde un repo propio tenía la respuesta antes que la
búsqueda desde cero (el primero fue la cabecera `ApiKey` del NAP en `nap-dashboard`).