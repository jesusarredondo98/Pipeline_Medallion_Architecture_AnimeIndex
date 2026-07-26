"""Limpieza determinista de `description` (REQ-S5). El orden de los pasos es parte del
contrato: si cambia entre corridas, `content_hash` (INV-4) deja de ser estable y REQ-S4 nunca
pasa (Agents.md §6, trampa conocida)."""

from __future__ import annotations

import html
import re

_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def clean_description(raw: str | None) -> str:
    """Pasos, en este orden exacto (determinismo, P3):
    1. `<br>` (con o sin `/`) se reemplaza por un espacio, para no pegar palabras entre líneas.
    2. Se eliminan el resto de tags HTML (p. ej. `<i>`, `<b>`) sin reemplazo.
    3. Se decodifican entidades HTML (`&amp;`, `&#39;`, ...).
    4. Se normalizan espacios (colapsa cualquier secuencia de whitespace a un solo espacio) y
       se recorta el resultado.
    """
    if not raw:
        return ""
    text = _BR_RE.sub(" ", raw)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text
