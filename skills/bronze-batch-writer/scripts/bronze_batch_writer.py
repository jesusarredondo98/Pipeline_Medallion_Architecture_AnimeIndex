"""Persiste cada lote como archivo independiente en /bronze. Bronze es crudo (INV-1): sólo se
agrega metadata de ingesta AL LOTE (envoltura del archivo), los registros individuales de
`media` viajan sin tocar."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def batch_filename(page: int) -> str:
    """Padding fijo de 4 dígitos: orden lexicográfico == orden numérico (REQ-B4)."""
    return f"anime_catalog_batch_{page:04d}.json"


def write_batch(
    bronze_dir: Path,
    page: int,
    media_records: list[dict],
    source: str = "anilist_graphql",
    now_fn=lambda: datetime.now(timezone.utc).isoformat(),
) -> Path:
    """Escribe el lote crudo. `media_records` no se modifica ni se recorre para limpiar: se
    serializa tal cual llegó de AniList (INV-1). La metadata de ingesta envuelve el lote, no
    cada registro, para no tocar 'la estructura de los registros' (REQ-B2)."""
    bronze_dir.mkdir(parents=True, exist_ok=True)
    envelope = {
        "ingestion_timestamp": now_fn(),
        "source": source,
        "source_page": page,
        "records": media_records,
    }
    final_path = bronze_dir / batch_filename(page)
    tmp_path = final_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(final_path)  # escritura atómica: nunca deja un .json a medio escribir
    return final_path
