"""Expone la búsqueda semántica (REQ-G3): recibe un vector de query ya embebido y un índice ya
cargado, devuelve id/título/score ordenados de mayor a menor. El título SÍ aparece aquí — es
metadato de presentación, nunca insumo del embedding (INV-2 aplica a description-embedder, no
a esta skill)."""

from __future__ import annotations

import numpy as np


def search(
    query_vector: np.ndarray,
    engine: str,
    index,
    ids_by_position: list[int],
    id_to_title: dict[int, str | None],
    k: int,
    id_to_description: dict[int, str | None] | None = None,
) -> list[dict]:
    """`index` ya fue cargado por el orquestador (evita que esta skill importe faiss/usearch
    directamente — sin acoplamiento cruzado con vector-index-builder).

    `id_to_description` es opcional y sólo enriquece la salida para inspección humana (p. ej.
    reportes, CLI) — comparar el prompt de búsqueda contra la sinopsis real. No participa del
    ranking ni del score: el embedding ya se calculó antes de llegar aquí (INV-2 sigue aplicando
    a description-embedder, no a esta skill)."""
    if engine == "faiss":
        scores, positions = index.search(query_vector.reshape(1, -1), k)
        pairs = [(int(p), float(s)) for p, s in zip(positions[0], scores[0]) if p >= 0]
    elif engine == "usearch":
        matches = index.search(query_vector, k)
        positions = np.asarray(matches.keys[:k])
        distances = np.asarray(matches.distances[:k])
        # usearch con metric="ip" devuelve DISTANCIA (menor=mejor): similitud = 1 - distancia,
        # para vectores normalizados (verificado empíricamente en Fase 2).
        pairs = [(int(p), float(1.0 - d)) for p, d in zip(positions, distances)]
    else:
        raise ValueError(f"motor desconocido: {engine}")

    results = []
    for position, score in pairs:
        if position < 0 or position >= len(ids_by_position):
            continue
        anime_id = ids_by_position[position]
        result = {"id": anime_id, "title_romaji": id_to_title.get(anime_id), "score": score}
        if id_to_description is not None:
            result["description"] = id_to_description.get(anime_id)
        results.append(result)

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:k]
