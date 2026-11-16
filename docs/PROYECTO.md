---
titulo: OpenInfraES — qué es y qué contiene
fecha: 2026-11-16
ambito: espana
estado: publicado
---

# OpenInfraES — infraestructura de España, en un visor

Un mapa de la infraestructura energética y de transporte de España que se puede **usar**, no solo
mirar: cada capa declara su fuente, su licencia y la fecha del dato, y cada elemento abre una ficha
con todos sus atributos.

**Documentación**: [`BIBLIOTECA.md`](BIBLIOTECA.md) — para qué existe el proyecto · este documento (visión general) · [`FUENTES.md`](FUENTES.md) — ficha por fuente
oficial con licencia, frecuencia y limitaciones · [`apis.md`](apis.md) — estado técnico de cada API ·
[`nap.md`](nap.md) — el NAP de transporte · [`../GUIA.md`](../GUIA.md) — reglas de trabajo.

Corre en local (`python -m http.server`). **Todavía no está en un servidor**, y esa es una decisión
consciente: primero el dato y el motor, después el alojamiento.

## Qué contiene

**28 capas en 6 grupos.** Con las capas de por defecto, ~7.400 objetos.

### Red eléctrica
| Capa | Registros | Fuente | Licencia |
|---|---:|---|---|
| Líneas 400 kV | 1.752 | OSM | ODbL |
| Líneas 220 kV | 3.176 | OSM | ODbL |
| Subestaciones | 657 | Atlas (BTN del IGN) | CC BY 4.0 |
| Interconexiones | 5 | Atlas | CC BY 4.0 |

### Generación
Hidráulicas (1.387), nucleares (7 reactores), ciclos combinados, resto del parque. Con potencia
instalada por planta.

### Gas
Gasoductos (678 tramos), regasificadoras (7), almacenamiento subterráneo (5), refinerías (10).

### Agua
Embalses (402, con capacidad y agua embalsada del parte semanal), desaladoras (28), **EDAR (3.034)**,
**ETAP (1.551)**, **trasvases (11 trazos)**, canales y acequias (10.777), **ríos (260 con caudal en
vivo)**.

### Transporte
Carreteras del Estado (1.602), puertos (45), terminales portuarias (440), terminales de aeropuerto
(102), terminales de mercancías (383), estaciones con GNL/GNC/H₂ (165).

### Riesgo
| Capa | Qué da | Fuente |
|---|---|---|
| **Terremotos (7 días)** | 80 sismos con magnitud, profundidad y región; el tamaño del punto es la magnitud | EMSC-CSEM (sin clave) |

### Tiempo real
| Capa | Qué da | Fuente | Clave |
|---|---|---|---|
| Trenes | ~418 posiciones con hora y ruta | Renfe GTFS-RT | no |
| Estaciones Cercanías | 405 en 11 núcleos | data.renfe.com | no |
| **Carburantes** | **11.433 estaciones con precio del gasóleo A, GNC, GNL y H₂** | MITECO | no |
| ⚡ Generación del día | 14 tecnologías, 702.451 MWh | REE apidatos | no |
| ⚡ Previsión | demanda y eólica por cuartos de hora | ESIOS | sí |

## Cómo está hecho

```
datos/            GeoJSON servidos al visor (simplificados)
  simplificado/   geometrías reducidas (-84% de vértices)
  atlas/          capas del Atlas Estratégico
  hermes/         capas del visor del MITMA
scripts/          un script por fuente, cada uno con su recibo
mapa.html         el visor: Leaflet + canvas, un solo fichero
docs/             este documento, apis.md, nap.md
```

**Regla de oro: nada se escribe a mano.** Cada `datos/*.geojson` sale de un script que descarga,
normaliza y deja un `_recibo.json` con cuántos registros y de cuándo. El validador (`scripts/validar.py`)
falla si falta un recibo, si un conteo no cuadra o si una capa se queda sin fuente.

## Las tres decisiones que explican el resto

1. **Un dato, una capa.** Cuando dos fuentes solapan (presas de OSM contra embalses del Atlas,
   gasoductos contra conducciones), se elige la que responde al pinchar y se documenta por qué. No se
   pintan las dos.
2. **La fecha del dato no es la de descarga.** El panel ⓘ distingue tres fechas y tres eslabones:
   quién produce el dato, quién lo publica y cuándo lo bajamos. Un embalse es del parte del 10 de
   noviembre aunque lo descargues el 16.
3. **Lo que no está, se dice.** El Tajo-Segura de OSM solo llega a Alarcón; la ficha lo declara en vez
   de dibujar una línea que mient. Igual con el caudal de los ríos: es modelado, no aforo oficial.

## Rendimiento

| Medida | Valor |
|---|---|
| Vértices tras simplificar | 930.638 → 152.092 (**-84%**) |
| 4 zooms (8 capas) | 163-260 ms (antes 240-294) |
| Arrastre | al techo del refresco (75-144 fps según pantalla) |
| Arrastre **sin capas** | los mismos fps: el motor no es el cuello |

Palancas: simplificación Douglas-Peucker, agrupación por rejilla al alejar, LOD por zoom (las 3.176
líneas de 220 kV no se dibujan por debajo de z6,2), carga solo de lo que cae en la vista y descarga
bajo demanda.

## Límites conocidos

- **No hay generación por planta en la API pública de REE.** Solo agregado diario. Por unidad exige
  ENTSO-E (token gratuito).
- **No hay tensión de red por nudo** en ninguna API pública, ni con token.
- **El NAP de transporte no acepta su clave por header** (ver `docs/nap.md`).
- **AEMET requiere clave**; sin ella no hay alertas meteorológicas automatizables.
- **El Tajo-Segura está a medias** en OSM y no hay capa oficial abierta.

## Licencias

Conviven dos regímenes y **no se pueden mezclar sin cuidado**:

- **ODbL 1.0** (OpenStreetMap): casi toda la red eléctrica, gas, agua. Es **comparte igual**: un
  producto derivado hereda ODbL.
- **CC BY 4.0** (Atlas, MITMA, MITECO): atribución, sin copyleft.
- **Condiciones propias** (REE REData, OMIE): pendiente de leer.

## De dónde sale cada dato

Las 46 entradas de `datos/fuentes.json` declaran **productor → publica → descarga** y tres fechas
distintas. El detalle, fuente por fuente, está en [`FUENTES.md`](FUENTES.md). Resumen:

| Organismo | Qué aporta | Licencia |
|---|---|---|
| **IGN / SCNE** | cartografía base, BTN, subestaciones | CC BY 4.0 |
| **MITECO** | embalses, desaladoras, precios de carburantes | Ley 37/2007 |
| **MITMA** | carreteras, puertos, terminales, combustibles alternativos | CC BY 4.0 |
| **REE / ESIOS** | generación, demanda, balance, previsión | condiciones propias |
| **Renfe** | trenes en vivo, estaciones de Cercanías | abierto |
| **EMSC-CSEM** | terremotos | abierto con atribución |
| **OpenStreetMap** | red eléctrica, gas, EDAR, ETAP, ríos | **ODbL** |

## Cómo se arranca

```bash
cd OpenInfraES
python -m http.server 8731 --bind 127.0.0.1
# http://127.0.0.1:8731/mapa.html
```

Credenciales en `.env` (ignorado por git). Para actualizar los datos, un script por fuente y
`python scripts/validar.py` antes de dar nada por bueno.
