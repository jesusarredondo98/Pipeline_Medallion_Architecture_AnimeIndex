---
name: vector-index-builder
description: Usar para crear el índice de Gold desde cero o para añadirle vectores nuevos, siempre persistiendo el mapeo posición→id junto al índice.
---

## Responsabilidad

Construir/actualizar el índice vectorial en `/gold/index`, junto con el mapeo
posición-en-índice → `id`.

## Requerimientos que satisface

- REQ-G2.
- INV-6 (el mapeo viaja con el índice).

## Entradas

- `gold_index_dir: Path`.
- `engine: "faiss" | "usearch"` — el motor elegido por `vector-engine-benchmark`.
- `vectors: np.ndarray` (float32, L2-normalizados, de `description-embedder`).
- `ids: list[int]` — `id` de AniList en el mismo orden que `vectors`.

## Salidas

- `/gold/index/{engine}.index` — índice serializado.
- `/gold/index/id_mapping.json` — `{"engine": ..., "ids": [...]}`; `ids[posición]` es el `id` de
  AniList en esa posición del índice.
- `vector_count(gold_index_dir) -> int`, `index_exists(...) -> bool`.

## Invariantes

- INV-6: `build_index` y `add_to_index` escriben SIEMPRE el mapeo junto con el índice, en la
  misma llamada — no hay forma de persistir uno sin el otro a través de esta skill.

## Procedimiento

1. `build_index`: si no existe índice previo, crearlo desde cero con todos los vectores/ids.
2. `add_to_index`: si ya existe un índice, añadir sólo los vectores nuevos (calculados por
   `gold-delta-indexer`) y extender el mapeo con los `ids` nuevos al final.
3. Import perezoso de `faiss`/`usearch`: sólo se importa la librería del motor efectivamente
   usado, dentro de la función — nunca ambas a nivel de módulo (evita el segfault de
   `vector-engine-benchmark` en el proceso de producción).

## Criterios de aceptación

- Tras `build_index`, `len(load_mapping(dir)["ids"]) == vectors.shape[0]`.
- Tras `add_to_index`, el mapeo previo se conserva en las mismas posiciones y los nuevos ids se
  agregan al final, sin reordenar.

## Errores y modos de fallo

- `add_to_index` sobre un directorio sin índice previo falla explícitamente (no hace fallback a
  `build_index` en silencio) — el orquestador de Gold decide cuál llamar según
  `index_exists(...)`.
