---
name: gold-delta-indexer
description: Usar antes de embeber, para determinar qué ids de Silver aún no están en el índice de Gold.
---

## Responsabilidad

Comparar los `id` del mapeo del índice contra los `id` de Silver y devolver únicamente el delta a
embeber; garantizar 0 embeddings nuevos y 0 crecimiento cuando Silver no cambió.

## Requerimientos que satisface

- REQ-G4.

## Entradas

- `silver_ids: list[int]` — todos los `id` actualmente en `/silver/anime`.
- `existing_ids: list[int]` — `vector_index_builder.load_mapping(gold_index_dir)["ids"]`.

## Salidas

- `compute_delta_ids(silver_ids, existing_ids) -> list[int]` — ids a embeber en esta corrida.

## Invariantes

Ninguna INV-* directa; es la condición necesaria de REQ-G4 (idempotencia en Gold).

## Procedimiento

1. Construir un `set` de `existing_ids` para lookup O(1).
2. Filtrar `silver_ids` conservando sólo los que no están en ese set, en el orden original.

## Criterios de aceptación

- Con `silver_ids == existing_ids` (Silver sin cambios), `compute_delta_ids` devuelve `[]` — el
  orquestador de Gold no debe llamar a `description-embedder` en absoluto en ese caso, para que
  la Prueba de Idempotencia en Gold vea 0 embeddings nuevos.
- Con 3 ids nuevos en Silver, `compute_delta_ids` devuelve exactamente esos 3, ni más ni menos.

## Errores y modos de fallo

- No aplica: función pura, sin I/O.
