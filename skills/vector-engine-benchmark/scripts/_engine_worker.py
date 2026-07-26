"""Worker de un solo motor, ejecutado en su PROPIO proceso (ver vector_engine_benchmark.py para
el porqué: FAISS y usearch cargados en el mismo proceso producen un segfault reproducible)."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np


def _run_faiss(vectors: np.ndarray, queries: np.ndarray, k: int, index_dir: Path) -> dict:
    import faiss

    dim = vectors.shape[1]
    t0 = time.perf_counter()
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    build_time_ms = (time.perf_counter() - t0) * 1000

    latencies_ms = []
    results = []
    for q in queries:
        t0 = time.perf_counter()
        _, idx = index.search(q.reshape(1, -1), k)
        latencies_ms.append((time.perf_counter() - t0) * 1000)
        results.append(idx[0].tolist())

    index_path = index_dir / "faiss_flat_ip.index"
    faiss.write_index(index, str(index_path))

    return {
        "engine": "faiss.IndexFlatIP",
        "build_time_ms": build_time_ms,
        "latencies_ms": latencies_ms,
        "results": results,
        "disk_footprint_bytes": index_path.stat().st_size,
    }


def _run_usearch(vectors: np.ndarray, queries: np.ndarray, k: int, index_dir: Path) -> dict:
    from usearch.index import Index

    dim = vectors.shape[1]
    t0 = time.perf_counter()
    index = Index(ndim=dim, metric="ip", dtype="f32")
    keys = np.arange(vectors.shape[0])
    index.add(keys, vectors)
    build_time_ms = (time.perf_counter() - t0) * 1000

    latencies_ms = []
    results = []
    for q in queries:
        t0 = time.perf_counter()
        matches = index.search(q, k)
        latencies_ms.append((time.perf_counter() - t0) * 1000)
        results.append(np.asarray(matches.keys[:k]).tolist())

    index_path = index_dir / "usearch_hnsw.index"
    index.save(str(index_path))

    return {
        "engine": "usearch.Index (HNSW)",
        "build_time_ms": build_time_ms,
        "latencies_ms": latencies_ms,
        "results": results,
        "disk_footprint_bytes": index_path.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", required=True, choices=["faiss", "usearch"])
    parser.add_argument("--vectors", required=True)
    parser.add_argument("--queries", required=True)
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--index-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    vectors = np.load(args.vectors).astype("float32")
    queries = np.load(args.queries).astype("float32")
    index_dir = Path(args.index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)

    if args.engine == "faiss":
        result = _run_faiss(vectors, queries, args.k, index_dir)
    else:
        result = _run_usearch(vectors, queries, args.k, index_dir)

    Path(args.out).write_text(json.dumps(result))


if __name__ == "__main__":
    main()
