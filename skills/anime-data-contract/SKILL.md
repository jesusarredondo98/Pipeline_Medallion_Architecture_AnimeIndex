---
name: anime-data-contract
description: Usar cuando se necesite validar un registro crudo de Bronze contra el contrato de calidad de Silver antes de escribirlo o rechazarlo.
---

## Responsabilidad

Definir y aplicar el modelo Pydantic V2 del contrato de Silver: `id` int requerido, `idMal`
int|None, `title.romaji` str no vacío, `description` str con longitud mínima post-limpieza.

## Requerimientos que satisface

- REQ-S1.
- INV-3 (`id` de AniList es la única PK).

## Entradas

- `raw: dict` — registro crudo de Bronze + `ingestion_timestamp` (inyectado por el orquestador).
- `cleaned_description: str` — salida de `html-description-normalizer`.
- `min_desc_len: int` (default 50).

## Salidas

- `validate_record(...) -> AnimeRecord` en éxito.
- Excepción `ContractViolation(motivo_rechazo, original_payload)` en fallo — `original_payload`
  es el `raw` sin modificar, para que `quarantine-writer` lo persista íntegro.

## Invariantes

- INV-3: el modelo no tiene ni expone ningún campo que pueda usarse como llave de merge distinto
  de `id`. `id_mal` es explícitamente opcional y nunca se valida como requerido.

## Procedimiento

1. Verificar `len(cleaned_description) >= min_desc_len`; si no, `ContractViolation` con motivo
   explícito de longitud.
2. Aplanar la forma anidada de AniList (`title.romaji` → `title_romaji`, `studios.nodes[].name`
   → `studios`, `startDate`/`endDate` → columnas planas) — necesario porque Silver es tabular
   (Delta/Polars), no un documento anidado.
3. Instanciar `AnimeRecord(**flat)`; Pydantic valida tipos, `id` requerido, `title_romaji` no
   vacío.
4. Si Pydantic lanza `ValidationError`, envolver en `ContractViolation` con el mensaje completo
   como `motivo_rechazo` y el `raw` original (sin aplanar) como payload.

## Criterios de aceptación

- Un registro sin `id` → `ContractViolation` con motivo que menciona el campo faltante.
- Un registro con `description` vacía (o corta tras limpieza) → `ContractViolation` con motivo de
  longitud, no un error genérico de Pydantic (Prueba de Contrato, PRD §4).
- Un registro con `idMal: null` pasa el contrato sin problema (INV-3).

## Errores y modos de fallo

- Nunca deja pasar un registro inválido silenciosamente (P4: fallar duro en contrato). Toda
  violación se propaga como `ContractViolation`, nunca se ignora ni se rellena con defaults.
