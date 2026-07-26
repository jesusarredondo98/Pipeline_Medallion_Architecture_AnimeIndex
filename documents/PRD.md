# Product Requirements Document (PRD) — v2.4
 
**Proyecto:** Pipeline Medallón de Datos e IA (Entorno Contenerizado)
**Fuente de datos:** AniList GraphQL API
**Motor de procesamiento:** Polars (cómputo) + delta-rs (formato transaccional de Silver)
**Audiencia Objetivo:** Agentes de Desarrollo de Código (AI Agents)
 
---
 
## 0. Changelog v1.0 → v2.0 (leer primero)
 
| Cambio | v1.0 (Jikan) | v2.0 (AniList) | Motivo |
|---|---|---|---|
| Fuente | Jikan REST v4 | AniList GraphQL | Jikan hace scraping de MyAnimeList; devuelve `504 BadResponseException` de forma intermitente en cualquier petición que no esté en su caché. Toda petición paginada (`?page=N`) resultó en cache miss → 504. Verificado empíricamente. |
| Protocolo | GET + query params | POST + cuerpo GraphQL | AniList es GraphQL. Requiere `Content-Type: application/json`. |
| **User-Agent** | "CRÍTICO: disfrazarse con User-Agent de navegador para evitar el 504" | **Requerimiento eliminado** | **Premisa falsa.** El 504 nunca fue una protección anti-bot contra el cliente. El fallo ocurría en el salto Jikan→MyAnimeList, del lado del servidor, fuera del alcance de cualquier header del cliente. Un User-Agent descriptivo y honesto es buena práctica; disfrazarse de Chrome no aporta nada. |
| PK | `mal_id` | `id` (AniList), con `idMal` como identificador secundario nullable | AniList tiene su propio espacio de IDs. `idMal` puede venir `null` en títulos no mapeados a MAL. |
| Campo de texto para IA | `synopsis` | `description` | Nombre del campo en el esquema de AniList. |
| Tabla Silver | `/silver/episodes` | `/silver/anime` | Se ingiere el catálogo de animes, no episodios. El nombre anterior era engañoso. |
| Autenticación | No requerida | No requerida para datos públicos | Sin cambio. |
 
### Changelog v2.0 → v2.1
 
| Cambio | v2.0 | v2.1 | Motivo |
|---|---|---|---|
| Motor de procesamiento | delta-rs (o Polars) | **Polars** (único) | Decisión del usuario. Elimina la ambigüedad del "o". |
| Mecanismo de upsert | `MERGE` de delta-rs | Anti-join en Polars + escritura atómica (REQ-S3 reescrito) | **Consecuencia obligada del cambio anterior.** Polars es una librería de DataFrames, no un formato de tabla transaccional: no tiene `MERGE` ni ACID. El upsert ahora se especifica como algoritmo explícito. |
| Métrica de idempotencia | `num_inserted_rows` (nativo de delta-rs) | `filas_nuevas` / `filas_actualizadas` (calculadas por el script) | Ese contador nativo deja de existir sin delta-rs. La evidencia de REQ-S4 ahora la produce el pipeline. |
| Alcance del embedding | Implícito | Explícito: **solo `description`**. El título es metadato de salida, nunca entra al vector. | Evitar que un agente concatene título + descripción "para mejorar el contexto" y contamine el espacio semántico. |
| Idempotencia en Gold | No especificada | REQ-G4 (nuevo) | Hueco detectado en la revisión: Silver era idempotente pero el índice vectorial podía crecer con duplicados en cada corrida. |
| Elección de motor vectorial | "FAISS (o HNSWlib)" — ambigüedad sin resolver, mismo patrón que "delta-rs (o Polars)" en v2.0 | REQ-G0 (nuevo): evaluación comparativa obligatoria contra el corpus real, con criterio de decisión explícito (recall exacto pesa más que latencia a este tamaño de corpus) | El PRD no puede dejarle al agente una decisión de arquitectura sin criterio — es la misma clase de hueco que ya se corrigió una vez en esta ronda de revisiones. |
 
### Changelog v2.2 → v2.3
 
| Cambio | v2.2 | v2.3 | Motivo |
|---|---|---|---|
| Volumen de extracción | "Al menos dos páginas" (100 registros) | 20 páginas por defecto (1,000 registros), configurable hasta el catálogo completo | Decisión del usuario. Un corpus de 100 registros era demasiado chico para que la comparativa de índices (REQ-G0) o la búsqueda semántica dijeran algo interesante. |
| Ritmo de extracción | Solo reactivo: esperar `Retry-After` tras un `429` | REQ-B5 (nuevo): pausa base + monitoreo proactivo de `X-RateLimit-Remaining`, frenando **antes** de tocar el límite | Verificado el límite real de AniList: 90 req/min más un burst limiter no documentado y riesgo de baneo de IP. Con 20+ páginas, depender solo del 429 significa dispararlo de forma predecible en cada corrida — ya no es una excepción, es el camino normal. |
| Resiliencia ante interrupciones | No especificada | REQ-B6 (nuevo): checkpointing por archivo existente en `/bronze` | Consecuencia directa de extraer más páginas: la ingesta deja de ser instantánea y se vuelve razonable que se interrumpa a mitad de camino. Sin reanudación, cada interrupción fuerza un re-scrape completo — lo cual además agrava el riesgo de rate limit del punto anterior. |
| Supuesto de "corpus chico" en REQ-G0 | Tiempo de construcción "probablemente no discrimine"; recall exacto justificado por volumen pequeño | Reformulado para ~1,000 registros: fuerza bruta sigue siendo barata a este volumen, pero ya no se asume que el tiempo de construcción sea indiferente | El criterio de decisión no cambió (exactitud > latencia), pero la justificación textual databa de un corpus 10× más chico y ya no era honesta. |
 
### Changelog v2.3 → v2.4
 
| Cambio | v2.3 | v2.4 | Motivo |
|---|---|---|---|
| Formato de Silver | Parquet + upsert manual en Polars (anti-join + comparación por hash + `os.replace`) | **Delta Lake, vía `deltalake`/`pl.write_delta`, con `MERGE` nativo** | Decisión del usuario: reincorporar delta-rs. Polars sigue siendo el motor de cómputo — delta-rs entra únicamente como formato de almacenamiento transaccional de Silver. No es un regreso a la ambigüedad "delta-rs o Polars" de la v1.0: ahora conviven con roles distintos. |
| Algoritmo de upsert | 6 pasos manuales especificados en el PRD porque Polars no tenía `MERGE` | 4 pasos, delegando el merge en sí a delta-rs | El PRD ya no necesita normar un algoritmo que la librería ejecuta de forma nativa. |
| Métricas de idempotencia | `filas_nuevas` / `filas_actualizadas` calculadas a mano en Polars | `num_target_rows_inserted` / `num_target_rows_updated`, leídas directamente del resultado de `merge().execute()` | Delta ya las calcula de forma confiable; recalcularlas a mano era lógica duplicada y una fuente extra de bugs. |
| Escritura atómica | Manual: archivo temporal + `os.replace` | Automática: log de transacciones de Delta | Era precisamente la pieza que delta-rs resolvía y que se había tenido que reconstruir a mano al quitarlo en v2.1. |
| Riesgo "sin transaccionalidad" | Abierto, con mitigación parcial (solo cubría el caso mono-proceso) | Cerrado | Consecuencia directa de recuperar delta-rs. |
 
---
 
## 1. Protocolo de Ejecución para Agentes (Obligatorio)
 
Antes de generar cualquier artefacto de código, el agente debe seguir estrictamente este flujo:
 
- **Fase 0 — Entendimiento Socrático:** Analizar este PRD y formular preguntas de clarificación sobre cualquier ambigüedad en requerimientos, dependencias o versiones. No se debe escribir código hasta que el usuario apruebe el nivel de entendimiento.
- **Fase 1 — Plan de Acción:** Presentar un desglose técnico paso a paso (WBS) especificando qué scripts, configuraciones y contenedores se van a crear y en qué orden.
- **Fase 2 — Ejecución Iterativa:** Desarrollo por capas (Bronze → Silver → Gold → Reporte).
- **Fase 3 — Pruebas de Agente:** Por cada capa desarrollada, autogenerar y ejecutar pruebas unitarias y de integración.
---
 
## 2. Objetivo del Producto
 
Implementar una arquitectura de datos medallón de punta a punta ejecutada en contenedores (Docker), procesando el catálogo general de animes desde la API pública de AniList hasta llegar a una capa de búsqueda semántica.
 
El flujo debe garantizar **idempotencia**, **control de calidad** y **visibilidad de los resultados**, dejando el repositorio listo para ser publicado en GitHub.
 
---
 
## 3. Especificaciones Técnicas y Arquitectura
 
- **Entorno:** Local (Mac M2, arquitectura ARM64). Todo orquestado mediante `docker-compose.yml`.
- **Stack:** Python, Pydantic V2, **Polars** (motor de cómputo), **delta-rs** (formato transaccional de Silver, vía `deltalake` / `pl.write_delta`), sentence-transformers (`all-MiniLM-L6-v2`), motor de índice vectorial a determinar por evaluación comparativa (ver REQ-G0; candidatos: FAISS, HNSWlib).
- **Formato de persistencia:** **Delta Lake para `/silver/anime`** (transaccional, con `MERGE` nativo y log de versiones). Bronze permanece en JSON crudo (REQ-B2); la cuarentena de Silver permanece en JSONL (REQ-S2) — ninguno de los dos necesita transaccionalidad. Gold usa el formato propio del motor de índice elegido en REQ-G0.
- **Restricción ARM:** todas las dependencias deben resolver a wheels `linux/arm64`. Si alguna no lo hace, el agente debe reportarlo en Fase 0 y proponer sustituto — no compilar desde fuente en silencio. `deltalake` (bindings de Rust) publica wheels arm64; verificar en Fase 0 contra la versión fijada en `requirements.txt`, no asumir.
### 3.0. Contrato de la fuente (AniList)
 
| Aspecto | Especificación |
|---|---|
| Endpoint | `https://graphql.anilist.co` |
| Método | `POST` |
| Headers | `Content-Type: application/json`, `Accept: application/json`, `User-Agent` descriptivo del proyecto |
| Autenticación | Ninguna para datos públicos |
| Paginación | `Page(page: Int, perPage: Int)`; `perPage` máximo = **50** |
| Fin de paginación | `pageInfo.hasNextPage == false` |
| Rate limit | **90 requests/minuto**, más un burst limiter no documentado que penaliza ráfagas cortas incluso por debajo del límite por minuto. Headers en cada respuesta: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` (timestamp Unix). En `429`: header `Retry-After` (segundos). El cliente **debe** respetar `Retry-After` y **además** monitorear `X-RateLimit-Remaining` de forma proactiva — ver REQ-B5. |
| Disponibilidad | AniList puede devolver `403` con `"The AniList API has been temporarily disabled due to severe stability issues"` durante incidentes propios. No es un error del cliente: no reintentar agresivamente: aplicar el mismo backoff que a un `5xx`. |
| Riesgo de baneo de IP | Un volumen alto de peticiones sostenidas puede resultar en bloqueo manual de IP por parte de AniList, ajeno al mecanismo de `429`/`Retry-After`. Motivo directo para no maximizar el ritmo de extracción solo porque el límite nominal lo permite — ver REQ-B5. |
| Errores de negocio | Un `200 OK` puede contener `{"errors": [...]}`. Validar la presencia de `errors` **antes** de leer `data`. |
 
**Query de referencia:**
 
```graphql
query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo { currentPage lastPage hasNextPage total perPage }
    media(type: ANIME, sort: ID) {
      id
      idMal
      title { romaji english native }
      format
      status
      episodes
      duration
      season
      seasonYear
      averageScore
      popularity
      favourites
      genres
      studios { nodes { name } }
      startDate { year month day }
      endDate { year month day }
      description(asHtml: false)
    }
  }
}
```
 
> **Nota para el agente:** `sort: ID` garantiza orden determinista entre corridas, condición necesaria para las pruebas de idempotencia. `description(asHtml: false)` reduce el marcado pero **no lo elimina del todo** — pueden persistir `<br>`, `<i>` y entidades HTML. La limpieza es responsabilidad de la capa Silver, no de Bronze.
 
---
 
## 3.1. Requerimientos Funcionales por Capa
 
### Capa Bronze (Ingesta)
 
- **REQ-B1:** Extraer el catálogo de animes desde AniList (`Page.media`, `type: ANIME`) en un rango de páginas **configurable**, con **20 páginas (1,000 registros) como valor por defecto** — suficiente para que la evaluación de índices de REQ-G0 y la búsqueda semántica de REQ-G3 trabajen sobre un corpus representativo, no un puñado de registros. Cada lote se persiste como un archivo independiente. El número de páginas es un parámetro de entrada del script, no un valor hardcodeado — permite escalar hasta el catálogo completo (~20,000+ entradas, ver `docs.anilist.co`) sin tocar código.
- **REQ-B2:** Persistir los JSON en un volumen local `/bronze`. Se debe agregar **únicamente** metadata de ingesta al lote (`ingestion_timestamp`, `source`, `source_page`), manteniendo la estructura de los registros cruda e intacta. Ninguna limpieza, casteo ni normalización ocurre en Bronze.
- **REQ-B3 (nuevo):** Manejo de fallos resiliente y no destructivo:
  - `429` → esperar el valor de `Retry-After` y reintentar.
  - `403` de disponibilidad (API deshabilitada temporalmente) → tratar como `5xx`, backoff exponencial, **no** insistir de inmediato.
  - `5xx` o error de red → backoff exponencial con jitter, máximo 4 intentos.
  - `200` con `errors` en el cuerpo → registrar y **no** reintentar (es un error de query, no transitorio).
  - Una página que falla definitivamente se registra en una lista de páginas fallidas y **el pipeline continúa con la siguiente**. Nunca abortar la corrida completa por un lote.
- **REQ-B4 (nuevo):** Nomenclatura de archivos con padding fijo (`anime_catalog_batch_0001.json`) para que el orden lexicográfico coincida con el orden numérico.
- **REQ-B5 (nuevo):** Ritmo de extracción proactivo, no solo reactivo al `429`. Depender únicamente de `Retry-After` significa que ya se disparó el límite antes de frenar — con 20+ páginas eso ocurre de forma predecible, no como excepción.
  - **Pausa base:** mínimo 1 segundo entre peticiones (≤ 60 req/min), dejando margen bajo el techo de 90 req/min para absorber el burst limiter no documentado.
  - **Frenado dinámico:** leer `X-RateLimit-Remaining` en cada respuesta. Si `Remaining` cae por debajo de un umbral (sugerido: 10), aumentar la pausa hasta el `X-RateLimit-Reset` reportado, **antes** de que ocurra el 429 — no después.
  - **Prohibido:** paralelizar peticiones a AniList para "ir más rápido". El riesgo de baneo de IP (ver §3.0) hace que maximizar el ritmo sea una optimización que no vale la pena para este volumen de datos.
- **REQ-B6 (nuevo):** Reanudación (checkpointing). Con 20+ páginas la extracción deja de ser instantánea y se vuelve susceptible a interrupciones a mitad de camino (corte de red, cierre del notebook, `Ctrl+C`). El script debe, al iniciar, inspeccionar `/bronze` y saltar las páginas cuyo archivo ya existe y es válido — **no** reiniciar desde la página 1 en cada corrida. Este comportamiento es compatible con REQ-B4 (el padding en el nombre de archivo permite determinar qué páginas faltan por simple listado de directorio).
### Capa Silver (Calidad e Idempotencia)
 
- **REQ-S1:** Implementar un contrato de datos con **Pydantic V2** que valide:
  - `id` (int, requerido) — clave primaria.
  - `idMal` (int | None) — identificador secundario, se acepta nulo.
  - `title.romaji` (str, requerido, no vacío).
  - `description` (str, requerido) — tras limpieza de HTML, debe superar un umbral mínimo de longitud útil (sugerido: 50 caracteres). Una sinopsis vacía o de una línea no sirve para embeddings.
- **REQ-S2:** Bifurcar el flujo. Los registros que no pasen el contrato se guardan en `/silver/quarantine` junto con su `motivo_rechazo` y el payload original íntegro.
  **Formato:** JSON Lines (`.jsonl`), un registro por línea, con append por corrida. No Parquet: los registros rechazados tienen esquema heterogéneo por definición — forzarlos a un esquema tabular provoca fallos de escritura justo en el camino diseñado para no fallar.
- **REQ-S3:** Ejecutar un `upsert` idempotente contra `/silver/anime` usando el `MERGE` nativo de **delta-rs** (vía `deltalake.DeltaTable.merge()` o el equivalente expuesto por Polars), con `id` como llave de merge:
  1. Leer/crear la Delta table en `/silver/anime`. Si no existe, crearla con el esquema derivado del contrato Pydantic — **nunca** inferir esquema desde una tabla vacía.
  2. Deduplicar el lote entrante por `id` en Polars antes del merge, conservando la última ocurrencia (el `MERGE` de Delta falla o da resultado indefinido si el source tiene `id` repetidos).
  3. Calcular una columna `content_hash` sobre el lote (hash de las columnas de negocio, **excluyendo** `ingestion_timestamp` — si no, toda fila parece modificada en cada corrida y REQ-S4 nunca pasa).
  4. Ejecutar el merge con predicado `target.id = source.id`:
     - `whenMatchedUpdate`, condicionado a `target.content_hash != source.content_hash` (evita reescribir filas sin cambios reales — es lo que hace posible la idempotencia).
     - `whenNotMatchedInsertAll()`.
  5. **No** se requiere escritura atómica manual ni `os.replace`: el log de transacciones de Delta la da por construcción. Esto es exactamente lo que Polars solo no ofrecía — es la razón de reincorporar delta-rs.
- **REQ-S4:** Garantizar y emitir logs de idempotencia, tomando las métricas **directamente del diccionario que devuelve `merge().execute()`** — no recalcularlas a mano en Polars, para no duplicar lógica que Delta ya reporta de forma confiable:
  | Métrica del reporte | Campo nativo de delta-rs |
  |---|---|
  | `filas_leidas` | conteo del lote antes de deduplicar (calculado por el script) |
  | `filas_validas` | conteo tras REQ-S1 (calculado por el script) |
  | `filas_en_cuarentena` | conteo de rechazados por REQ-S2 (calculado por el script) |
  | `filas_nuevas` | `num_target_rows_inserted` |
  | `filas_actualizadas` | `num_target_rows_updated` |
  | `filas_totales_silver` | conteo post-merge de la Delta table (`DeltaTable.to_pandas().shape[0]` o equivalente en Polars) |
  **Criterio de aceptación:** procesar el mismo lote por segunda vez debe producir `num_target_rows_inserted = 0` **y** `num_target_rows_updated = 0`, con `filas_totales_silver` sin cambio.
- **REQ-S5 (nuevo):** Limpieza de `description` documentada y determinista (strip de tags HTML, decodificación de entidades, normalización de espacios). Determinista es requisito: si la limpieza varía entre corridas, `content_hash` (REQ-S3, paso 3) cambia en cada ejecución, el predicado `whenMatchedUpdate` se dispara siempre, y REQ-S4 nunca pasa.
### Capa Gold (Modelado e IA)
 
- **REQ-G0 (nuevo):** Antes de construir el índice definitivo, evaluar comparativamente **al menos dos** motores de índice vectorial contra el corpus real de Silver (no un dataset sintético). Candidatos mínimos: FAISS (`IndexFlatIP` o `IndexHNSWFlat`) y HNSWlib. La comparación debe reportar, para cada motor:
  | Criterio | Por qué importa aquí |
  |---|---|
  | Tiempo de construcción del índice | Con el volumen por defecto (~1,000 registros antes de cuarentena) puede empezar a mostrar diferencia entre motores, a diferencia de una muestra de decenas — repórtese con el tamaño real del corpus usado, no asumido. |
  | Latencia de búsqueda (p50/p95) sobre los queries de REQ-G3 | A este volumen ambos motores deberían responder en milisegundos; el número documenta que se midió, no que discriminó. |
  | Recall@k contra fuerza bruta (similitud coseno exacta) | **El criterio que de verdad importa a esta escala.** Fuerza bruta sigue siendo computacionalmente barata en el orden de miles de vectores — no hay necesidad real de sacrificar exactitud por velocidad todavía. Un índice aproximado (HNSW) que pierda recall aquí no se está ganando nada a cambio. |
  | Huella en disco de `/gold/index` | Relevante para el `.gitignore` y el tamaño de la imagen Docker. |
  | Soporte para `arm64` sin compilar desde fuente | Ver restricción de §3. `faiss-cpu` publica wheels arm64; verificar lo mismo para la alternativa antes de adoptarla. |
  **Salida obligatoria:** una tabla en el reporte final (ver §4) con estos criterios por motor, y una línea explícita de justificación de cuál se usa en producción (`/gold/index`). El motor descartado no se borra del repo — vive en el script de evaluación como evidencia reproducible.
  **Regla de decisión:** a un volumen de miles de vectores, fuerza bruta exacta sigue siendo viable — la exactitud (Recall@k = 1.0 vs. fuerza bruta) pesa más que la latencia. Si ambos motores empatan en recall, gana el de menor huella en disco. Si el usuario en el futuro escala la extracción al catálogo completo (~20,000+ entradas, ver REQ-B1), esta regla debe revisarse: ahí sí la latencia empieza a pesar frente a la exactitud marginal.
- **REQ-G1:** Consumir los registros limpios de Silver y generar embeddings con `all-MiniLM-L6-v2`.
  **El texto embebido es exclusivamente `description`.** El título **no** se concatena, no se antepone y no participa del vector bajo ninguna forma. La búsqueda es por contenido narrativo, no por nombre. Un agente que concatene `title + description` "para dar más contexto" está violando este requerimiento.
- **REQ-G2:** Construir/actualizar un índice vectorial y persistirlo en `/gold/index`, junto con el mapeo posición-en-índice → `id`. El mapeo se persiste con el índice; un índice sin su mapeo es inservible.
- **REQ-G3:** Exponer una función de Python para búsqueda semántica que reciba un query en texto y devuelva los metadatos relevantes. El título **sí** aparece en la salida (`id`, `title.romaji`, score de similitud) — es metadato de presentación, no insumo del embedding.
- **REQ-G4 (nuevo):** El índice debe ser idempotente respecto a Silver. Antes de embeber, comparar los `id` ya presentes en el mapeo contra los `id` de Silver y embeber **únicamente el delta**. Reejecutar el pipeline sin cambios en Silver debe producir `0` embeddings nuevos y `0` crecimiento del índice.
  Sin este requerimiento, la idempotencia de REQ-S4 se cumple en Silver pero se pierde en Gold: el índice acumula vectores duplicados en cada corrida y los resultados de búsqueda se degradan.
---
 
## 4. Estrategia de Pruebas y Reportabilidad
 
- **Prueba de Contrato:** Inyectar un JSON malformado (ej. `description` vacío, `id` ausente) y verificar su enrutamiento a cuarentena con el `motivo_rechazo` correcto.
- **Prueba de Idempotencia:** Ejecutar el pipeline dos veces con el mismo payload y afirmar que en la segunda corrida `num_target_rows_inserted = 0`, `num_target_rows_updated = 0` (métricas nativas del merge) y `filas_totales_silver` no incrementa en la Delta table de `/silver/anime`.
- **Prueba Semántica:** Inyectar un query descriptivo (ej. `"pirates searching for treasure"`, `"mecha pilots defending a city"`). Aserciones:
  - devuelve exactamente `k` resultados;
  - todos los `id` devueltos existen en Silver;
  - los scores vienen ordenados de mayor a menor;
  - el score del top-1 supera un umbral configurable.
  **No** afirmar qué título específico debe salir primero: esa aserción se rompe cada vez que cambia el corpus y convierte la suite en ruido.
- **Prueba de Idempotencia en Gold (nueva):** Ejecutar la construcción del índice dos veces sin cambios en Silver y afirmar que el número de vectores en `/gold/index` no incrementa (REQ-G4).
- **Prueba Comparativa de Índices (nueva):** Verificar que el script de evaluación de REQ-G0 produce, para cada motor candidato, las cinco métricas de la tabla de criterios, y que el recall reportado se calculó contra fuerza bruta real (no un valor hardcodeado).
- **Prueba de Resiliencia (nueva):** Simular una respuesta `429` con `Retry-After` y verificar que el cliente espera el tiempo indicado en lugar de reintentar de inmediato.
- **Prueba de Ritmo Proactivo (nueva):** Simular una respuesta con `X-RateLimit-Remaining` por debajo del umbral configurado y verificar que el cliente aumenta la pausa **antes** de recibir un 429, no después (REQ-B5).
- **Prueba de Reanudación (nueva):** Ejecutar una extracción parcial (ej. 5 de 20 páginas), interrumpir, y verificar que una segunda corrida completa las 15 restantes sin re-descargar las primeras 5 (REQ-B6).
- **Reporte de Ejecución:** El script principal debe finalizar generando un reporte tabular (Markdown o consola) con:
  - Tabla de conteo usando exactamente los nombres de REQ-S4: `filas_leidas`, `filas_validas`, `filas_en_cuarentena`, `filas_nuevas`, `filas_actualizadas`, `filas_totales_silver` — con una columna por corrida, para que la segunda evidencie cero duplicados.
  - Tabla comparativa de motores de índice vectorial (REQ-G0), con el motor elegido señalado explícitamente.
  - Tabla con el top 3 de resultados de la prueba de búsqueda semántica (`id`, título, score de similitud).
---
 
## 5. Entregables Esperados del Agente
 
- `docker-compose.yml` configurado con volúmenes locales.
- `Dockerfile` optimizado para el stack, base `linux/arm64`.
- `requirements.txt` con versiones fijadas y compatibles con ARM64.
- Scripts modulares de Python (o Jupyter Notebook estructurado) cubriendo las tres capas.
- Suite de pruebas (Agent Testing scripts).
- Reporte Final Resumido: módulo o celda que imprima las tablas de evidencia al finalizar la corrida.
- `.gitignore` que excluya archivos autogenerados, entornos virtuales, `.env` y estrictamente los directorios de datos (`/bronze`, `/silver`, `/gold`).
- `README.md` documentando arquitectura, cómo levantar los contenedores, cómo ejecutar las pruebas y cómo visualizar el reporte final.
---
 
## 6. Riesgos conocidos
 
| Riesgo | Mitigación |
|---|---|
| AniList aplica rate limiting o banea la IP por volumen sostenido | Ritmo proactivo con margen bajo el límite nominal (REQ-B5), no solo reacción a `429`. Con 20 páginas a ≥1s de pausa, la extracción completa toma ~20-25s de espera pura — nunca vale la pena arriesgar un baneo por ahorrar ese tiempo. |
| Una extracción larga se interrumpe a mitad de camino | Checkpointing por archivo existente en `/bronze` (REQ-B6). Sin esto, cada interrupción obliga a re-descargar todo desde la página 1, multiplicando el riesgo de rate limit del punto anterior. |
| `description` con HTML residual degrada la calidad de los embeddings | Limpieza determinista en Silver (REQ-S5) + umbral mínimo de longitud (REQ-S1). |
| `idMal` nulo rompe joins si se asume como PK | `id` de AniList es la única PK. `idMal` es opcional por contrato. |
| Limpieza no determinista rompe la idempotencia | La prueba de REQ-S4 lo detecta; ejecutarla en cada iteración, no solo al final. |
| ~~Sin transaccionalidad~~ — resuelto en v2.4 | Ya no aplica: delta-rs provee ACID y log de transacciones nativo para `/silver/anime` (REQ-S3). Se deja la fila como registro de que el riesgo existió y por qué se cerró, no como riesgo abierto. |
| Versión de `deltalake` sin wheel `arm64` para la variante fijada en `requirements.txt` | Verificar en Fase 0 (ver §3, Restricción ARM) antes de fijar la versión, no después de que falle el build. |
| `description` corta o nula reduce el corpus efectivo para Gold | Con el valor por defecto de 20 páginas (1,000 registros crudos), incluso descontando cuarentena el corpus debería quedar muy por encima del piso de ~50 registros necesario para que REQ-G0 discrimine entre motores de índice. Si tras la corrida quedan <200 registros en Gold, subir `paginas` antes de evaluar calidad de búsqueda. |
| Imagen Docker pesada | `sentence-transformers` arrastra PyTorch (~2-3 GB). Usar imagen base slim, instalar la variante CPU de torch y cachear el modelo en una capa dedicada para no re-descargarlo en cada build. |
| El agente concatena título + descripción al embeber | Prohibido explícitamente en REQ-G1. Verificable por inspección del código en Fase 3. |