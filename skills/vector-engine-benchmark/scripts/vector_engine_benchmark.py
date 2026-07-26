"""Evalúa comparativamente FAISS (exacto) y usearch (HNSW aproximado, sustituto de hnswlib)
contra el corpus real de Silver (REQ-G0). Cada motor corre en su PROPIO subproceso: se
reprodujo un segfault determinista al cargar `faiss` y `usearch` en el mismo proceso de Python
(conflicto de símbolos nativos SIMD/BLAS) — aislarlos es la forma correcta de medir un
benchmark de librerías nativas, no un workaround cosmético."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_WORKER_SCRIPT = Path(__file__).resolve().parent / "_engine_worker.py"
ENGINES = ("faiss", "usearch")


@dataclass(frozen=True)
class EngineReport:
    engine: str
    build_time_ms: float
    latency_p50_ms: float
    latency_p95_ms: float
    recall_at_k: float
    disk_footprint_bytes: int
    arm64_wheel: bool = True

    def as_dict(self) -> dict:
        return {
            "engine": self.engine,
            "build_time_ms": round(self.build_time_ms, 3),
            "latency_p50_ms": round(self.latency_p50_ms, 4),
            "latency_p95_ms": round(self.latency_p95_ms, 4),
            "recall_at_k": round(self.recall_at_k, 4),
            "disk_footprint_bytes": self.disk_footprint_bytes,
            "arm64_wheel": self.arm64_wheel,
        }


def _brute_force_topk(vectors: np.ndarray, queries: np.ndarray, k: int) -> np.ndarray:
    """Fuerza bruta real (similitud coseno exacta). Los embeddings ya vienen L2-normalizados
    (description-embedder), por lo que el producto punto equivale a similitud coseno."""
    sims = queries @ vectors.T
    return np.argsort(-sims, axis=1)[:, :k]


def _recall(results: list[list[int]], ground_truth: np.ndarray) -> float:
    hits = 0
    total = 0
    for r, gt in zip(results, ground_truth):
        hits += len(set(r) & set(gt.tolist()))
        total += len(gt)
    return hits / total if total else 0.0


def _run_engine_subprocess(
    engine: str, vectors: np.ndarray, queries: np.ndarray, k: int, tmp_dir: Path
) -> dict:
    vectors_path = tmp_dir / f"{engine}_vectors.npy"
    queries_path = tmp_dir / f"{engine}_queries.npy"
    out_path = tmp_dir / f"{engine}_result.json"
    np.save(vectors_path, vectors)
    np.save(queries_path, queries)

    subprocess.run(
        [
            sys.executable,
            str(_WORKER_SCRIPT),
            "--engine", engine,
            "--vectors", str(vectors_path),
            "--queries", str(queries_path),
            "--k", str(k),
            "--index-dir", str(tmp_dir / f"{engine}_index"),
            "--out", str(out_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(out_path.read_text())


def run_benchmark(vectors: np.ndarray, queries: np.ndarray, k: int, tmp_dir: Path) -> list[EngineReport]:
    """Ejecuta ambos motores contra el mismo corpus/queries y calcula recall@k contra fuerza
    bruta real (nunca hardcodeado)."""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    ground_truth = _brute_force_topk(vectors, queries, k)

    reports = []
    for engine in ENGINES:
        raw = _run_engine_subprocess(engine, vectors, queries, k, tmp_dir)
        latencies = raw["latencies_ms"]
        reports.append(
            EngineReport(
                engine=raw["engine"],
                build_time_ms=raw["build_time_ms"],
                latency_p50_ms=float(np.percentile(latencies, 50)),
                latency_p95_ms=float(np.percentile(latencies, 95)),
                recall_at_k=_recall(raw["results"], ground_truth),
                disk_footprint_bytes=raw["disk_footprint_bytes"],
            )
        )
    return reports


def choose_engine(reports: list[EngineReport]) -> tuple[EngineReport, str]:
    """Regla de decisión de REQ-G0: a este volumen, gana el recall exacto; en empate, gana la
    menor huella en disco."""
    best_recall = max(r.recall_at_k for r in reports)
    tied = [r for r in reports if r.recall_at_k == best_recall]
    if len(tied) == 1:
        winner = tied[0]
        justification = f"{winner.engine} tiene el mayor recall@k medido ({winner.recall_at_k:.3f})."
    else:
        winner = min(tied, key=lambda r: r.disk_footprint_bytes)
        names = ", ".join(r.engine for r in tied)
        justification = (
            f"Empate en recall@k ({best_recall:.3f}) entre {names}; gana {winner.engine} "
            f"por menor huella en disco ({winner.disk_footprint_bytes} bytes)."
        )
    return winner, justification
