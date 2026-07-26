---
name: vector-engine-benchmark
description: Usar antes de construir el índice definitivo de Gold, para elegir el motor vectorial con evidencia medida contra el corpus real.
---

## Responsabilidad

Evaluar comparativamente ≥ 2 motores de índice vectorial contra el corpus real de Silver,
reportando tiempo de construcción, latencia p50/p95, Recall@k vs. fuerza bruta real, huella en
disco y soporte arm64; justificar el motor elegido en una línea.

## Requerimientos que satisface

- REQ-G0.

## Entradas

- `vectors: np.ndarray` (float32, L2-normalizados) — embeddings reales de `description-embedder`
  sobre el corpus de Silver.
- `queries: np.ndarray` — subconjunto de vectores (o embeddings de queries de prueba) usado para
  medir latencia y recall.
- `k: int`.
- `tmp_dir: Path` — directorio de trabajo para los índices serializados de cada motor.

## Salidas

- `run_benchmark(...) -> list[EngineReport]` — una fila por motor con las 5 métricas de REQ-G0.
- `choose_engine(reports) -> (EngineReport, str)` — motor ganador + línea de justificación,
  aplicando la regla de decisión del PRD (recall exacto pesa más que latencia a este volumen;
  empate → gana menor huella en disco).

## Invariantes

Ninguna INV-* de datos directa. Garantiza que el recall se calcula contra fuerza bruta REAL
(`_brute_force_topk`, similitud coseno exacta vía producto punto sobre vectores normalizados),
nunca un valor hardcodeado (P6).

## Procedimiento

1. Calcular el ground truth de fuerza bruta en el proceso principal (sólo NumPy, sin FAISS ni
   usearch — evita cualquier conflicto nativo).
2. Para cada motor candidato (`faiss`, `usearch`), lanzar `_engine_worker.py` en un **subproceso
   independiente** vía `sys.executable`, pasando vectores/queries por archivo `.npy`.
   **Motivo del aislamiento:** se reprodujo un segfault determinista (exit code 139) al cargar
   `faiss` y `usearch` en el mismo proceso de Python y ejecutar operaciones de ambos —
   probablemente conflicto de símbolos nativos SIMD/BLAS entre sus extensiones compiladas.
   Aislar cada motor en su propio proceso no es un workaround cosmético: es la práctica correcta
   para benchmarking de librerías nativas (evita también contención de hilos entre motores).
3. Cada worker mide su propio tiempo de construcción y latencia por query, serializa su índice a
   disco (mide huella real) y devuelve sus resultados top-k por JSON.
4. En el proceso principal, calcular `recall_at_k` comparando los resultados de cada motor contra
   el ground truth de fuerza bruta.
5. `choose_engine`: recall más alto gana; empate → menor huella en disco.

## Criterios de aceptación

- Cada `EngineReport` trae las 5 métricas de la tabla de REQ-G0.
- `recall_at_k` se calculó contra `_brute_force_topk`, no un valor fijo (verificado por
  `semantic-test-kit`, Prueba Comparativa de Índices).
- El motor descartado permanece en el repo (`_engine_worker.py` cubre ambos) — no se borra
  código, sólo no se usa en producción.

## Errores y modos de fallo

- Si un worker falla (`subprocess.run(..., check=True)`), la excepción se propaga sin intentar
  "adivinar" un resultado parcial — un benchmark que no pudo ejecutar un motor no reporta ese
  motor como ganador por omisión.
