---
titulo: Emplazamiento — el contexto de un punto y lo que falta
fecha: 2026-11-20
---

# Emplazamiento

El visor responde «qué hay en el mapa». Un expediente pregunta otra cosa: **dado un punto y un
radio, qué se sabe y qué falta**. Eso lo contesta `scripts/probador_emplazamiento.py`, que lee
`datos/` en solo lectura y escribe un informe con su procedencia.

```bash
python scripts/probador_emplazamiento.py --lat 37.4067 --lon -1.5822 \
    --nombre Aguilas --radio 25 --out casos/aguilas
```

Salida: `casos/<slug>/informe_emplazamiento.json` + `.md`. Hay dos casos de control versionados:
`casos/aguilas` y `casos/las-negras`.

## Qué devuelve, y con qué estado

Cada bloque sale con **ok · parcial · vacio · por_son dear**. Un dato que falta **no se pinta como
cero**: va a `huecos[]` con el motivo.

| Bloque | Fuente | Estado |
|---|---|---|
| Desaladoras en el radio, con capacidad | MITECO | ok |
| Demarcación hidrográfica del punto | MITECO | ok |
| Embalses de la cuenca y parte semanal | MITECO · Boletín Hidrológico | ok |
| EDAR con agua regenerable | I-ReWater HUB | ok |
| Generación cercana y precio OMIE | REE · OMIE | ok |
| Avisos AEMET y sismicidad | AEMET · EMSC-CSEM | ok |
| **Población municipal del punto** | INE · Padrón | pendiente: hay provincia/comunidad, no municipio |
| **Caudal de río** | Open-Meteo Flood (GloFAS) | parcial: **modelado**, rejilla ~5 km, no es aforo |
| **Serie y tendencia de caudal** | CEDEX · Anuario de aforos | por sondear |
| **Demanda agraria** | I-ReWater (regadío) | vacío: el capturador devolvió 0 teselas |
| **Masas subterráneas, Red Natura, calidad, batimetría** | MITECO · BDN · Náyade | por sondear |

## Reglas del informe

- Todo dato lleva **organismo, fecha del dato y licencia** (tabla «Capas usadas» al final).
- **GloFAS se cita como modelado**, nunca como caudal medido: un expediente no se justifica con una
  rejilla de 5 km.
- El agua embalsada de la cuenca **no** justifica el río que se capta ni el acuífero que se protege.
- Los agregados se declaran con su camino de cálculo, para poder contrastarlos con el organismo.

## Lo que este informe no es

No es una autorización ni un estudio de impacto ambiental. Es el **contexto del dato abierto** y la
lista explícita de lo que no hay. Cerrar los huecos es trabajo de capturador, no de redacción.
