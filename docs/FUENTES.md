---
titulo: Fuentes oficiales — ficha por ficha
fecha: 2026-11-16
ambito: espana
estado: publicado
---

# Fuentes oficiales de OpenInfraES

Cada capa del visor sale de una de estas fuentes. Aquí está, para cada una: **qué publica el
organismo**, la **URL oficial**, **cómo se obtiene** el dato (endpoint exacto), la **licencia**, la
**frecuencia** de actualización, **qué capas alimenta** y qué **limitaciones** tiene.

Regla del repositorio: solo se cita el organismo que produce el dato. Si se llega a él a través de
otra web, esa web no aparece aquí.

---

## 1. IGN — Instituto Geográfico Nacional (SCNE)

**Qué publica.** La Base Topográfica Nacional (BTN) y las teselas de cartografía base. Es la
cartografía oficial de España, y el marco del Sistema Cartográfico Nacional (Ley 14/2010).

- **URL oficial**: <https://www.ign.es> · <https://www.scne.es>
- **Cómo se obtiene**:
  - Teselas del mapa base: `https://www.ign.es/wmts/ign-base?request=GetTile&service=WMTS&version=1.0.0&layer=IGNBase-gris&style=default&tilematrixset=GoogleMapsCompatible&tilematrix={z}&tilerow={y}&tilecol={x}&format=image/png`
  - Capas vectoriales derivadas de la BTN: ver ficha 2.
- **Licencia**: CC BY 4.0 · atribución `© scne.es`.
- **Frecuencia**: continua (BTN Continua).
- **Alimenta**: fondo del mapa (4 bases: radar, gris, color, ortofoto PNOA).
- **Limitaciones**: el WMTS devuelve **200 con cuerpo vacío** si no se envía `Accept: image/*` y
  `Referer`. No tiene teselas oscuras: el tema oscuro se hace con un filtro CSS sobre la capa de solo
  líneas (`IGNBaseTodo-nofondo`), porque invertir la capa gris aplasta el mar contra la tierra y el
  mapa se queda sin costas.

## 2. Atlas Estratégico de España — vía de descarga de capas del IGN y del MITECO

**Qué publica.** GeoJSON ya vectorizados de infraestructura: red eléctrica, subestaciones, nuclear,
gas, embalses, desaladoras, hidrógeno. No es el productor del dato: es quien lo vectoriza y lo sirve.

- **URL**: <https://atlas.eltercioviejo.com> · licencia de los datos, **CC BY 4.0**.
- **Cómo se obtiene**: `https://atlas.eltercioviejo.com/datos/capas/<id>.geojson`, con manifiesto en
  `/datos/manifest.json` (42 capas; aquí se usan 17).
- **Origen real de cada capa**: el campo `atribucion` del propio dato dice de dónde viene. La red y
  las subestaciones son **obra derivada de la BTN Continua del IGN**; los embalses vienen del
  **Boletín Hidrológico del MITECO**, con su fecha en el campo `fecha_dato`.
- **Alimenta**: subestaciones (657), interconexiones, nuclear (7), regasificación, almacenamiento de
  gas, refinerías, embalses (402), desaladoras (28).
- **Limitaciones**: el manifiesto trae el campo `fichero` relativo a `/datos/`, no a la raíz (17
  capas dieron 404 por eso). Algunas capas **mezclan geometrías**: `red-electrica` son 657 polígonos
  de subestación **y** 2 tendidos; hay que mirar la propiedad `categoria`, no el tipo de la primera
  feature.

## 3. MITECO — Ministerio para la Transición Ecológica

Tres cosas distintas, las tres oficiales:

### 3a. Boletín Hidrológico (el dato primario de los embalses)
- **Cómo se obtiene**: es el origen del campo `agua_actual_hm3` de la capa de embalses, consultado a
  través de la ficha 2. El parte es **semanal** y trae fecha propia.
- **Limitaciones**: cubre embalses peninsulares de más de 5 hm³.

### 3b. Precios de carburantes (tiempo real)
- **URL oficial**: `https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/`
- **Cómo se obtiene**: `GET` a esa URL. Devuelve ~12 MB de JSON con **11.528 estaciones**.
  `scripts/carburantes.py` lo adelgaza a 11.433 con precio válido.
- **Licencia**: reutilización con atribución (Ley 37/2007).
- **Frecuencia**: **cada 30 minutos**.
- **Alimenta**: capa de carburantes, con precio de gasóleo A, gasolina 95/98, GNC, GNL y H₂.
- **Limitaciones**: el servidor **corta el handshake TLS con Python** (`SSLEOFError`): hay que
  descargar con `curl`. Los números vienen con **coma decimal** (`39,211417`) y las claves con
  espacios y tildes (`Precio Gasoleo A`, `Longitud (WGS84)`).

### 3c. Desaladoras e inventario de presas
- **URL oficial**: <https://www.miteco.gob.es/es/agua.html>
- **Cómo se obtiene**: las desaladoras llegan vectorizadas por la ficha 2; el inventario de presas
  (≈3.200) **no publica geometría**, solo listados.

## 4. MITMA — Ministerio de Transportes (visor Hermes)

**Qué publica.** La red de carreteras del Estado, puertos, aeropuertos, terminales intermodales y el
registro de combustibles alternativos.

- **URL oficial**: <https://mapas.fomento.gob.es/VisorHermes/>
- **Cómo se obtiene** (ArcGIS REST abierto, sin clave):
  `https://mapas.fomento.gob.es/arcgis/rest/services/Hermes/<servicio>/MapServer/<capa>/query?where=1=1&outFields=*&returnGeometry=true&outSR=4326&f=geojson`
- **Licencia**: CC BY 4.0 (scne.es).
- **Alimenta**: carreteras (1.602), puertos (45), terminales portuarias (440), terminales de
  aeropuerto (102), terminales de mercancías (383), estaciones GNL/GNC/H₂ (165 de 11.485).
- **Limitaciones**: `resultRecordCount=1000` **falla** con HTML de error → paginar de 500 en 500. La
  geometría completa de carreteras son ~85 MB → `maxAllowableOffset=0.002` la deja en 0,63 MB. La
  **capa 0 de aeropuertos no admite query** (hay que usar la 1 y la 2).

## 5. REE — Red Eléctrica de España

**Qué publica.** Generación por tecnología, demanda, balance eléctrico, intercambios.

- **URL oficial**: <https://www.ree.es/es/apidatos> (sin clave) · <https://api.esios.ree.es> (con clave)
- **Cómo se obtiene**:
  - Sin clave: `https://apidatos.ree.es/es/datos/generacion/estructura-generacion?start_date=...&end_date=...&time_trunc=day`
  - Con clave: `https://api.esios.ree.es/indicators/<id>` con cabecera `x-api-key`.
- **Licencia**: **condiciones propias del editor** — no es CC BY.
- **Frecuencia**: apidatos, agregado **diario**; ESIOS, cuartos de hora.
- **Alimenta**: panel ⚡ (14 tecnologías del día) y previsión (indicadores **460** demanda y **541**
  eólica).
- **Limitaciones**: la API pública **solo sirve agregados diarios**. `time_trunc=hour` devuelve
  **400** en todos los widgets, `demanda-tiempo-real` también, y `geo_limit=ccaa` da **500**.
  **No hay generación por planta** ni **tensión de red**: los «niveles de tensión» de ESIOS son
  tarifarios (E0, E1, E2…), no medidas en kV.
- **Trampa del formato**: los valores **no** están en `data.attributes.values` — ese objeto solo trae
  título y `last-update`. Las series vienen en **`included[]`**, un objeto por tecnología.

## 6. Renfe

### 6a. Posiciones de trenes (GTFS-Realtime)
- **URL oficial**: `https://gtfsrt.renfe.com/vehicle_positions.pb` (también `trip_updates.pb` y `alerts.pb`)
- **Cómo se obtiene**: descarga directa, sin clave. Formato **Protocol Buffers**; se lee con
  `gtfs-realtime-bindings`.
- **Frecuencia**: continua (es una foto del momento).
- **Alimenta**: capa de trenes (**418** posiciones) y alertas (98).
- **Limitaciones**: **`route_id` viene vacío** — la ruta está en la etiqueta (`C1-23551` → `C1`). Las
  alertas traen `header_text` vacío aunque `description_text` sí.

### 6b. Estaciones de Cercanías
- **URL oficial**: <https://data.renfe.com> (CKAN abierto, sin clave)
- **Cómo se obtiene**: `https://data.renfe.com/api/3/action/package_show?id=estaciones-cercanias-<núcleo>`
  y el CSV de su recurso.
- **Alimenta**: **405 estaciones** en 11 núcleos (Madrid 93, Valencia 66, Bilbao 44…).
- **Limitaciones**: el separador del CSV cambia (`;` o `,`) y los ficheros llevan **BOM**
  (`utf-8-sig`); sin eso la primera columna se llama `\ufeffNombre`.

## 7. EMSC-CSEM — sismología europea

**Qué publica.** El catálogo sísmico europeo en tiempo casi real.

- **URL oficial**: <https://www.seismicportal.eu/fdsnws/event/1/query>
- **Cómo se obtiene**: `?format=json&minlatitude=27&maxlatitude=44.5&minlongitude=-19.5&maxlongitude=5&starttime=<fecha>`
- **Licencia**: abierta, con atribución.
- **Alimenta**: capa de terremotos (**80 sismos** en 7 días).
- **Limitaciones**: `profundidad = -1` significa **superficie o desconocida**, no un km por encima.

## 8. OpenStreetMap

**Qué publica.** Infraestructura mapeada por voluntarios: líneas eléctricas, gasoductos, ríos,
EDAR, ETAP, canales.

- **URL oficial**: <https://www.openstreetmap.org> · consultas por <https://overpass-api.de>
- **Cómo se obtiene**: Overpass API con `[out:json]` y `out geom`.
- **Licencia**: **ODbL 1.0 — comparte igual**. Todo producto derivado hereda ODbL y no se puede
  mezclar sin más con datos CC BY.
- **Alimenta**: líneas 400/220 kV, gasoductos, hidráulicas, EDAR (3.034), ETAP (1.551), trasvases,
  canales (10.777), ríos (260).
- **Limitaciones**: Overpass devuelve **502/504** con frecuencia y exige `User-Agent` (si no, **406**).
  El mapeo es desigual: el **Tajo-Segura solo está hasta Alarcón**; los trasvases son fragmentos con
  nombre, no trazados continuos.

## 9. Pendientes de clave

| Organismo | Qué falta | Estado |
|---|---|---|
| **AEMET** | avisos meteorológicos CAP | 404 en todos los endpoints sin token; alta gratuita |
| **ENTSO-E** | generación y previsión **por unidad** | 401 sin token |
| **NAP (MITMA)** | catálogo de 179 conjuntos de transporte | su gateway no acepta la clave por header |

## 10. Disponibles y no usadas todavía

| Organismo | Qué ofrece | Por qué interesa |
|---|---|---|
| **DGT** | aforos de tráfico (IMD), incidencias, obras | explica la demanda de combustible |
| **Puertos del Estado** | estadística mensual de tráfico portuario | cruce con bunkering |
| **GIE AGSI+** | almacenamiento de gas europeo por instalación | nivel de gas y precio |
| **OMIE** | mercado diario e intradiario | el precio como variable |
| **NASA FIRMS** | focos de calor por satélite | riesgo de incendio junto a líneas |
| **Eurostat** | balance energético completo | la base de Prometeo |
| **INE** | población, renta, hogares por sección censal | la demanda, al detalle |

---

## Cómo se verifica que una fuente sigue viva

`scripts/validar.py` comprueba que cada capa tiene recibo, que los conteos cuadran y que
`datos/fuentes.json` declara origen para las 46 entradas. Cuando una URL devuelve **200 con una
página de error** —el INE y el MITECO lo hacen—, la comprobación es por **título** de la página, no
por código HTTP. Un 200 no es una prueba.
