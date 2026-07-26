"""Punto de entrada del pipeline: Bronze → Silver → Gold → Reporte (Agents.md Fase 2, orden
estricto). Orquesta los orquestadores de capa; no contiene lógica de negocio propia."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from pipeline import skill_loader  # noqa: F401
from pipeline.config import from_args
from pipeline import bronze_pipeline, gold_pipeline, silver_pipeline

import description_embedder
import execution_report_renderer
import vector_engine_benchmark

DEFAULT_SEARCH_QUERY = "pirates searching for treasure"

# Prompts adicionales de ejemplo para el reporte extendido (más allá del top-3 mínimo de REQ-G3),
# pensados para inspección manual — incluye los dos ejemplos literales del PRD §4.
EXAMPLE_SEARCH_QUERIES = [
    "pirates searching for treasure",
    "mecha pilots defending a city",
    "detective solving a murder mystery",
    "high school romance and friendship",
    "space battle between rival factions",
    "cooking competition between chefs",
    "a lonely robot learning about humanity",
    "a young ninja who dreams of becoming the leader of his village",
    "a young boy with superhuman strength searching for magical dragon balls that grant wishes",
]


def main(argv: list[str] | None = None) -> None:
    config = from_args(argv)

    print(f"=== Bronze: ingiriendo hasta {config.paginas} páginas de AniList ===")
    bronze_result = bronze_pipeline.run_bronze(config)
    print(bronze_result)

    print("=== Silver: corrida 1 ===")
    silver_metrics_1 = silver_pipeline.run_silver(config)
    print(silver_metrics_1.as_dict())

    print("=== Silver: corrida 2 (evidencia de idempotencia, REQ-S4) ===")
    silver_metrics_2 = silver_pipeline.run_silver(config)
    print(silver_metrics_2.as_dict())

    print("=== Gold: benchmark de motores vectoriales contra el corpus real (REQ-G0) ===")
    silver_anime_dir = Path(config.silver_dir) / "anime"
    df = gold_pipeline.read_silver(silver_anime_dir)
    descriptions = df["description"].to_list()
    vectors = description_embedder.embed_descriptions(descriptions)

    rng = np.random.default_rng(42)
    n_queries = min(50, len(vectors))
    query_positions = rng.choice(len(vectors), size=n_queries, replace=False)
    queries = vectors[query_positions]

    with tempfile.TemporaryDirectory() as tmp_bench_dir:
        reports = vector_engine_benchmark.run_benchmark(vectors, queries, config.k, Path(tmp_bench_dir))
    winner, justification = vector_engine_benchmark.choose_engine(reports)
    print([r.as_dict() for r in reports])
    print(f"Motor elegido: {winner.engine} — {justification}")

    engine_name = "faiss" if "faiss" in winner.engine.lower() else "usearch"

    print(f"=== Gold: construyendo/actualizando el índice de producción con {engine_name} ===")
    gold_result = gold_pipeline.run_gold(config, engine=engine_name)
    print(gold_result)

    print(f'=== Búsqueda semántica de ejemplo: "{DEFAULT_SEARCH_QUERY}" ===')
    search_results = gold_pipeline.search(config, DEFAULT_SEARCH_QUERY, k=config.k)
    print(search_results)

    report = execution_report_renderer.render_full_report(
        silver_runs=[silver_metrics_1.as_dict(), silver_metrics_2.as_dict()],
        engine_reports=reports,
        winner_engine=winner.engine,
        engine_justification=justification,
        search_query=DEFAULT_SEARCH_QUERY,
        search_results=search_results,
    )
    print("\n" + report)

    print("=== Ejemplos adicionales de búsqueda semántica (reporte extendido) ===")
    examples = []
    for query in EXAMPLE_SEARCH_QUERIES:
        results = gold_pipeline.search(config, query, k=config.k)
        examples.append({"query": query, "results": results})
        print(f'  "{query}" -> top1: {results[0]["title_romaji"]!r} (score {results[0]["score"]:.4f})')
    examples_report = execution_report_renderer.render_search_examples_report(examples)

    reports_dir = Path(config.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "execution_report.md").write_text(report, encoding="utf-8")
    (reports_dir / "semantic_search_examples.md").write_text(examples_report, encoding="utf-8")
    print(f"\nReportes escritos en {reports_dir}/execution_report.md y {reports_dir}/semantic_search_examples.md")


if __name__ == "__main__":
    main()
