"""Imprime el reporte final: conteos de idempotencia (nombres exactos de REQ-S4, una columna
por corrida), comparativa de motores vectoriales (motor elegido señalado) y top 3 de búsqueda
semántica (§4 del PRD)."""

from __future__ import annotations

_METRIC_NAMES = [
    "filas_leidas",
    "filas_validas",
    "filas_en_cuarentena",
    "filas_nuevas",
    "filas_actualizadas",
    "filas_totales_silver",
]


def render_silver_counts_table(runs: list[dict]) -> str:
    """`runs`: una entrada dict por corrida, con las 6 claves exactas de REQ-S4."""
    headers = ["métrica"] + [f"corrida {i + 1}" for i in range(len(runs))]
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for name in _METRIC_NAMES:
        row = [name] + [str(run[name]) for run in runs]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_engine_comparison_table(reports: list, winner_engine: str) -> str:
    headers = [
        "motor", "tiempo_construccion_ms", "latencia_p50_ms", "latencia_p95_ms",
        "recall_at_k", "huella_disco_bytes", "elegido",
    ]
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in reports:
        d = r.as_dict()
        marker = "✓" if r.engine == winner_engine else ""
        row = [
            d["engine"], str(d["build_time_ms"]), str(d["latency_p50_ms"]),
            str(d["latency_p95_ms"]), str(d["recall_at_k"]), str(d["disk_footprint_bytes"]), marker,
        ]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _markdown_safe_synopsis(description: str | None, max_len: int = 160) -> str:
    """Escapa `|` y saltos de línea (rompen una fila de tabla Markdown) y trunca para que la
    tabla siga siendo legible — sólo afecta la presentación, nunca el texto embebido (INV-2 no
    aplica aquí: description-embedder ya recibió el texto completo antes de este punto)."""
    if not description:
        return ""
    flat = description.replace("|", "/").replace("\n", " ").strip()
    if len(flat) > max_len:
        return flat[:max_len].rstrip() + "…"
    return flat


def render_top_search_results(results: list[dict], query: str, limit: int = 3) -> str:
    headers = ["id", "title_romaji", "score", "synopsis"]
    lines = [f'Query: "{query}"', "", "| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in results[:limit]:
        synopsis = _markdown_safe_synopsis(r.get("description"))
        lines.append(f"| {r['id']} | {r['title_romaji']} | {r['score']:.4f} | {synopsis} |")
    return "\n".join(lines)


def render_search_examples_report(examples: list[dict]) -> str:
    """`examples`: lista de {"query": str, "results": list[dict]} — reporte extendido con
    varios prompts de ejemplo (todos los resultados devueltos, no sólo top-3), más allá del
    mínimo de REQ-G3, pensado para inspección manual del profesor/usuario."""
    lines = ["# Ejemplos de Búsqueda Semántica", ""]
    for example in examples:
        results = example["results"]
        lines.append(render_top_search_results(results, example["query"], limit=len(results)))
        lines.append("")
    return "\n".join(lines)


def render_full_report(
    silver_runs: list[dict],
    engine_reports: list,
    winner_engine: str,
    engine_justification: str,
    search_query: str,
    search_results: list[dict],
) -> str:
    return "\n".join([
        "# Reporte de Ejecución",
        "",
        "## Conteos de Silver (idempotencia, REQ-S4)",
        "",
        render_silver_counts_table(silver_runs),
        "",
        "## Comparativa de motores vectoriales (REQ-G0)",
        "",
        render_engine_comparison_table(engine_reports, winner_engine),
        "",
        f"**Motor elegido:** {winner_engine} — {engine_justification}",
        "",
        "## Top 3 de búsqueda semántica (REQ-G3)",
        "",
        render_top_search_results(search_results, search_query),
        "",
    ])
