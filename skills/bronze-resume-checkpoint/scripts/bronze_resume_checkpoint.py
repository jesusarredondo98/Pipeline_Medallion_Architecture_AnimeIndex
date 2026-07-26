"""Determina qué páginas ya están completas en /bronze para no re-descargarlas (REQ-B6)."""

from __future__ import annotations

import json
import re
from pathlib import Path

_BATCH_RE = re.compile(r"^anime_catalog_batch_(\d{4})\.json$")


def _is_valid_batch_file(path: Path) -> bool:
    """Un archivo es válido si es JSON parseable con la forma esperada del sobre de Bronze."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return isinstance(data, dict) and "records" in data and "source_page" in data


def existing_valid_pages(bronze_dir: Path) -> set[int]:
    """Lista /bronze y devuelve el conjunto de números de página con archivo válido existente."""
    if not bronze_dir.exists():
        return set()
    valid_pages: set[int] = set()
    for entry in bronze_dir.iterdir():
        match = _BATCH_RE.match(entry.name)
        if match and _is_valid_batch_file(entry):
            valid_pages.add(int(match.group(1)))
    return valid_pages


def pages_to_fetch(total_pages: int, bronze_dir: Path) -> list[int]:
    """Rango 1..total_pages menos las páginas ya completas. Nunca reinicia desde la página 1."""
    done = existing_valid_pages(bronze_dir)
    return [p for p in range(1, total_pages + 1) if p not in done]
