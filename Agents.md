# Agents.md — Harness de Agentes

**Proyecto:** Pipeline Medallón de Datos e IA (AniList → Bronze → Silver → Gold)
**Documento normativo de origen:** [documents/PRD.md](documents/PRD.md) (v2.4)
**Audiencia:** agentes de desarrollo de código que operan sobre este repositorio.

> Este archivo es el **contrato operativo** del agente: define cómo trabaja, con qué
> habilidades, bajo qué invariantes y con qué criterio de terminado.
> El **qué** se construye vive en el PRD; el **cómo se opera** vive aquí.
> Ante conflicto entre ambos, **manda el PRD** y el agente debe reportar la discrepancia
> en lugar de resolverla por su cuenta.

---

## 0. Estado actual del repositorio

```
arq_medallion/
├── Agents.md          ← este documento (harness)
├── documents/
│   └── PRD.md         ← requerimientos v2.4
└── skills/            ← vacío: pendiente de poblar (§4)
```

**Nada de código existe todavía.** Este documento no implementa nada: especifica el
harness y el catálogo de skills atómicas que deberán crearse. La implementación
arranca sólo tras la aprobación de Fase 0 y Fase 1 (§2).

---

## 1. Principios operativos (no negociables)

| # | Principio | Consecuencia práctica |
|---|---|---|
| P1 | **Una skill, una responsabilidad** | Si una skill necesita la conjunción "y" para describirse, se parte en dos. |
| P2 | **Trazabilidad a requerimiento** | Todo artefacto de código declara qué `REQ-*` satisface. Código sin REQ asociado se justifica explícitamente o no se escribe. |
| P3 | **Determinismo antes que conveniencia** | Cualquier transformación que alimente `content_hash` o embeddings debe ser reproducible bit a bit entre corridas. |
| P4 | **Fallar suave en ingesta, fallar duro en contrato** | Bronze nunca aborta la corrida por un lote (REQ-B3); Silver nunca deja pasar un registro que viola el contrato (REQ-S1/S2). |
| P5 | **No optimizar el ritmo de red** | Prohibido paralelizar peticiones a AniList (REQ-B5). El riesgo de baneo de IP supera cualquier ahorro de segundos. |
| P6 | **La evidencia se emite, no se afirma** | Toda propiedad declarada (idempotencia, recall, resiliencia) se demuestra con métricas impresas o pruebas ejecutadas, nunca con prosa. |
| P7 | **Verificar, no asumir, la matriz ARM64** | Toda dependencia se confirma con wheel `linux/arm64` publicada antes de fijarla en `requirements.txt`. |
| P8 | **No ampliar el alcance en silencio** | Si el agente detecta un hueco en el PRD, lo reporta y propone; no lo rellena con criterio propio sin dejar constancia. |

### 1.1. Invariantes prohibitivas (violarlas invalida la entrega)

- **INV-1 — Bronze es crudo.** Sólo se agregan `ingestion_timestamp`, `source`,
  `source_page`. Cero limpieza, casteo o normalización (REQ-B2).
- **INV-2 — El embedding es sólo `description`.** El título no se concatena, no se
  antepone, no participa del vector bajo ninguna forma (REQ-G1). Sí aparece en la
  salida de búsqueda (REQ-G3).
- **INV-3 — `id` de AniList es la única PK.** `idMal` es nullable y jamás se usa como
  llave de merge ni de join (REQ-S1).
- **INV-4 — `content_hash` excluye `ingestion_timestamp`.** Incluirlo rompe REQ-S4 de
  forma silenciosa (REQ-S3, paso 3).
- **INV-5 — Sin paralelismo contra AniList.** Una petición a la vez, pausa base ≥ 1 s
  (REQ-B5).
- **INV-6 — El mapeo posición→`id` viaja con el índice.** Un índice sin mapeo es un
  entregable inválido (REQ-G2).
- **INV-7 — Cuarentena es JSONL append.** No Parquet, no Delta, no esquema forzado
  (REQ-S2).
- **INV-8 — `errors` antes que `data`.** Un `200 OK` con `errors` no se reintenta y no
  se procesa (§3.0 del PRD, REQ-B3).
- **INV-9 — Los directorios de datos no se versionan.** `/bronze`, `/silver`, `/gold`
  van al `.gitignore` (§5 del PRD).

---

## 2. Protocolo de ejecución (mapa del §1 del PRD)

El agente avanza por fases. **No se salta ninguna y no se escribe código productivo
antes de la aprobación explícita del usuario al cierre de Fase 0 y Fase 1.**

### Fase 0 — Entendimiento Socrático
- **Entrada:** PRD.md + este harness.
- **Salida obligatoria:**
  1. Lista de preguntas de clarificación sobre ambigüedades reales (no retóricas).
  2. **Matriz de compatibilidad ARM64** con versión candidata y confirmación de wheel
     `linux/arm64` para: `polars`, `deltalake`, `pydantic`, `sentence-transformers`,
     `torch` (variante CPU), `faiss-cpu`, `hnswlib`. Para cada una sin wheel: sustituto
     propuesto. Nunca compilar desde fuente en silencio (§3 del PRD).
  3. Declaración de parámetros por defecto propuestos (`paginas=20`, `perPage=50`,
     `pausa_base=1s`, `umbral_remaining=10`, `min_desc_len=50`, `k` de búsqueda).
- **Gate:** el usuario aprueba. Sin aprobación, no hay Fase 1.
- **Skill de apoyo:** `arm64-dependency-audit`.

### Fase 1 — Plan de Acción (WBS)
- **Salida obligatoria:** desglose paso a paso de scripts, configuraciones y
  contenedores, en orden de construcción, cada ítem etiquetado con su `REQ-*` y con la
  skill que lo produce.
- **Gate:** el usuario aprueba el WBS.

### Fase 2 — Ejecución Iterativa
- Orden estricto: **Bronze → Silver → Gold → Reporte**.
- Una capa no se declara terminada hasta cumplir su *Definition of Done* (§5).
- Cada capa se compone invocando skills atómicas del catálogo (§4), no escribiendo
  lógica monolítica ad hoc.

### Fase 3 — Pruebas de Agente
- Por cada capa: autogenerar y **ejecutar** pruebas unitarias y de integración.
- Las 7 pruebas del §4 del PRD son el piso, no el techo.
- Resultados reales: si algo falla, se reporta con el output, no se maquilla.

---

## 3. Convención de skills

### 3.1. Ubicación y formato

Cada skill vive en su propio directorio bajo [skills/](skills/):

```
skills/<nombre-kebab-case>/
├── SKILL.md          ← contrato de la skill (obligatorio)
├── reference.md      ← detalle técnico extenso (opcional, sólo si SKILL.md > ~150 líneas)
└── scripts/          ← código reutilizable que la skill instala o invoca (opcional)
```

`SKILL.md` empieza con frontmatter YAML:

```yaml
---
name: <nombre-kebab-case>            # idéntico al nombre del directorio
description: <cuándo usarla, en una línea; empieza con "Usar cuando...">
---
```

### 3.2. Estructura obligatoria del cuerpo de `SKILL.md`

| Sección | Contenido |
|---|---|
| `## Responsabilidad` | Una frase. Si lleva "y", la skill no es atómica. |
| `## Requerimientos que satisface` | Lista de `REQ-*` del PRD. |
| `## Entradas` | Parámetros, tipos, valores por defecto, de dónde vienen. |
| `## Salidas` | Artefactos producidos, rutas, formatos, métricas emitidas. |
| `## Invariantes` | Qué `INV-*` de §1.1 debe hacer cumplir esta skill. |
| `## Procedimiento` | Pasos numerados, deterministas, sin ambigüedad. |
| `## Criterios de aceptación` | Condiciones verificables que prueban que la skill funcionó. |
| `## Errores y modos de fallo` | Qué hace ante cada fallo previsible; qué nunca hace. |

### 3.3. Reglas de diseño

- **Atomicidad:** una skill hace *una* cosa. Componer es responsabilidad del
  orquestador de capa, no de la skill.
- **Sin estado oculto:** toda dependencia entra por parámetro o por ruta declarada.
- **Idempotente por defecto:** ejecutar dos veces con la misma entrada produce el mismo
  resultado y no duplica efectos.
- **Fronteras explícitas:** cada `SKILL.md` declara qué está **fuera** de su alcance y
  a qué skill delegar en ese caso.
- **Sin acoplamiento cruzado:** una skill no importa código de otra; comparte datos vía
  artefactos en disco o valores de retorno.

---

## 4. Catálogo de skills atómicas (a construir en `skills/`)

Estado inicial: **todas pendientes**. Se crean en el orden de Fase 2.

### 4.0. Transversales (Fase 0 / 1)

| Skill | Responsabilidad | REQ |
|---|---|---|
| `arm64-dependency-audit` | Verificar que cada dependencia candidata publica wheel `linux/arm64` para la versión fijada y reportar sustitutos cuando no. | §3 Restricción ARM, §6 riesgo `deltalake` |
| `docker-arm64-scaffold` | Generar `Dockerfile` (base slim, torch CPU, capa dedicada de caché del modelo), `docker-compose.yml` con volúmenes locales y `requirements.txt` con versiones fijadas. | §5 Entregables, §6 riesgo imagen pesada |
| `repo-hygiene-scaffold` | Generar `.gitignore` (excluye `/bronze`, `/silver`, `/gold`, venv, `.env`, autogenerados) y el esqueleto de `README.md`. | §5 Entregables, INV-9 |

### 4.1. Bronze — Ingesta

| Skill | Responsabilidad | REQ |
|---|---|---|
| `anilist-graphql-client` | Ejecutar la query paginada contra `https://graphql.anilist.co` vía `POST`, con headers correctos, y validar `errors` **antes** de leer `data`. | §3.0, REQ-B1, INV-8 |
| `rate-limit-governor` | Regular el ritmo: pausa base ≥ 1 s, lectura de `X-RateLimit-Remaining` y frenado proactivo hasta `X-RateLimit-Reset` al cruzar el umbral. Prohíbe paralelismo. | REQ-B5, INV-5 |
| `http-retry-policy` | Clasificar la respuesta y decidir el reintento: `429`→`Retry-After`; `403` de indisponibilidad y `5xx`→backoff exponencial con jitter, máx. 4 intentos; `200`+`errors`→no reintentar. | REQ-B3 |
| `bronze-batch-writer` | Persistir cada lote como archivo independiente en `/bronze` con padding fijo (`anime_catalog_batch_0001.json`), agregando **sólo** `ingestion_timestamp`, `source`, `source_page`. | REQ-B2, REQ-B4, INV-1 |
| `bronze-resume-checkpoint` | Al iniciar, listar `/bronze`, determinar qué páginas ya tienen archivo válido y saltarlas; nunca reiniciar desde la página 1. | REQ-B6 |
| `failed-pages-ledger` | Registrar las páginas que fallan definitivamente y garantizar que el pipeline continúa con la siguiente. | REQ-B3 (no abortar) |

### 4.2. Silver — Calidad e Idempotencia

| Skill | Responsabilidad | REQ |
|---|---|---|
| `html-description-normalizer` | Limpiar `description` de forma **determinista**: strip de tags, decodificación de entidades, normalización de espacios. Documentar cada paso. | REQ-S5, P3 |
| `anime-data-contract` | Definir y aplicar el modelo Pydantic V2: `id` int requerido, `idMal` int\|None, `title.romaji` str no vacío, `description` str con longitud mínima post-limpieza. | REQ-S1, INV-3 |
| `quarantine-writer` | Escribir los registros rechazados a `/silver/quarantine` en JSONL append, con `motivo_rechazo` y el payload original íntegro. | REQ-S2, INV-7 |
| `content-hash-builder` | Calcular `content_hash` sobre las columnas de negocio, **excluyendo** `ingestion_timestamp`, de forma estable entre corridas. | REQ-S3 paso 3, INV-4 |
| `delta-merge-upsert` | Crear/abrir la Delta table `/silver/anime` con esquema derivado del contrato, deduplicar el lote por `id` en Polars y ejecutar el `MERGE` nativo con `whenMatchedUpdate` condicionado a hash distinto + `whenNotMatchedInsertAll`. | REQ-S3 |
| `silver-metrics-emitter` | Emitir las 6 métricas de REQ-S4 leyendo `num_target_rows_inserted` / `num_target_rows_updated` **directamente** del resultado de `merge().execute()`. | REQ-S4, P6 |

### 4.3. Gold — Modelado e IA

| Skill | Responsabilidad | REQ |
|---|---|---|
| `vector-engine-benchmark` | Evaluar ≥ 2 motores (FAISS, HNSWlib) contra el corpus real de Silver, reportando: tiempo de construcción, latencia p50/p95, Recall@k vs. fuerza bruta real, huella en disco, soporte arm64. Emitir la línea de justificación del motor elegido. | REQ-G0 |
| `description-embedder` | Generar embeddings con `all-MiniLM-L6-v2` a partir **exclusivamente** de `description`. Rechaza cualquier entrada que incluya el título. | REQ-G1, INV-2 |
| `vector-index-builder` | Construir/actualizar el índice en `/gold/index` y persistir el mapeo posición→`id` junto al índice. | REQ-G2, INV-6 |
| `gold-delta-indexer` | Comparar los `id` del mapeo contra los `id` de Silver y embeber **sólo el delta**; garantizar 0 embeddings nuevos y 0 crecimiento cuando Silver no cambió. | REQ-G4 |
| `semantic-search-api` | Exponer la función de búsqueda: recibe texto, devuelve `id`, `title.romaji` y score ordenados de mayor a menor. | REQ-G3 |

### 4.4. Pruebas y reporte (Fase 3 / §4 del PRD)

| Skill | Responsabilidad | Pruebas del PRD que cubre |
|---|---|---|
| `contract-test-kit` | Inyectar JSON malformado (`description` vacío, `id` ausente) y verificar enrutamiento a cuarentena con el `motivo_rechazo` correcto. | Prueba de Contrato |
| `idempotency-test-kit` | Doble corrida en Silver (`inserted=0`, `updated=0`, total sin cambio) y doble construcción en Gold (sin crecimiento de vectores). | Prueba de Idempotencia, Prueba de Idempotencia en Gold |
| `resilience-test-kit` | Simular `429` con `Retry-After`; simular `X-RateLimit-Remaining` bajo umbral y verificar frenado **anticipado**; extracción parcial 5/20 e interrupción, verificando reanudación sin re-descarga. | Prueba de Resiliencia, Prueba de Ritmo Proactivo, Prueba de Reanudación |
| `semantic-test-kit` | Verificar `k` resultados, `id` existentes en Silver, scores descendentes, top-1 sobre umbral configurable. **Prohibido** afirmar qué título sale primero. Verificar que el benchmark de REQ-G0 produce las 5 métricas y que el recall se calculó contra fuerza bruta real. | Prueba Semántica, Prueba Comparativa de Índices |
| `execution-report-renderer` | Imprimir el reporte final: tabla de conteos con los nombres exactos de REQ-S4 (una columna por corrida), tabla comparativa de motores con el elegido señalado, y top 3 de la búsqueda semántica. | §4 Reporte de Ejecución |

**Total: 22 skills.** Ninguna existe todavía.

---

## 5. Definition of Done por capa

Una capa se declara terminada sólo si **todas** sus condiciones son verificables por
ejecución, no por inspección de prosa.

### Bronze
- [ ] `paginas` es parámetro de entrada, no constante en código.
- [ ] Archivos con padding fijo, orden lexicográfico == orden numérico.
- [ ] Registros crudos e intactos; sólo los 3 campos de metadata agregados.
- [ ] Una segunda corrida no re-descarga páginas ya presentes.
- [ ] Una página que falla queda registrada y el pipeline continúa.
- [ ] Pausa observable ≥ 1 s entre peticiones; frenado anticipado demostrado en prueba.

### Silver
- [ ] Registros inválidos en `/silver/quarantine`, JSONL, con motivo y payload original.
- [ ] `/silver/anime` es una Delta table con esquema derivado del contrato.
- [ ] Segunda corrida del mismo lote: `num_target_rows_inserted = 0` **y**
      `num_target_rows_updated = 0` **y** `filas_totales_silver` sin cambio.
- [ ] Limpieza de `description` produce el mismo `content_hash` en corridas sucesivas.

### Gold
- [ ] Tabla comparativa de ≥ 2 motores con las 5 métricas, recall medido contra fuerza
      bruta real, motor elegido justificado en una línea.
- [ ] El script del motor descartado permanece en el repo como evidencia reproducible.
- [ ] Inspección de código confirma que el título no entra al embedding.
- [ ] `/gold/index` contiene índice **y** mapeo posición→`id`.
- [ ] Segunda construcción sin cambios en Silver: 0 embeddings nuevos, 0 crecimiento.

### Reporte y entrega
- [ ] Reporte con las 3 tablas del §4 del PRD, nombres de métrica exactos.
- [ ] `docker-compose.yml`, `Dockerfile` arm64, `requirements.txt` fijado.
- [ ] Suite de pruebas ejecutada, con resultados reales reportados.
- [ ] `.gitignore` excluye `/bronze`, `/silver`, `/gold`, venv, `.env`.
- [ ] `README.md` documenta arquitectura, levantado de contenedores, ejecución de
      pruebas y visualización del reporte.

---

## 6. Trampas conocidas (el agente debe evitarlas activamente)

Derivadas del §6 del PRD y del historial de cambios v1.0→v2.4. Son errores que ya se
cometieron o se anticiparon; repetirlos es un fallo del harness, no un descubrimiento.

| Trampa | Por qué es tentadora | Qué hacer |
|---|---|---|
| Concatenar `title + description` "para dar más contexto" | Parece mejorar la señal | Prohibido por INV-2. Verificable por inspección en Fase 3. |
| Incluir `ingestion_timestamp` en `content_hash` | Es una columna más del DataFrame | Excluirla (INV-4). Si no, toda fila parece modificada y REQ-S4 nunca pasa. |
| Recalcular `filas_nuevas`/`filas_actualizadas` a mano en Polars | Se siente más controlable | Leerlas del resultado de `merge().execute()` (REQ-S4). Recalcular duplica lógica y agrega bugs. |
| Paralelizar la extracción | Ahorra ~20 s | Prohibido (INV-5). El riesgo es baneo de IP, no un `429`. |
| Escribir cuarentena en Parquet | Consistencia con Silver | Prohibido (INV-7). El esquema de los rechazados es heterogéneo por definición. |
| Inferir el esquema de la Delta table desde una tabla vacía | Menos código | Derivarlo del contrato Pydantic (REQ-S3 paso 1). |
| Asumir que `deltalake`/`faiss-cpu` tienen wheel arm64 | Suelen tenerla | Verificar en Fase 0 contra la versión exacta (P7). |
| Afirmar en la Prueba Semántica qué título debe salir primero | Da una aserción "fuerte" | Prohibido: se rompe al cambiar el corpus y convierte la suite en ruido. |
| Elegir el motor vectorial "porque HNSW es más rápido" | Es cierto a otra escala | A ~1,000 vectores manda el recall exacto (REQ-G0, regla de decisión). |
| Abortar la corrida de Bronze ante un lote fallido | Parece más "correcto" | Prohibido (P4/REQ-B3): registrar y continuar. |
| Usar `idMal` como llave | Aparenta ser el ID canónico de anime | Es nullable. `id` de AniList es la única PK (INV-3). |
| Limpiar HTML en Bronze | El dato ya viene sucio | Bronze es crudo (INV-1). La limpieza es de Silver (REQ-S5). |

---

## 7. Protocolo de reporte del agente

Al cerrar cada fase, el agente entrega:

1. **Qué se construyó**, con la lista de `REQ-*` cubiertos y las skills invocadas.
2. **Evidencia ejecutada**: comandos corridos y su output real.
3. **Qué quedó fuera** y por qué — explícito, nunca omitido en silencio.
4. **Riesgos abiertos** detectados durante la implementación que el PRD no anticipa.

Si una prueba falla, se reporta con el output completo. Un entregable parcial declarado
como tal es aceptable; uno parcial declarado como completo, no.

---

## 8. Fuera de alcance de este documento

- La implementación de las 22 skills (§4): pendiente, arranca tras el gate de Fase 1.
- Cualquier código de las capas Bronze, Silver o Gold.
- La elección definitiva del motor vectorial: la decide el benchmark de REQ-G0 contra
  el corpus real, no este harness.
- Versiones concretas de dependencias: las fija la matriz ARM64 de Fase 0.
