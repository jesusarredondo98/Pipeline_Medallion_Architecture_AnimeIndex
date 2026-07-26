"""Contrato de datos Pydantic V2 para Silver (REQ-S1). `id` de AniList es la única PK (INV-3);
`idMal` es opcional. La longitud mínima de `description` se aplica sobre el texto YA LIMPIO
(entrada de esta skill, no responsabilidad suya limpiarlo — eso es html-description-normalizer)."""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError


class AnimeRecord(BaseModel):
    id: int
    id_mal: int | None = None
    title_romaji: str = Field(min_length=1)
    title_english: str | None = None
    title_native: str | None = None
    format: str | None = None
    status: str | None = None
    episodes: int | None = None
    duration: int | None = None
    season: str | None = None
    season_year: int | None = None
    average_score: int | None = None
    popularity: int | None = None
    favourites: int | None = None
    genres: list[str] = Field(default_factory=list)
    studios: list[str] = Field(default_factory=list)
    start_year: int | None = None
    start_month: int | None = None
    start_day: int | None = None
    end_year: int | None = None
    end_month: int | None = None
    end_day: int | None = None
    description: str = Field(min_length=1)
    ingestion_timestamp: str


class ContractViolation(ValueError):
    """Un registro que no pasa el contrato. Lleva el `motivo_rechazo` y el payload ORIGINAL
    íntegro (previo a cualquier flattening), para que quarantine-writer lo persista intacto."""

    def __init__(self, motivo_rechazo: str, original_payload: dict):
        self.motivo_rechazo = motivo_rechazo
        self.original_payload = original_payload
        super().__init__(motivo_rechazo)


def _flatten(raw: dict) -> dict:
    """Aplana la forma anidada de AniList a columnas planas para Polars/Delta."""
    title = raw.get("title") or {}
    studios_nodes = ((raw.get("studios") or {}).get("nodes")) or []
    start = raw.get("startDate") or {}
    end = raw.get("endDate") or {}
    return {
        "id": raw.get("id"),
        "id_mal": raw.get("idMal"),
        "title_romaji": title.get("romaji"),
        "title_english": title.get("english"),
        "title_native": title.get("native"),
        "format": raw.get("format"),
        "status": raw.get("status"),
        "episodes": raw.get("episodes"),
        "duration": raw.get("duration"),
        "season": raw.get("season"),
        "season_year": raw.get("seasonYear"),
        "average_score": raw.get("averageScore"),
        "popularity": raw.get("popularity"),
        "favourites": raw.get("favourites"),
        "genres": raw.get("genres") or [],
        "studios": [n.get("name") for n in studios_nodes if n and n.get("name")],
        "start_year": start.get("year"),
        "start_month": start.get("month"),
        "start_day": start.get("day"),
        "end_year": end.get("year"),
        "end_month": end.get("month"),
        "end_day": end.get("day"),
        "ingestion_timestamp": raw.get("ingestion_timestamp"),
    }


def validate_record(raw: dict, cleaned_description: str, min_desc_len: int) -> AnimeRecord:
    """`raw` es el registro crudo de Bronze (con `ingestion_timestamp` ya inyectado por el
    orquestador de Silver). `cleaned_description` viene de `html-description-normalizer`.
    Lanza `ContractViolation` si no cumple el contrato — nunca deja pasar un registro inválido."""
    if len(cleaned_description) < min_desc_len:
        raise ContractViolation(
            f"description tiene {len(cleaned_description)} caracteres tras limpieza HTML, "
            f"mínimo requerido {min_desc_len}",
            raw,
        )
    flat = _flatten(raw)
    flat["description"] = cleaned_description
    try:
        return AnimeRecord(**flat)
    except ValidationError as exc:
        raise ContractViolation(f"Pydantic ValidationError: {exc}", raw) from exc
