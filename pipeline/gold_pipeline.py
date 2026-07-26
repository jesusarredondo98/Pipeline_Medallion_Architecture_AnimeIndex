"""Orquestador de la capa Gold. Compone skills atómicas: leer Silver → delta de ids →
embeber sólo el delta → construir/actualizar índice. Expone además `search(...)` para REQ-G3,
cargando el motor elegido de forma perezosa (nunca faiss y usearch juntos en el mismo proceso,
ver vector-engine-benchmark). No contiene lógica de negocio propia (Agents.md Fase 2)."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from pipeline import skill_loader  # noqa: F401
from pipeline.config import PipelineConfig

import description_embedder
import gold_delta_indexer
import semantic_search_api
import vector_index_builder


def read_silver(silver_anime_dir: Path) -> pl.DataFrame:
    return pl.read_delta(str(silver_anime_dir))


def run_gold(config: PipelineConfig, engine: str = "faiss") -> dict:
    silver_anime_dir = Path(config.silver_dir) / "anime"
    gold_index_dir = Path(config.gold_dir) / "index"

    df = read_silver(silver_anime_dir)
    silver_ids = df["id"].to_list()

    mapping = vector_index_builder.load_mapping(gold_index_dir)
    existing_ids = mapping["ids"]
    vector_count_antes = len(existing_ids)

    delta_ids = gold_delta_indexer.compute_delta_ids(silver_ids, existing_ids)

    if not delta_ids:
        return {
            "embeddings_nuevos": 0,
            "vector_count_antes": vector_count_antes,
            "vector_count_despues": vector_count_antes,
            "engine": mapping["engine"] or engine,
        }

    rows_by_id = {row["id"]: row for row in df.to_dicts()}
    descriptions = [rows_by_id[i]["description"] for i in delta_ids]

    vectors = description_embedder.embed_descriptions(descriptions)

    if vector_index_builder.index_exists(gold_index_dir, engine):
        vector_index_builder.add_to_index(gold_index_dir, engine, vectors, delta_ids)
    else:
        vector_index_builder.build_index(gold_index_dir, engine, vectors, delta_ids)

    vector_count_despues = vector_index_builder.vector_count(gold_index_dir)

    return {
        "embeddings_nuevos": len(delta_ids),
        "vector_count_antes": vector_count_antes,
        "vector_count_despues": vector_count_despues,
        "engine": engine,
    }


def _load_index(gold_index_dir: Path, engine: str):
    index_path = gold_index_dir / f"{engine}.index"
    if engine == "faiss":
        import faiss

        return faiss.read_index(str(index_path))
    if engine == "usearch":
        from usearch.index import Index

        return Index.restore(str(index_path))
    raise ValueError(f"motor desconocido: {engine}")


def search(config: PipelineConfig, query_text: str, k: int | None = None) -> list[dict]:
    silver_anime_dir = Path(config.silver_dir) / "anime"
    gold_index_dir = Path(config.gold_dir) / "index"
    k = k or config.k

    mapping = vector_index_builder.load_mapping(gold_index_dir)
    engine = mapping["engine"]
    ids_by_position = mapping["ids"]

    df = read_silver(silver_anime_dir)
    id_to_title = dict(zip(df["id"].to_list(), df["title_romaji"].to_list()))
    id_to_description = dict(zip(df["id"].to_list(), df["description"].to_list()))

    query_vector = description_embedder.embed_descriptions([query_text])[0]
    index = _load_index(gold_index_dir, engine)

    return semantic_search_api.search(
        query_vector, engine, index, ids_by_position, id_to_title, k, id_to_description=id_to_description
    )
