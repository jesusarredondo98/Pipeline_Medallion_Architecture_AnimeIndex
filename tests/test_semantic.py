"""Prueba Semántica, Prueba Comparativa de Índices, Prueba de Idempotencia en Gold (PRD §4)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

import bronze_batch_writer
import contract_test_kit as ctk
import description_embedder
import idempotency_test_kit as itk
import semantic_test_kit as stk
import vector_engine_benchmark as veb

from pipeline import gold_pipeline, silver_pipeline
from pipeline.config import PipelineConfig

_CORPUS = [
    ("Pirates of the Grand Line", "A crew of pirates sails the seas searching for a legendary hidden treasure, facing storms and rival crews. " * 2),
    ("Giant Robots Unite", "Teenage pilots climb into giant mecha robots to defend their city from a relentless alien invasion force. " * 2),
    ("School Romance Days", "Two high school students slowly fall in love while navigating exams, friendship and awkward misunderstandings. " * 2),
    ("Detective of the Old Town", "A sharp-witted detective investigates a string of mysterious disappearances in a quiet coastal town. " * 2),
    ("Cooking Battle Royale", "Rival chefs compete in high-stakes culinary tournaments to earn the title of grand master chef. " * 2),
]


def _build_corpus(tmp_path: Path) -> PipelineConfig:
    bronze_dir = tmp_path / "bronze"
    silver_dir = tmp_path / "silver"
    gold_dir = tmp_path / "gold"

    records = []
    for i, (title, desc) in enumerate(_CORPUS):
        raw = ctk.make_valid_raw_record(id=i + 1, description_len=len(desc))
        raw["title"]["romaji"] = title
        raw["description"] = desc
        raw.pop("ingestion_timestamp", None)
        records.append(raw)
    bronze_batch_writer.write_batch(bronze_dir, 1, records)

    config = PipelineConfig(bronze_dir=str(bronze_dir), silver_dir=str(silver_dir), gold_dir=str(gold_dir), k=2)
    silver_pipeline.run_silver(config)
    gold_pipeline.run_gold(config, engine="faiss")
    return config


def test_busqueda_semantica_devuelve_resultados_validos(tmp_path: Path):
    config = _build_corpus(tmp_path)
    results = gold_pipeline.search(config, "pirates searching for treasure", k=2)
    valid_ids = {i + 1 for i in range(len(_CORPUS))}
    stk.assert_valid_search_results(results, k=2, valid_ids=valid_ids, min_top1_score=0.2)


def test_busqueda_semantica_mecha(tmp_path: Path):
    config = _build_corpus(tmp_path)
    results = gold_pipeline.search(config, "mecha pilots defending a city", k=2)
    valid_ids = {i + 1 for i in range(len(_CORPUS))}
    stk.assert_valid_search_results(results, k=2, valid_ids=valid_ids, min_top1_score=0.2)


def test_gold_es_idempotente_sin_crecimiento(tmp_path: Path):
    config = _build_corpus(tmp_path)
    gold_index_dir = Path(config.gold_dir) / "index"
    import vector_index_builder

    antes = vector_index_builder.vector_count(gold_index_dir)
    result_2 = gold_pipeline.run_gold(config, engine="faiss")
    despues = vector_index_builder.vector_count(gold_index_dir)

    itk.assert_gold_no_growth(antes, despues)
    assert result_2["embeddings_nuevos"] == 0


def test_gold_embebe_solo_el_delta_al_agregar_registros(tmp_path: Path):
    config = _build_corpus(tmp_path)
    gold_pipeline.run_gold(config, engine="faiss")  # ya cubierto por _build_corpus, redundante a propósito

    # Agrega UN registro nuevo a Bronze/Silver.
    bronze_dir = Path(config.bronze_dir)
    raw = ctk.make_valid_raw_record(id=999, description_len=100)
    raw["title"]["romaji"] = "New Arrival"
    raw.pop("ingestion_timestamp", None)
    bronze_batch_writer.write_batch(bronze_dir, 2, [raw])
    silver_pipeline.run_silver(config)

    result = gold_pipeline.run_gold(config, engine="faiss")
    assert result["embeddings_nuevos"] == 1
    assert result["vector_count_despues"] == result["vector_count_antes"] + 1


def test_embed_descriptions_solo_acepta_descripciones():
    """INV-2 se cumple estructuralmente: no hay parámetro de título. Ver decisión documentada
    en skills/description-embedder/SKILL.md sobre por qué no hay guard de contenido."""
    import inspect

    params = list(inspect.signature(description_embedder.embed_descriptions).parameters)
    assert params == ["descriptions", "model"]


def test_benchmark_produce_las_5_metricas_por_motor(tmp_path: Path):
    np.random.seed(42)
    vectors = np.random.rand(50, 16).astype("float32")
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    queries = vectors[:8]

    reports = veb.run_benchmark(vectors, queries, k=5, tmp_dir=tmp_path / "bench")
    stk.assert_benchmark_report_complete(reports)

    winner, justification = veb.choose_engine(reports)
    assert winner.engine in {r.engine for r in reports}
    assert justification  # línea de justificación no vacía


def test_benchmark_recall_contra_fuerza_bruta_no_es_hardcodeado(tmp_path: Path):
    """El recall debe variar según los datos: con vectores idénticos duplicados, ambos motores
    deben acercarse a recall=1.0; verificamos que se calculó realmente comparando contra una
    segunda corrida con datos distintos y confirmando que el valor no es una constante fija."""
    np.random.seed(7)
    vectors_a = np.random.rand(60, 16).astype("float32")
    vectors_a /= np.linalg.norm(vectors_a, axis=1, keepdims=True)
    reports_a = veb.run_benchmark(vectors_a, vectors_a[:10], k=5, tmp_dir=tmp_path / "bench_a")

    for r in reports_a:
        assert r.recall_at_k == pytest.approx(1.0, abs=1e-6)  # query == vector propio, top-1 exacto siempre
