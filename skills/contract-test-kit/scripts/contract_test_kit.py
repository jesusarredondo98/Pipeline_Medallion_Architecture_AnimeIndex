"""Dobles de prueba para la Prueba de Contrato: registros crudos válidos y variantes
malformadas (description vacía, id ausente) para verificar el enrutamiento a cuarentena."""

from __future__ import annotations


def make_valid_raw_record(id: int = 1, description_len: int = 80) -> dict:
    """Registro crudo con la forma de Bronze (media de AniList + ingestion_timestamp)."""
    return {
        "id": id,
        "idMal": None,
        "title": {"romaji": "Anime de prueba", "english": None, "native": None},
        "format": "TV",
        "status": "FINISHED",
        "episodes": 12,
        "duration": 24,
        "season": "SPRING",
        "seasonYear": 2020,
        "averageScore": 70,
        "popularity": 100,
        "favourites": 10,
        "genres": ["Action"],
        "studios": {"nodes": [{"name": "Studio X"}]},
        "startDate": {"year": 2020, "month": 1, "day": 1},
        "endDate": {"year": 2020, "month": 3, "day": 1},
        "description": "Sinopsis de prueba. " * (description_len // 20 + 1),
        "ingestion_timestamp": "2026-07-26T00:00:00Z",
    }


def make_record_missing_id(**kwargs) -> dict:
    record = make_valid_raw_record(**kwargs)
    del record["id"]
    return record


def make_record_with_empty_description(**kwargs) -> dict:
    record = make_valid_raw_record(**kwargs)
    record["description"] = ""
    return record
