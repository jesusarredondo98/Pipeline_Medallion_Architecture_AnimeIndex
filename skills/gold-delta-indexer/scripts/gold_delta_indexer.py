"""Compara los id ya presentes en el mapeo del índice contra los id de Silver, devolviendo
ÚNICAMENTE el delta a embeber (REQ-G4). No embebe ni escribe el índice — eso es responsabilidad
de description-embedder y vector-index-builder, compuestos por el orquestador de Gold."""

from __future__ import annotations


def compute_delta_ids(silver_ids: list[int], existing_ids: list[int]) -> list[int]:
    """ids presentes en Silver que AÚN NO están en el mapeo del índice, en el orden en que
    aparecen en `silver_ids` (determinismo: mismo orden entre corridas)."""
    existing_set = set(existing_ids)
    return [i for i in silver_ids if i not in existing_set]
