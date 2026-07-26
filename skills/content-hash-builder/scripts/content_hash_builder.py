"""Calcula content_hash sobre las columnas de negocio, EXCLUYENDO ingestion_timestamp (INV-4).
Incluirlo hace que toda fila parezca modificada en cada corrida y REQ-S4 nunca pasa
(Agents.md §6, trampa conocida)."""

from __future__ import annotations

import hashlib
import json

_EXCLUDED_FIELDS = frozenset({"ingestion_timestamp"})


def compute_content_hash(record: dict) -> str:
    """Serialización canónica (claves ordenadas) para estabilidad entre corridas (P3)."""
    business_fields = {k: v for k, v in record.items() if k not in _EXCLUDED_FIELDS}
    canonical = json.dumps(business_fields, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
