---
name: contract-test-kit
description: Usar para construir la Prueba de Contrato de Silver (registros malformados que deben terminar en cuarentena).
---

## Responsabilidad

Inyectar JSON malformado (`description` vacío, `id` ausente) y verificar enrutamiento a
cuarentena con el `motivo_rechazo` correcto.

## Requerimientos que satisface

- Prueba de Contrato (PRD §4).
- REQ-S1, REQ-S2.

## Entradas

Ninguna externa: construye sus propios dobles de prueba.

## Salidas

- `make_valid_raw_record(id, description_len)` — registro crudo con la forma de Bronze, válido.
- `make_record_missing_id(...)` — variante sin `id`.
- `make_record_with_empty_description(...)` — variante con `description` vacía.

## Invariantes

No aplica: es infraestructura de prueba.

## Procedimiento

1. Construir un registro válido como línea base.
2. Generar variantes malformadas eliminando o vaciando un campo específico.
3. Pasar cada variante por `html-description-normalizer` + `anime-data-contract.validate_record`
   y verificar que lanza `ContractViolation` con un `motivo_rechazo` que menciona el campo roto.

## Criterios de aceptación

- Ver `tests/test_contract.py`.

## Errores y modos de fallo

No aplica.
