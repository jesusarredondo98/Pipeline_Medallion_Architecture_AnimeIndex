---
name: semantic-search-api
description: Usar para responder una búsqueda semántica ya con el query embebido y el índice cargado en memoria.
---

## Responsabilidad

Exponer la función de búsqueda semántica: recibe un vector de query, devuelve `id`,
`title.romaji` y score ordenados de mayor a menor.

## Requerimientos que satisface

- REQ-G3.

## Entradas

- `query_vector: np.ndarray` — embedding del texto de búsqueda (de `description-embedder`, sin
  `titles_for_guard` porque un query libre no tiene un título asociado que proteger).
- `engine: "faiss" | "usearch"`.
- `index` — objeto de índice ya cargado en memoria por el orquestador.
- `ids_by_position: list[int]` — `vector_index_builder.load_mapping(...)["ids"]`.
- `id_to_title: dict[int, str | None]` — de Silver (`id` → `title_romaji`).
- `k: int`.
- `id_to_description: dict[int, str | None] | None` — opcional, de Silver (`id` → `description`).
  Sólo enriquece la salida para inspección humana (comparar el prompt contra la sinopsis real en
  reportes/CLI); no participa del ranking.

## Salidas

- `search(...) -> list[dict]` — cada elemento `{"id": int, "title_romaji": str|None, "score": float}`,
  y además `"description": str|None` si se pasó `id_to_description`. Orden descendente por
  `score`, longitud ≤ `k`.

## Invariantes

Ninguna INV-* directa. El título aparece aquí porque REQ-G3 lo exige explícitamente como
metadato de presentación — no contradice INV-2 (que aplica al insumo del embedding, no a la
salida de búsqueda).

## Procedimiento

1. Ejecutar la búsqueda nativa del motor (`faiss` devuelve producto punto, mayor=mejor;
   `usearch` con `metric="ip"` devuelve distancia, menor=mejor — se convierte a similitud con
   `1 - distancia`, verificado empíricamente).
2. Mapear cada posición devuelta a su `id` de AniList vía `ids_by_position`.
3. Enriquecer con `title_romaji` desde `id_to_title` y, si se proveyó, `description` desde
   `id_to_description`.
4. Ordenar descendente por score y truncar a `k`.

## Criterios de aceptación

- Devuelve exactamente `k` resultados (o menos si el índice tiene menos de `k` vectores).
- Todos los `id` devueltos existen en `ids_by_position` (y por construcción, en Silver).
- Los scores vienen estrictamente no-crecientes.
- **Nunca** se afirma qué título específico debe salir primero — eso se rompe con cualquier
  cambio de corpus (Agents.md §6, trampa conocida).

## Errores y modos de fallo

- Una posición fuera de rango del mapeo (no debería ocurrir si `vector-index-builder` mantiene
  la invariante INV-6) se descarta silenciosamente del resultado, nunca se propaga como `None`.
