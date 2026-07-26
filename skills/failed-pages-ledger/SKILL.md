---
name: failed-pages-ledger
description: Usar cuando una página agota sus reintentos, para registrarla y permitir que el pipeline continúe con la siguiente.
---

## Responsabilidad

Registrar las páginas que fallan definitivamente (tras agotar `http-retry-policy`, o por
`AniListQueryError`) y garantizar que el pipeline continúa con la siguiente página.

## Requerimientos que satisface

- REQ-B3 (no abortar la corrida por un lote).
- P4 (fallar suave en ingesta).

## Entradas

- `bronze_dir: Path`.
- `page: int`.
- `reason: str` — descripción del fallo (p. ej. `"RetriesExhausted: status=503"` o
  `"AniListQueryError: [...]"`).

## Salidas

- `bronze/failed_pages.jsonl` — JSONL append, una línea por fallo, con `page`, `reason`,
  `recorded_at`.
- `read_failures(bronze_dir) -> list[dict]` para el reporte final.

## Invariantes

Ninguna INV-* de datos directa; es la contraparte que hace que P4/REQ-B3 sean verificables (no
sólo "no lanzar excepción", sino dejar evidencia).

## Procedimiento

1. Al capturar `RetriesExhausted` o `AniListQueryError` para una página, llamar
   `record_failure(bronze_dir, page, reason)`.
2. El orquestador de Bronze (`bronze_pipeline.py`) continúa el bucle con la siguiente página —
   esta skill sólo registra, no controla el flujo.

## Criterios de aceptación

- Una corrida con 1 página fallida de 20 produce 19 archivos de lote válidos y una línea en
  `failed_pages.jsonl` — la corrida no termina en excepción no capturada.

## Errores y modos de fallo

- Si escribir el ledger falla (p. ej. disco lleno), la excepción se propaga: registrar el fallo
  de una página es la última red de seguridad, no puede fallar en silencio.
