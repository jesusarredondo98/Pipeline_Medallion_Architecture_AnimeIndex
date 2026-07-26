---
name: delta-merge-upsert
description: Usar cuando se necesite escribir un lote de registros validados a /silver/anime de forma idempotente.
---

## Responsabilidad

Crear/abrir la Delta table `/silver/anime` con esquema derivado del contrato, deduplicar el
lote entrante por `id` en Polars y ejecutar el `MERGE` nativo con `whenMatchedUpdate` condicionado
a hash distinto + `whenNotMatchedInsertAll`.

## Requerimientos que satisface

- REQ-S3 (pasos 1, 2, 4, 5).

## Entradas

- `silver_anime_dir: Path`.
- `df: pl.DataFrame` — lote de registros validados (`AnimeRecord.model_dump()` + `content_hash`),
  ya deduplicado por `deduplicate_by_id`.

## Salidas

- `ensure_table(...)` → `DeltaTable` (crea la tabla vacía con `arrow_schema()` si no existe).
- `deduplicate_by_id(df)` → `pl.DataFrame` sin `id` repetidos, conservando la última ocurrencia.
- `upsert(silver_anime_dir, df)` → `dict` — el resultado crudo de `merge().execute()`, sin
  transformar (`silver-metrics-emitter` lo consume).
- `total_rows(silver_anime_dir)` → `int` — conteo post-merge.

## Invariantes

- INV-3: el predicado de merge es siempre `target.id = source.id`, nunca `idMal`.

## Procedimiento

1. `ensure_table`: si `/silver/anime` no es una Delta table, crearla vacía con `arrow_schema()`
   derivado 1:1 del contrato Pydantic (nunca inferir desde una tabla vacía sin tipos).
2. `deduplicate_by_id`: `df.unique(subset=["id"], keep="last", maintain_order=True)`.
3. `upsert`: convertir a Arrow, ejecutar `dt.merge(predicate="target.id = source.id", ...)` con
   `when_matched_update(updates=todas_las_columnas, predicate="target.content_hash != source.content_hash")`
   y `when_not_matched_insert_all()`, y `execute()`.
4. La atomicidad de la escritura la da el log de transacciones de Delta — no hay `os.replace`
   manual (REQ-S3 paso 5).

## Criterios de aceptación

- Primera corrida con N registros nuevos: `num_target_rows_inserted == N`,
  `num_target_rows_updated == 0`.
- Segunda corrida con el mismo lote exacto: `num_target_rows_inserted == 0` **y**
  `num_target_rows_updated == 0`, `total_rows` sin cambio (verificado en Fase 2, ver
  `tests/test_idempotency.py`).
- Un registro con un campo de negocio distinto (mismo `id`): `num_target_rows_updated == 1`.

## Errores y modos de fallo

- Si `df` trae `id` repetidos sin pasar por `deduplicate_by_id`, el comportamiento del MERGE es
  indefinido (documentado explícitamente en el PRD) — esta skill no protege contra ese uso
  incorrecto, es responsabilidad del orquestador llamar los pasos en orden.
