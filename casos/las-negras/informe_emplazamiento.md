# Emplazamiento candidato: Las Negras  (36.8767, -2.0153)
Radio de influencia: 25 km · generado 2026-11-20T10:38:24+00:00

## [OK     ] Desaladoras existentes
> Coordenada de precisión municipal en origen: la distancia es al núcleo, no a la planta.
```json
{
 "en_radio": [
  {
   "nombre": "Desaladora de Carboneras",
   "km": 17.1,
   "m3_dia": null,
   "hm3_anio": 44,
   "fase": "produccion",
   "en_servicio": null,
   "demarcacion": "Cuencas Mediterráneas Andaluzas",
   "geo_precision": "municipio",
   "id": "desaladoras:carboneras"
  }
 ],
 "mas_cercana": {
  "nombre": "Desaladora de Carboneras",
  "km": 17.1,
  "m3_dia": null,
  "hm3_anio": 44,
  "fase": "produccion",
  "en_servicio": null,
  "demarcacion": "Cuencas Mediterráneas Andaluzas",
  "geo_precision": "municipio",
  "id": "desaladoras:carboneras"
 },
 "total_espana": 28
}
```

## [OK     ] Demarcación hidrográfica
```json
{
 "nombre": "CUENCAS MEDITERRANEAS ANDALUZAS"
}
```

## [PARCIAL] Población (provincia)
> El Atlas no tiene población por municipio: solo provincia y comunidad.
```json
{
 "unidad": {
  "cod_ine": "04",
  "nombre": "Almería",
  "codigo": "04",
  "pais": "ES",
  "superficie_km2": 8756,
  "poblacion": 731792,
  "color": "#f59e0b",
  "tramo_poblacion": "media-alta",
  "densidad": 83.6,
  "color_densidad": "#3b82f6",
  "tramo_densidad": "alta"
 },
 "nivel": "provincia"
}
```

## [PARCIAL] Población (comunidad)
> El Atlas no tiene población por municipio: solo provincia y comunidad.
```json
{
 "unidad": {
  "cod_ine": "01",
  "nombre": "Andalucía",
  "codigo": "01",
  "pais": "ES",
  "superficie_km2": 87678,
  "poblacion": 8472407,
  "color": "#b45309",
  "tramo_poblacion": "alta",
  "densidad": 96.6,
  "color_densidad": "#3b82f6",
  "tramo_densidad": "alta",
  "paro_pct": 17.35,
  "color_paro": "#991b1b",
  "tramo_paro": "alto"
 },
 "nivel": "comunidad"
}
```

## [OK     ] Embalses de la demarcación (parte del Boletín Hidrológico)
```json
{
 "demarcacion": "CUENCAS MEDITERRANEAS ANDALUZAS",
 "n": 12,
 "los_5_mas_cercanos_de_espana": [
  {
   "nombre": "Embalse de Cuevas de Almanzora",
   "km": 51.3,
   "capacidad_hm3": 161.0,
   "agua_hm3": 15.0,
   "demarcacion": "Cuenca Mediterránea Andaluza"
  },
  {
   "nombre": "Embalse de Benínar",
   "km": 89.9,
   "capacidad_hm3": 63.0,
   "agua_hm3": 9.0,
   "demarcacion": "Cuenca Mediterránea Andaluza"
  },
  {
   "nombre": "Embalse de Puentes",
   "km": 97.0,
   "capacidad_hm3": 26.0,
   "agua_hm3": 12.0,
   "demarcacion": "Segura"
  },
  {
   "nombre": "Embalse de Valdeinfierno",
   "km": 103.4,
   "capacidad_hm3": 12.0,
   "agua_hm3": 0.0,
   "demarcacion": "Segura"
  },
  {
   "nombre": "Embalse de Negratín",
   "km": 112.6,
   "capacidad_hm3": 571.0,
   "agua_hm3": 328.0,
   "demarcacion": "Guadalquivir"
  }
 ],
 "capacidad_total_hm3": 1174.0,
 "agua_total_hm3": 729.0,
 "llenado_pct": 62.1,
 "los_5_mas_cercanos": [
  {
   "nombre": "Embalse de Cuevas de Almanzora",
   "km": 51.3,
   "capacidad_hm3": 161.0,
   "agua_hm3": 15.0,
   "demarcacion": "Cuenca Mediterránea Andaluza",
   "fecha": "2026-11-10"
  },
  {
   "nombre": "Embalse de Benínar",
   "km": 89.9,
   "capacidad_hm3": 63.0,
   "agua_hm3": 9.0,
   "demarcacion": "Cuenca Mediterránea Andaluza",
   "fecha": "2026-11-10"
  },
  {
   "nombre": "Embalse de Rules",
   "km": 131.2,
   "capacidad_hm3": 111.0,
   "agua_hm3": 90.0,
   "demarcacion": "Cuenca Mediterránea Andaluza",
   "fecha": "2026-11-10"
  },
  {
   "nombre": "Embalse de Béznar",
   "km": 135.6,
   "capacidad_hm3": 53.0,
   "agua_hm3": 35.0,
   "demarcacion": "Cuenca Mediterránea Andaluza",
   "fecha": "2026-11-10"
  },
  {
   "nombre": "Embalse de Viñuela, La",
   "km": 190.9,
   "capacidad_hm3": 165.0,
   "agua_hm3": 137.0,
   "demarcacion": "Cuenca Mediterránea Andaluza",
   "fecha": "2026-11-10"
  }
 ],
 "en_radio_km": []
}
```

## [PARCIAL] Ríos y cauces
> El GeoJSON NO trae valor de caudal: solo un punto de aforo. El caudal se pide a Open-Meteo Flood (GloFAS, modelado, malla ~5 km) y solo 7 días atrás + 2 de previsión.
```json
{
 "en_radio": [],
 "mas_cercano": {
  "nombre": "Río Andarax",
  "km": 36.5,
  "longitud_km": 65.1,
  "punto_aforo": [
   -2.726,
   37.0041
  ],
  "tiene_caudal_en_fichero": false
 }
}
```

## [PARCIAL] Caudal del punto de aforo más cercano (GloFAS, MODELADO)
> No hay serie histórica ni escenario a futuro: el proyecto necesita años, no 9 días.
```json
{
 "rio": "Río Andarax",
 "punto_aforo": [
  -2.726,
  37.0041
 ],
 "unidad": "m³/s",
 "serie": {
  "2026-11-13": 0.0,
  "2026-11-14": 0.0,
  "2026-11-15": 0.0,
  "2026-11-16": 0.0,
  "2026-11-17": 0.0,
  "2026-11-18": 0.0,
  "2026-11-19": 0.0,
  "2026-11-20": 0.0,
  "2026-11-21": 0.0
 },
 "horizonte_dias": 9,
 "ojo": "modelo de reanálisis/previsión, no aforo oficial; el horizonte es de 2 días"
}
```

## [OK     ] EDAR con agua regenerable (I-ReWater HUB)
```json
{
 "n_en_radio": 4,
 "total_espana": 2086,
 "muestra": [
  {
   "municipio": "SAN JOSE",
   "km": 14.3,
   "capacidad": 7000,
   "qentrada_he": "3600",
   "poblacion_servida": null,
   "volumen_reutilizable_m3": "383250.000",
   "demanda_potencial_riego": "199123.3535287246320000",
   "impacto": "Alto Impacto"
  },
  {
   "municipio": "CARBONERAS",
   "km": 15.2,
   "capacidad": 15600,
   "qentrada_he": "15600",
   "poblacion_servida": null,
   "volumen_reutilizable_m3": "854100.000",
   "demanda_potencial_riego": "1081705.98765827575360000",
   "impacto": "Impacto Nulo"
  },
  {
   "municipio": "SAN ISIDRO-CAMPOHERMOSO",
   "km": 16.7,
   "capacidad": 39867,
   "qentrada_he": "39867",
   "poblacion_servida": null,
   "volumen_reutilizable_m3": "2182718.250",
   "demanda_potencial_riego": "15831235.15998034092320000",
   "impacto": "Alto Impacto"
  },
  {
   "municipio": "CABO DE GATA",
   "km": 22.6,
   "capacidad": 6000,
   "qentrada_he": "4092",
   "poblacion_servida": null,
   "volumen_reutilizable_m3": "328500.000",
   "demanda_potencial_riego": "293201.35018287669360000",
   "impacto": "Impacto Nulo"
  }
 ]
}
```

## [OK     ] EDAR OSM en el radio
```json
{
 "n": 6,
 "ejemplos": [
  {
   "nombre": null,
   "km": 13.6
  },
  {
   "nombre": null,
   "km": 24.2
  },
  {
   "nombre": null,
   "km": 24.2
  },
  {
   "nombre": "Depuradora de Cabo de Gata",
   "km": 22.8
  },
  {
   "nombre": "EdarEl Viso",
   "km": 16.6
  }
 ],
 "total_espana": 3034
}
```

## [OK     ] ETAP OSM en el radio
```json
{
 "n": 1,
 "ejemplos": [
  {
   "nombre": null,
   "km": 17.5
  }
 ],
 "total_espana": 1551
}
```

## [OK     ] Canales/conducciones en el radio
```json
{
 "n": 2,
 "ejemplos": [
  {
   "nombre": "Acueducto del Arco",
   "km": 21.4
  },
  {
   "nombre": "Acueducto de Fernán Pérez",
   "km": 6.3
  }
 ],
 "total_espana": 10895
}
```

## [VACIO  ] Trasvases en el radio
```json
{
 "n": 0,
 "ejemplos": [],
 "total_espana": 8
}
```

## [OK     ] Generación eléctrica en el radio
```json
{
 "n": 4,
 "mw_total": 137.6,
 "muestra": [
  {
   "nombre": "FV PARCAS",
   "km": 8.3,
   "mw": 39.972,
   "tecnologia": "solar_pv"
  },
  {
   "nombre": "FV CADIMA",
   "km": 12.6,
   "mw": 39.972,
   "tecnologia": "solar_pv"
  },
  {
   "nombre": "CSF LUCAINENA",
   "km": 15.4,
   "mw": 36.2,
   "tecnologia": "solar_pv"
  },
  {
   "nombre": "ALMERIA II",
   "km": 21.1,
   "mw": 21.5,
   "tecnologia": "solar_pv"
  }
 ]
}
```

## [OK     ] Precio de la electricidad (OMIE, día del fichero)
```json
{
 "fecha": "2026-11-18",
 "eur_mwh_medio": 52.13,
 "min": 0.0,
 "max": 150.0,
 "n_cuartos": 96
}
```

## [OK     ] Avisos AEMET de la zona
```json
{
 "zona": {
  "zona": "Poniente y Almería Capital - Costa",
  "km_al_borde": 22.8,
  "nivel": "rojo",
  "fenomenos": "CO"
 }
}
```

## [OK     ] Sismicidad a menos de 150 km
```json
{
 "n": 25,
 "mayores": [
  {
   "magnitud": 3.1,
   "km": 134.0,
   "hora": "2026-11-11T06:50:43.74Z",
   "lugar": "SPAIN"
  },
  {
   "magnitud": 2.5,
   "km": 142.1,
   "hora": "2026-11-15T02:35:31.76Z",
   "lugar": "SPAIN"
  },
  {
   "magnitud": 2.5,
   "km": 42.2,
   "hora": "2026-11-10T23:48:32.28Z",
   "lugar": "SPAIN"
  },
  {
   "magnitud": 2.4,
   "km": 144.6,
   "hora": "2026-11-15T03:40:13.97Z",
   "lugar": "SPAIN"
  },
  {
   "magnitud": 2.2,
   "km": 135.1,
   "hora": "2026-11-10T10:31:05.06Z",
   "lugar": "STRAIT OF GIBRALTAR"
  }
 ]
}
```

## Qué falta (declarado, no inventado)

| dato | estado | por qué |
|---|---|---|
| población municipal del punto | pendiente | no hay capa de municipios (A2); hoy solo provincia y comunidad autónoma |
| serie histórica y tendencia de caudal | por_sondear | CEDEX · Anuario de aforos: descarga en bloque, sin endpoint de consulta |
| demanda agraria de la cuenca | vacio | el capturador de I-ReWater devolvió 0 teselas en regadío |
| masas de agua subterránea | por_sondear | IDE-MITECO (agua): sin sondeo del servicio de descarga |
| Red Natura 2000 y espacios protegidos | por_sondear | Banco de Datos de la Naturaleza: falta resolver la distribución |
| calidad y salinidad del agua | por_sondear | Náyade solo publica aguas de baño |
| batimetría y emisario de vertido | por_sondear | no existe capa abierta |
| Trasvases en el radio | vacio | la consulta no devolvió registros en el radio |

## Catálogo
```json
{
 "licencia_si": 69,
 "licencia_pendiente": 5,
 "caducados": 30,
 "oficiales": 62,
 "comunitarias": 12,
 "por_jerarquia": {
  "1": 44,
  "2": 18,
  "3": 12
 },
 "descargables_ligeros": 34,
 "kb_total": 66225.3
}
```

## Capas usadas y su procedencia
| capa | fuente | licencia | actualizado | descargado | features |
|---|---|---|---|---|---|
| aemet-zonas | AEMET | © AEMET, citar como autora | 20261118 | 2026-11-18T19:20:33 | 70 |
| agua-embalsada | MITECO | CC-BY-4.0 | 2026-11-10 | 2026-11-19 | 402 |
| canales | OpenStreetMap | ODbL 1.0 | 2026-11-19 | 2026-11-19 | 10777 |
| demarcaciones | MITECO | Reutilización con atribución (Ley 37/2007) | None | 2026-11-19 | 25 |
| desaladoras | MITECO | CC-BY-4.0 | 2026-08-31 | 2026-11-19 | 28 |
| edar | OpenStreetMap | ODbL 1.0 | 2026-11-19 | 2026-11-19 | 3034 |
| embalses | MITECO | CC-BY-4.0 | 2026-11-10 | 2026-11-19 | 402 |
| etap | OpenStreetMap | ODbL 1.0 | 2026-11-19 | 2026-11-19 | 1551 |
| ine-ccaa | INE · Eurostat GISCO | datos abiertos INE · Eurostat CC BY 4.0 | 2026-11-19 | 2026-11-19 | 19 |
| ine-provincias | INE · Eurostat GISCO | datos abiertos INE · Eurostat CC BY 4.0 | 2026-11-19 | 2026-11-19 | 52 |
| irewater-edar | I-ReWater HUB (Interreg) | CC BY 4.0 | 2026-11-19 | 2026-11-19 | 2086 |
| omie_precio | None | None | None | None | None |
| plantas | REE · Registro administrativo de instalaciones de producción | condiciones del editor | None | 2026-11-19 | 5797 |
| rios | OpenStreetMap | ODbL 1.0 | None | 2026-11-19 | 260 |
| sismos | EMSC-CSEM | abierta con atribución | 2026-11-09 | 2026-11-19 | 80 |
| trasvases | OpenStreetMap | ODbL 1.0 | 2026-11-19 | 2026-11-19 | 8 |