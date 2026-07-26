---
name: semantic-test-kit
description: Usar para construir la Prueba Semántica y la Prueba Comparativa de Índices de Gold.
---

## Responsabilidad

Verificar `k` resultados, `id` existentes en Silver, scores descendentes, top-1 sobre umbral
configurable. Verificar que el benchmark de REQ-G0 produce las 5 métricas y que el recall se
calculó contra fuerza bruta real.

## Requerimientos que satisface

- Prueba Semántica, Prueba Comparativa de Índices (PRD §4).
- REQ-G0, REQ-G3.

## Entradas

- `results: list[dict]` — salida de `semantic_search_api.search(...)`.
- `k: int`, `valid_ids: set[int]`, `min_top1_score: float`.
- `reports: list[EngineReport]` — salida de `vector_engine_benchmark.run_benchmark(...)`.

## Salidas

- `assert_valid_search_results(...)` — `AssertionError` explícito si alguna propiedad falla.
- `assert_benchmark_report_complete(...)` — ídem para el benchmark de motores.

## Invariantes

**Prohibido** afirmar qué título específico debe salir primero: esa aserción se rompe cada vez
que cambia el corpus y convierte la suite en ruido (Agents.md §6, trampa conocida).

## Procedimiento

1. Verificar cardinalidad (`len(results) == k`), pertenencia de `id` a Silver, orden descendente
   de `score`, y que el top-1 supere el umbral.
2. Para el benchmark: verificar que cada motor reporta las 5 métricas de REQ-G0 y que
   `recall_at_k` está en `[0, 1]` — nunca hardcodeado (se calculó en `vector_engine_benchmark`
   contra `_brute_force_topk`, no contra un valor fijo).

## Criterios de aceptación

- Ver `tests/test_semantic.py`.

## Errores y modos de fallo

No aplica.
