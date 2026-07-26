"""Registra páginas que fallan definitivamente, sin abortar la corrida (REQ-B3, P4)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

LEDGER_FILENAME = "failed_pages.jsonl"


def record_failure(
    bronze_dir: Path,
    page: int,
    reason: str,
    now_fn=lambda: datetime.now(timezone.utc).isoformat(),
) -> Path:
    """Append JSONL — cada línea es un fallo, nunca se sobrescribe el histórico de la corrida."""
    bronze_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = bronze_dir / LEDGER_FILENAME
    entry = {"page": page, "reason": reason, "recorded_at": now_fn()}
    with ledger_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return ledger_path


def read_failures(bronze_dir: Path) -> list[dict]:
    ledger_path = bronze_dir / LEDGER_FILENAME
    if not ledger_path.exists():
        return []
    with ledger_path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
