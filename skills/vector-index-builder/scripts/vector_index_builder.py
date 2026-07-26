"""Construye/actualiza el índice vectorial en /gold/index y persiste el mapeo posición→id junto
al índice (REQ-G2, INV-6). Importa el motor (faiss/usearch) de forma perezosa: sólo se carga la
librería del motor elegido, nunca ambas en el mismo proceso (ver vector-engine-benchmark sobre
el segfault reproducido al mezclarlas)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

MAPPING_FILENAME = "id_mapping.json"


def _index_filename(engine: str) -> str:
    return f"{engine}.index"


def load_mapping(gold_index_dir: Path) -> dict:
    mapping_path = gold_index_dir / MAPPING_FILENAME
    if not mapping_path.exists():
        return {"engine": None, "ids": []}
    return json.loads(mapping_path.read_text())


def _save_mapping(gold_index_dir: Path, engine: str, ids: list[int]) -> None:
    (gold_index_dir / MAPPING_FILENAME).write_text(json.dumps({"engine": engine, "ids": ids}))


def build_index(gold_index_dir: Path, engine: str, vectors: np.ndarray, ids: list[int]) -> None:
    """Construye el índice DESDE CERO. El mapeo `ids[posición] == id de AniList` (INV-6)."""
    gold_index_dir.mkdir(parents=True, exist_ok=True)
    index_path = gold_index_dir / _index_filename(engine)

    if engine == "faiss":
        import faiss

        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        faiss.write_index(index, str(index_path))
    elif engine == "usearch":
        from usearch.index import Index

        index = Index(ndim=vectors.shape[1], metric="ip", dtype="f32")
        index.add(np.arange(len(ids)), vectors)
        index.save(str(index_path))
    else:
        raise ValueError(f"motor desconocido: {engine}")

    _save_mapping(gold_index_dir, engine, list(ids))


def add_to_index(gold_index_dir: Path, engine: str, new_vectors: np.ndarray, new_ids: list[int]) -> None:
    """Añade vectores nuevos a un índice YA EXISTENTE, extendiendo el mapeo (REQ-G4: sólo el
    delta se añade, nunca se reconstruye desde cero cuando ya hay un índice)."""
    mapping = load_mapping(gold_index_dir)
    existing_ids = mapping["ids"]
    start_pos = len(existing_ids)
    index_path = gold_index_dir / _index_filename(engine)

    if engine == "faiss":
        import faiss

        index = faiss.read_index(str(index_path))
        index.add(new_vectors)
        faiss.write_index(index, str(index_path))
    elif engine == "usearch":
        from usearch.index import Index

        index = Index.restore(str(index_path))
        keys = np.arange(start_pos, start_pos + len(new_ids))
        index.add(keys, new_vectors)
        index.save(str(index_path))
    else:
        raise ValueError(f"motor desconocido: {engine}")

    _save_mapping(gold_index_dir, engine, existing_ids + list(new_ids))


def index_exists(gold_index_dir: Path, engine: str) -> bool:
    return (gold_index_dir / _index_filename(engine)).exists()


def vector_count(gold_index_dir: Path) -> int:
    """Tamaño actual del índice, medido por el mapeo — evidencia usada por idempotency-test-kit
    para verificar 0 crecimiento (REQ-G4)."""
    return len(load_mapping(gold_index_dir)["ids"])
