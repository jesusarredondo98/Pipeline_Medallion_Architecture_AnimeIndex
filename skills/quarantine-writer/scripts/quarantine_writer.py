"""Escribe registros rechazados a /silver/quarantine en JSONL append (REQ-S2, INV-7). Nunca
Parquet: el esquema de los rechazados es heterogéneo por definición."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

QUARANTINE_FILENAME = "quarantine.jsonl"


def write_quarantine(
    silver_dir: Path,
    motivo_rechazo: str,
    original_payload: dict,
    now_fn=lambda: datetime.now(timezone.utc).isoformat(),
) -> Path:
    quarantine_dir = Path(silver_dir) / "quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    path = quarantine_dir / QUARANTINE_FILENAME
    entry = {
        "motivo_rechazo": motivo_rechazo,
        "payload_original": original_payload,
        "quarantined_at": now_fn(),
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    return path


def read_quarantine(silver_dir: Path) -> list[dict]:
    path = Path(silver_dir) / "quarantine" / QUARANTINE_FILENAME
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
