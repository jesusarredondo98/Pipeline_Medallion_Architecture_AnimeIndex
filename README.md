# Pipeline Medallón — AniList → Bronze → Silver → Gold

Pipeline de datos e IA sobre el catálogo de animes de [AniList](https://anilist.co), implementado
como arquitectura medallón (Bronze → Silver → Gold) con búsqueda semántica final.

- **Requerimientos:** [documents/PRD.md](documents/PRD.md) (v2.4)
- **Harness de agentes / decisiones de Fase 0-1:** [Agents.md](Agents.md)

## Arquitectura

```
AniList GraphQL API
       │  (POST, paginado, rate-limit gobernado)
       ▼
   /bronze/*.json          ← JSON crudo + metadata de ingesta (INV-1)
       │  (contrato Pydantic V2 + limpieza HTML determinista)
       ▼
   /silver/anime            ← Delta Lake, MERGE idempotente por `id` (INV-3, INV-4)
   /silver/quarantine/*.jsonl  ← registros rechazados (INV-7)
       │  (embeddings de `description`, exclusivamente — INV-2)
       ▼
   /gold/index               ← índice vectorial + mapeo posición→id (INV-6)
       │
       ▼
   búsqueda semántica (REQ-G3)
```

## Requisitos

- Docker + Docker Compose (imagen base `linux/arm64`).
- Sin dependencias del host: todo corre contenerizado.

## Levantar el pipeline (end-to-end, desde el contenedor)

```bash
# 1. Construir la imagen (una sola vez, o cada vez que cambie el código/requirements.txt)
docker compose build

# 2. Correr el pipeline completo: Bronze → Silver → Gold → Reporte
docker compose run --rm pipeline --paginas 20
```

**Importante:** el `entrypoint` del servicio ya es `python -m pipeline.main` — el segundo comando
NO lleva `python -m pipeline.main` de nuevo, sólo los argumentos (`--paginas 20`, etc.).

Parámetros configurables (ver `pipeline/config.py`): `--paginas`, `--per-page`, `--pausa-base`,
`--umbral-remaining`, `--min-desc-len`, `--k`, `--bronze-dir`, `--silver-dir`, `--gold-dir`,
`--reports-dir`.

Para repetir desde cero (sin checkpoint de corridas previas):

```bash
rm -rf bronze silver gold reports
docker compose run --rm pipeline --paginas 20
```

## Ejecutar pruebas (dentro del contenedor)

```bash
docker compose run --rm --entrypoint pytest pipeline -v
```

Cubre: contrato (cuarentena), idempotencia (Silver + Gold), resiliencia (429/backoff/ritmo
proactivo/reanudación) y búsqueda semántica + comparativa de motores vectoriales. 19/19 pruebas
verificadas tanto en `linux/arm64` (contenedor) como en desarrollo local.

## Probar búsquedas semánticas con otros prompts

Sin re-ejecutar Bronze/Silver/Gold (usa el índice de `/gold` ya construido):

```bash
docker compose run --rm --entrypoint python pipeline -m pipeline.search_cli "tu prompt en inglés" --k 5
```

Las descripciones de AniList están en inglés — los prompts funcionan mejor en ese idioma, y
mientras más se acerquen al vocabulario real de una sinopsis (en vez de nombres propios sueltos),
mejor discrimina la búsqueda semántica.

Cada resultado (en el CLI y en los reportes) incluye la sinopsis real del anime encontrado, para
comparar visualmente qué tan bien se relaciona con el prompt de búsqueda.

## Ver los reportes

Al finalizar `pipeline/main.py`, además de imprimirse en consola, quedan persistidos en
`reports/` (montado como volumen, visible en el host sin entrar al contenedor):

- `reports/execution_report.md` — las 3 tablas exigidas por el PRD §4: conteos de idempotencia de
  Silver (nombres exactos de REQ-S4), comparativa de motores vectoriales (REQ-G0, motor elegido
  señalado) y top-3 de una búsqueda semántica de ejemplo (REQ-G3), con columna `synopsis` (sinopsis
  real truncada) para comparar el prompt contra el resultado.
- `reports/semantic_search_examples.md` — reporte extendido (no exigido literalmente por el PRD)
  con varios prompts de ejemplo y todos sus resultados (incluida la misma columna `synopsis`),
  útil para inspección manual.

## Estructura

- `skills/` — 25 skills atómicas (contrato en `SKILL.md`, código en `scripts/`), catalogadas en
  `Agents.md` §4.
- `pipeline/` — orquestadores de capa (`bronze_pipeline.py`, `silver_pipeline.py`,
  `gold_pipeline.py`, `main.py`) y `search_cli.py` (búsqueda ad hoc). Componen skills; no
  contienen lógica de negocio propia.
- `tests/` — suite de pruebas de agente (Fase 3).
- `reports/` — reportes de evidencia generados por `main.py` (versionados, no gitignored).
- `scripts/arm64_audit.md` — evidencia de la auditoría de compatibilidad ARM64 (Fase 0).
