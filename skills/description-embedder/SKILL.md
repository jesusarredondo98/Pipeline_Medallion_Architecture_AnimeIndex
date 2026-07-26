---
name: description-embedder
description: Usar cuando se necesite generar embeddings de anime a partir de la descripción validada de Silver.
---

## Responsabilidad

Generar embeddings con `all-MiniLM-L6-v2` a partir exclusivamente de `description`.

## Requerimientos que satisface

- REQ-G1.
- INV-2 (el embedding es sólo `description`).

## Entradas

- `descriptions: list[str]` — columna `description` de Silver (ya limpia, post-contrato).
- `model: SentenceTransformer | None` — inyectable; por defecto carga (y cachea en memoria)
  `all-MiniLM-L6-v2`.

## Salidas

- `embed_descriptions(descriptions, model=None) -> np.ndarray` — matriz `(n, 384)` float32,
  L2-normalizada (para que producto punto == similitud coseno en el motor de índice).

## Invariantes

- INV-2: cumplida **estructuralmente** — la función no tiene ningún parámetro `titles` ni
  equivalente; no existe forma de que un título entre al texto a embeber a través de esta skill.
  Se verifica por **inspección de código** (tal como exige el DoD de Gold en Agents.md §5), no
  por un guard de contenido en tiempo de ejecución.

  **Decisión documentada:** se implementó y luego se retiró un guard que rechazaba cualquier
  texto que "contuviera" el título correspondiente. La corrida real contra AniList (Fase 2)
  produjo un falso positivo genuino: la sinopsis de *Eyeshield 21* revela ese mismo nombre como
  el alias del protagonista dentro de la narrativa — no es una fuga de título, es contenido
  legítimo. Un guard basado en contenido no puede distinguir una mención orgánica de una
  concatenación real, así que añadía riesgo de rechazar corpus válido sin aportar una garantía
  real (la garantía real es que `gold_pipeline.py` nunca construye el texto a partir de otra
  cosa que `description`, verificable leyendo el código).

## Procedimiento

1. Cargar (o reusar del caché en memoria) el modelo `all-MiniLM-L6-v2`.
2. Codificar las descripciones con `normalize_embeddings=True`.

## Criterios de aceptación

- Inspección de código confirma que el único insumo textual de `embed_descriptions` es
  `descriptions` — ninguna llamada en el repo le pasa un título ni una concatenación.
- El resultado tiene norma L2 ≈ 1 por fila (vectores normalizados).

## Errores y modos de fallo

- No aplica: función pura sobre el modelo cargado, sin lógica de rechazo de contenido.
