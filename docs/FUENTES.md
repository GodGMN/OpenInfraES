---
titulo: Fuentes oficiales — ficha por ficha
fecha: 2026-11-16
ambito: espana
estado: publicado
---

# Fuentes oficiales de OpenInfraES

Cada capa sale de un organismo público. Aquí está, para cada uno: **qué publica**, la **URL oficial**,
**cómo se obtiene** el dato, la **licencia**, la **frecuencia**, **qué capas alimenta** y sus
**limitaciones**.

Solo se cita al organismo que produce el dato.

---

## 1. IGN — Instituto Geográfico Nacional (SCNE)

**Qué publica.** La Base Topográfica Nacional (BTN) y la cartografía base de España. Es la fuente de
la red eléctrica, los recintos de subestación y las teselas del mapa.

- **URL oficial**: <https://www.ign.es> · <https://www.scne.es>
- **Cómo se obtiene**:
  - Teselas del mapa: `https://www.ign.es/wmts/ign-base?request=GetTile&service=WMTS&version=1.0.0&layer=IGNBase-gris&style=default&tilematrixset=GoogleMapsCompatible&tilematrix={z}&tilerow={y}&tilecol={x}&format=image/png`
  - Vectorial (BTN): capas en GeoJSON ya vectorizadas, en `datos/oficial/`.
- **Licencia**: CC BY 4.0 · atribución `© scne.es`.
- **Frecuencia**: continua (BTN Continua).
- **Alimenta**: fondo del mapa (4 bases) y **subestaciones (657)**, red de 220/400 kV.
- **Limitaciones**: el WMTS devuelve **200 con cuerpo vacío** sin `Accept: image/*` y `Referer`. No
  tiene teselas oscuras: el tema oscuro se hace con filtro CSS sobre la capa de solo líneas. Las capas
  vectoriales **mezclan geometrías**: la de red eléctrica son 657 polígonos de subestación **y** 2
  tendidos; hay que mirar la propiedad `categoria`, no el tipo de la primera feature.

## 2. MITECO — Ministerio para la Transición Ecológica

Tres conjuntos distintos, los tres oficiales:

### 2a. Boletín Hidrológico — el dato primario de los embalses
- **URL oficial**: <https://www.miteco.gob.es/es/agua.html>
- **Cómo se obtiene**: parte **semanal**; el volumen de cada embalse llega en el campo
  `agua_actual_hm3` con su propia fecha en `fecha_dato`.
- **Licencia**: reutilización con atribución (Ley 37/2007).
- **Alimenta**: **402 embalses** con capacidad y agua embalsada.
- **Limitaciones**: cubre embalses peninsulares de más de 5 hm³.

### 2b. Precios de carburantes — tiempo real
- **URL oficial**: `https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/`
- **Cómo se obtiene**: `GET` a esa URL → ~12 MB de JSON con **11.528 estaciones**. `scripts/carburantes.py`
  lo reduce a 11.433 con precio válido.
- **Licencia**: Ley 37/2007.
- **Frecuencia**: **cada 30 minutos**.
- **Alimenta**: carburantes con gasóleo A, gasolina 95/98, GNC, GNL y H₂.
- **Limitaciones**: el servidor **corta el handshake TLS con Python** (`SSLEOFError`) → descargar con
  `curl`. Números con **coma decimal** (`39,211417`) y claves con espacios y tildes.

### 2c. Desaladoras, presas e hidrógeno
- **Cómo se obtiene**: desaladoras (28) e instalaciones de hidrógeno en GeoJSON; el inventario de
  presas (≈3.200) **no publica geometría**, solo listados.

## 3. MITMA — Ministerio de Transportes (visor Hermes)

- **URL oficial**: <https://mapas.fomento.gob.es/VisorHermes/>
- **Cómo se obtiene** (ArcGIS REST abierto, sin clave):
  `https://mapas.fomento.gob.es/arcgis/rest/services/Hermes/<servicio>/MapServer/<capa>/query?where=1=1&outFields=*&returnGeometry=true&outSR=4326&f=geojson`
- **Licencia**: CC BY 4.0 (scne.es).
- **Alimenta**: carreteras (1.602), puertos (45), terminales portuarias (440), terminales de aeropuerto
  (102), terminales de mercancías (383), estaciones GNL/GNC/H₂ (165 de 11.485).
- **Limitaciones**: `resultRecordCount=1000` **falla** → paginar de 500 en 500. Carreteras sin
  simplificar son ~85 MB → `maxAllowableOffset=0.002` la deja en 0,63 MB. La capa 0 de aeropuertos no
  admite query.

## 4. REE — Red Eléctrica de España

- **URL oficial**: <https://www.ree.es/es/apidatos> (sin clave) · <https://api.esios.ree.es> (con clave)
- **Cómo se obtiene**:
  - `https://apidatos.ree.es/es/datos/generacion/estructura-generacion?start_date=...&end_date=...&time_trunc=day`
  - Con clave: `https://api.esios.ree.es/indicators/<id>` + cabecera `x-api-key`.
- **Licencia**: **condiciones propias del editor**.
- **Frecuencia**: apidatos, **diaria**; ESIOS, cuartos de hora.
- **Alimenta**: panel ⚡ (14 tecnologías) e interconexiones (5); previsión por ESIOS (460 demanda,
  541 eólica).
- **Limitaciones**: la API pública **solo sirve agregados diarios** (`time_trunc=hour` → 400). **No hay
  generación por planta** ni **tensión de red**: los «niveles de tensión» de ESIOS son tarifarios.
- **Trampa**: las series están en **`included[]`**, no en `data.attributes.values`.

## 5. CSN, CORES y Enagás

- **CSN** (<https://www.csn.es>): **7 reactores** con potencia y tecnología.
- **CORES** (<https://www.cores.es>): refinerías (10) y almacenamiento de productos petrolíferos.
- **Enagás** (<https://www.enagas.es>): regasificadoras (7), almacenamiento subterráneo (5) e
  interconexiones de gas.
- **Licencia**: CC BY 4.0 en las capas vectorizadas.

## 6. Renfe

### 6a. Posiciones de trenes (GTFS-Realtime)
- **URL oficial**: `https://gtfsrt.renfe.com/vehicle_positions.pb` (y `trip_updates.pb`, `alerts.pb`)
- **Cómo se obtiene**: descarga directa, sin clave. Protocol Buffers con `gtfs-realtime-bindings`.
- **Alimenta**: **418 trenes** y 98 alertas.
- **Limitaciones**: **`route_id` viene vacío** (la ruta va en la etiqueta, `C1-23551` → `C1`); las
  alertas traen `header_text` vacío aunque la descripción sí.

### 6b. Estaciones de Cercanías
- **URL oficial**: <https://data.renfe.com> (CKAN abierto)
- **Cómo se obtiene**: `api/3/action/package_show?id=estaciones-cercanias-<núcleo>` + su CSV.
- **Alimenta**: **405 estaciones** en 11 núcleos.
- **Limitaciones**: separador `;` o `,` según fichero; llevan **BOM** (`utf-8-sig`).

## 7. EMSC-CSEM — sismología europea

- **URL oficial**: <https://www.seismicportal.eu/fdsnws/event/1/query>
- **Cómo se obtiene**: `?format=json&minlatitude=27&maxlatitude=44.5&minlongitude=-19.5&maxlongitude=5&starttime=<fecha>`
- **Alimenta**: **80 sismos** en 7 días.
- **Limitaciones**: `profundidad = -1` significa **superficie o desconocida**.

## 8. OpenStreetMap

- **URL oficial**: <https://www.openstreetmap.org> · consultas por <https://overpass-api.de>
- **Cómo se obtiene**: Overpass API con `[out:json]` y `out geom`.
- **Licencia**: **ODbL 1.0 — comparte igual**.
- **Alimenta**: líneas 400/220 kV, gasoductos, hidráulicas, EDAR (3.034), ETAP (1.551), trasvases,
  canales (10.777), ríos (260).
- **Limitaciones**: Overpass da **502/504** a menudo y exige `User-Agent` (si no, **406**). El mapeo es
  desigual: el **Tajo-Segura solo llega a Alarcón**; los trasvases son fragmentos con nombre.

## 9. Pendientes de clave

| Organismo | Qué falta | Estado |
|---|---|---|
| **AEMET** | avisos meteorológicos CAP | 404 sin token; alta gratuita |
| **ENTSO-E** | generación y previsión **por unidad** | 401 sin token; **cuenta ya creada** |
| **NAP (MITMA)** | 179 conjuntos de transporte | su gateway no acepta la clave por header |

## 10. Disponibles y no usados todavía

| Organismo | Qué ofrece | Por qué interesa |
|---|---|---|
| **DGT** | aforos de tráfico (IMD), incidencias, obras | explica la demanda de combustible |
| **Puertos del Estado** | estadística mensual de tráfico portuario | cruce con bunkering |
| **GIE AGSI+** | almacenamiento de gas europeo por instalación | nivel de gas y precio |
| **OMIE** | mercado diario e intradiario | el precio como variable |
| **NASA FIRMS** | focos de calor por satélite | riesgo de incendio junto a líneas |
| **Eurostat** | balance energético completo | la base de Prometeo |
| **INE** | población, renta y hogares por sección censal | la demanda, al detalle |
