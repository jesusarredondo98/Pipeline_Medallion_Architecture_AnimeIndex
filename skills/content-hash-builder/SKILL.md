---
name: content-hash-builder
description: Usar al preparar un registro validado para el merge de Silver, para calcular el content_hash que decide si una fila cambió.
---

## Responsabilidad

Calcular `content_hash` sobre las columnas de negocio, excluyendo `ingestion_timestamp`, de
forma estable entre corridas.

## Requerimientos que satisface

- REQ-S3 paso 3.
- INV-4.

## Entradas

- `record: dict` — el registro ya validado por `anime-data-contract` (`AnimeRecord.model_dump()`),
  incluyendo `ingestion_timestamp`.

## Salidas

- `compute_content_hash(record) -> str` — SHA-256 hexadecimal.

## Invariantes

- INV-4: `ingestion_timestamp` se excluye explícitamente antes de serializar. Ningún otro campo
  se excluye — todas las demás columnas son "de negocio" y participan del hash.

## Procedimiento

1. Copiar el registro sin la clave `ingestion_timestamp`.
2. Serializar a JSON con `sort_keys=True` (la serialización no depende del orden de inserción del
   dict, condición necesaria para estabilidad — P3).
3. Calcular SHA-256 sobre la serialización canónica.

## Criterios de aceptación

- Dos invocaciones con el mismo registro (mismos valores, distinto `ingestion_timestamp`,
  incluso con las claves en distinto orden) producen el mismo hash.
- Cambiar cualquier campo de negocio (p. ej. `average_score`) cambia el hash.

## Errores y modos de fallo

- No aplica: es una función pura, sin I/O ni estado.
