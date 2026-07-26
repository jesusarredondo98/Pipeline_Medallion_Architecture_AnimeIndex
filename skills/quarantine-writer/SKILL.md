---
name: quarantine-writer
description: Usar cuando anime-data-contract rechaza un registro, para persistirlo en cuarentena con su motivo.
---

## Responsabilidad

Escribir los registros rechazados a `/silver/quarantine` junto con su `motivo_rechazo` y el
payload original íntegro.

## Requerimientos que satisface

- REQ-S2.
- INV-7 (cuarentena es JSONL append).

## Entradas

- `silver_dir: Path`.
- `motivo_rechazo: str` — viene de `ContractViolation.motivo_rechazo`.
- `original_payload: dict` — `ContractViolation.original_payload`, el `raw` sin modificar.

## Salidas

- `silver/quarantine/quarantine.jsonl` — una línea JSON por rechazo, con `motivo_rechazo`,
  `payload_original`, `quarantined_at`.
- `read_quarantine(silver_dir) -> list[dict]` para el reporte y las pruebas.

## Invariantes

- INV-7: JSONL append, nunca Parquet ni ningún esquema forzado — el payload original puede tener
  cualquier forma (incluso estar corrupto o incompleto).

## Procedimiento

1. Crear `silver_dir/quarantine` si no existe.
2. Construir la entrada con motivo, payload y timestamp.
3. Hacer append de una línea JSON al archivo — nunca reescribir el archivo completo.

## Criterios de aceptación

- Cada línea de `quarantine.jsonl` es JSON válido por sí sola (`json.loads` por línea).
- El `payload_original` es idéntico al registro que falló el contrato, sin transformar.

## Errores y modos de fallo

- Si el payload no es serializable directamente, se serializa con `default=str` — nunca se omite
  el registro completo por un campo no serializable.
