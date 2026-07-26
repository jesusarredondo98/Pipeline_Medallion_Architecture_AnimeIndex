---
name: silver-metrics-emitter
description: Usar al final de cada corrida de Silver, para construir las 6 métricas de evidencia de idempotencia.
---

## Responsabilidad

Emitir las 6 métricas de REQ-S4 leyendo `num_target_rows_inserted` / `num_target_rows_updated`
**directamente** del resultado de `merge().execute()`.

## Requerimientos que satisface

- REQ-S4.
- P6 (la evidencia se emite, no se afirma).

## Entradas

- `filas_leidas: int` — conteo del lote antes de deduplicar (calculado por el orquestador).
- `filas_validas: int` — conteo tras `anime-data-contract`.
- `filas_en_cuarentena: int` — conteo de rechazos de `quarantine-writer`.
- `merge_result: dict` — el dict crudo de `delta_merge_upsert.upsert(...)`.
- `filas_totales_silver: int` — `delta_merge_upsert.total_rows(...)`.

## Salidas

- `SilverRunMetrics` (dataclass) con los 6 campos, nombrados EXACTAMENTE como en REQ-S4:
  `filas_leidas`, `filas_validas`, `filas_en_cuarentena`, `filas_nuevas`, `filas_actualizadas`,
  `filas_totales_silver`.

## Invariantes

Ninguna INV-* directa; es la garantía de que P6 se cumple para Silver — no hay una sola métrica
de idempotencia calculada a mano.

## Procedimiento

1. Tomar `filas_nuevas` de `merge_result["num_target_rows_inserted"]`.
2. Tomar `filas_actualizadas` de `merge_result["num_target_rows_updated"]`.
3. Ensamblar `SilverRunMetrics` con los 3 conteos del orquestador + los 2 nativos de Delta +
   `filas_totales_silver`.

## Criterios de aceptación

- `build_metrics(...).filas_nuevas` es idéntico a `merge_result["num_target_rows_inserted"]` sin
  ninguna transformación aritmética intermedia.
- Segunda corrida del mismo lote: `filas_nuevas == 0` y `filas_actualizadas == 0` y
  `filas_totales_silver` sin cambio respecto a la corrida anterior (criterio de aceptación de
  REQ-S4, verificado en `tests/test_idempotency.py`).

## Errores y modos de fallo

- Si `merge_result` no trae las claves nativas esperadas (cambio de versión de `deltalake` que
  renombra el campo), la skill falla con `KeyError` explícito — nunca sustituye por un valor
  recalculado a mano.
