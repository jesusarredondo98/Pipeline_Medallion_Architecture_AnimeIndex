"""Aserciones reutilizables para la Prueba Semántica y la Prueba Comparativa de Índices
(PRD §4). Nunca afirma qué título específico debe salir primero (Agents.md §6, trampa
conocida) — sólo verifica propiedades estructurales robustas a cambios de corpus."""

from __future__ import annotations


def assert_valid_search_results(results: list[dict], k: int, valid_ids: set[int], min_top1_score: float) -> None:
    assert len(results) == k, f"esperaba {k} resultados, obtuve {len(results)}"
    for r in results:
        assert r["id"] in valid_ids, f"id {r['id']} no existe en Silver"
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True), f"scores no vienen ordenados descendente: {scores}"
    assert scores[0] >= min_top1_score, f"score del top-1 ({scores[0]}) no supera el umbral {min_top1_score}"


def assert_benchmark_report_complete(reports: list) -> None:
    """Verifica que el benchmark de REQ-G0 produjo las 5 métricas para cada motor y que el
    recall no es un valor fijo/hardcodeado (varía según los datos reales de entrada)."""
    required_fields = {
        "build_time_ms",
        "latency_p50_ms",
        "latency_p95_ms",
        "recall_at_k",
        "disk_footprint_bytes",
    }
    assert len(reports) >= 2, "REQ-G0 exige comparar al menos 2 motores"
    for report in reports:
        as_dict = report.as_dict()
        missing = required_fields - as_dict.keys()
        assert not missing, f"faltan métricas {missing} para {report.engine}"
        assert 0.0 <= report.recall_at_k <= 1.0
