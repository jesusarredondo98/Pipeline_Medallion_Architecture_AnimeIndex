---
name: execution-report-renderer
description: Usar al final de la corrida completa del pipeline, para imprimir el reporte de evidencia exigido por el PRD.
---

## Responsabilidad

Imprimir el reporte final: tabla de conteos con los nombres exactos de REQ-S4 (una columna por
corrida), tabla comparativa de motores con el elegido señalado, y top 3 de la búsqueda semántica.

## Requerimientos que satisface

- §4 Reporte de Ejecución (PRD).

## Entradas

- `silver_runs: list[dict]` — una entrada por corrida de Silver, con las 6 claves exactas de
  REQ-S4 (`SilverRunMetrics.as_dict()` de cada corrida).
- `engine_reports: list[EngineReport]`, `winner_engine: str`, `engine_justification: str` — de
  `vector-engine-benchmark`.
- `search_query: str`, `search_results: list[dict]` — de `semantic-search-api`; si cada resultado
  trae `"description"` (porque el orquestador pasó `id_to_description`), se muestra como columna
  `synopsis` truncada, para comparar visualmente el prompt contra la sinopsis real.

## Salidas

- `render_full_report(...) -> str` — Markdown completo, listo para imprimir en consola y/o
  persistir en `reports/execution_report.md`.
- `render_search_examples_report(examples) -> str` — Markdown con varios prompts de ejemplo y
  todos sus resultados (no sólo top-3), para `reports/semantic_search_examples.md` — pensado
  para inspección manual (p. ej. por un evaluador externo), no exigido literalmente por el PRD.

## Invariantes

Ninguna INV-* directa. Garantiza P6 (la evidencia se emite): los nombres de columna de la tabla
de conteos son literalmente `filas_leidas`, `filas_validas`, `filas_en_cuarentena`,
`filas_nuevas`, `filas_actualizadas`, `filas_totales_silver` — nunca una paráfrasis.

## Procedimiento

1. Tabla de conteos: una fila por métrica de REQ-S4, una columna por corrida (típicamente 2: la
   corrida real y una segunda corrida del mismo lote para evidenciar cero duplicados).
2. Tabla comparativa: una fila por motor evaluado en REQ-G0, con un marcador (`✓`) en la fila del
   motor elegido.
3. Top 3 de búsqueda: los primeros 3 resultados de una query de ejemplo, con `id`, `title_romaji`,
   `score` y `synopsis` (sinopsis real truncada a 160 caracteres, con `|` y saltos de línea
   escapados para no romper la tabla Markdown).

## Criterios de aceptación

- Las 6 columnas de la tabla de conteos usan los nombres literales de REQ-S4.
- La fila del motor elegido en la tabla comparativa lleva el marcador; ninguna otra fila lo lleva.
- El top 3 nunca excede 3 filas, incluso si `search_results` trae más.

## Errores y modos de fallo

- Si `silver_runs` tiene una sola corrida, la tabla se imprime igual con una sola columna — no
  es un error, sólo evidencia parcial (el llamador decide cuántas corridas incluir).
