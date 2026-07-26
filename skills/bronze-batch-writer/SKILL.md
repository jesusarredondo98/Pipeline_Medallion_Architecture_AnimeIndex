---
name: bronze-batch-writer
description: Usar cuando se necesite persistir un lote de registros crudos de AniList como archivo independiente en /bronze.
---

## Responsabilidad

Persistir cada lote como archivo independiente en `/bronze` con padding fijo, agregando
**sólo** `ingestion_timestamp`, `source`, `source_page` como metadata que envuelve el lote.

## Requerimientos que satisface

- REQ-B2, REQ-B4.
- INV-1 (Bronze es crudo).

## Entradas

- `bronze_dir: Path`.
- `page: int`.
- `media_records: list[dict]` — la lista `media` devuelta por `anilist-graphql-client`, sin
  modificar.
- `source: str` (default `"anilist_graphql"`).

## Salidas

- Archivo `anime_catalog_batch_{page:04d}.json` con la forma:
  ```json
  {"ingestion_timestamp": "...", "source": "...", "source_page": N, "records": [...]}
  ```
- Métrica implícita: existencia del archivo == página completada.

## Invariantes

- INV-1: `media_records` se serializa sin recorrerlo ni transformarlo — cero limpieza, casteo o
  normalización. La metadata envuelve el lote (`records`), no se inyecta dentro de cada registro,
  precisamente para no tocar "la estructura de los registros" (REQ-B2).

## Procedimiento

1. Crear `bronze_dir` si no existe.
2. Construir el sobre (`envelope`) con los 3 campos de metadata + `records`.
3. Escribir a un archivo temporal (`.json.tmp`) y renombrar de forma atómica al nombre final —
   evita dejar un archivo a medio escribir si el proceso se interrumpe a mitad de la escritura
   (consistente con REQ-B6: `bronze-resume-checkpoint` sólo debe ver archivos completos).

## Criterios de aceptación

- `anime_catalog_batch_0001.json` … `anime_catalog_batch_0020.json` ordenan igual
  lexicográficamente que numéricamente.
- El campo `records` es byte-idéntico a la entrada (mismo orden, mismas claves, mismos valores).

## Errores y modos de fallo

- Si la escritura se interrumpe, el archivo temporal (`.json.tmp`) queda huérfano pero el
  archivo final nunca existe a medias — `bronze-resume-checkpoint` no lo contará como válido.
