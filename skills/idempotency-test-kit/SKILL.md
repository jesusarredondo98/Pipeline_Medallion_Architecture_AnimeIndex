---
name: idempotency-test-kit
description: Usar para construir las pruebas de idempotencia de Silver y Gold (doble corrida sin duplicados).
---

## Responsabilidad

Doble corrida en Silver (`inserted=0`, `updated=0`, total sin cambio) y doble construcción en
Gold (sin crecimiento de vectores).

## Requerimientos que satisface

- Prueba de Idempotencia, Prueba de Idempotencia en Gold (PRD §4).
- REQ-S4, REQ-G4.

## Entradas

- `metrics_segunda_corrida: SilverRunMetrics` (de `silver-metrics-emitter`).
- `total_antes: int`, `total_despues: int` — `delta_merge_upsert.total_rows(...)` antes/después.
- `vector_count_antes/despues: int` — tamaño del índice de Gold antes/después de reconstruir.

## Salidas

- `assert_silver_idempotent(...)` — lanza `AssertionError` con mensaje explícito si no se cumple.
- `assert_gold_no_growth(...)` — ídem para Gold.

## Invariantes

No aplica: es infraestructura de prueba.

## Procedimiento

1. Ejecutar el orquestador de la capa (Silver o Gold) dos veces sobre el mismo insumo, sin
   cambios entre corridas.
2. Pasar los resultados de la segunda corrida (y los conteos antes/después) a la aserción
   correspondiente.

## Criterios de aceptación

- Ver `tests/test_idempotency.py`.

## Errores y modos de fallo

No aplica.
