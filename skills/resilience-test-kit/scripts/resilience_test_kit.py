"""Dobles de prueba deterministas para simular respuestas de AniList sin red real: 429 con
Retry-After, X-RateLimit-Remaining bajo umbral, y extracción parcial interrumpida."""

from __future__ import annotations

import json
from typing import Callable

import httpx


def make_page_body(page: int, per_page: int, num_records: int = 1, has_next_page: bool = False) -> dict:
    """Cuerpo `{"data": {"Page": {...}}}` con la forma real de la query de referencia."""
    media = [
        {
            "id": page * 1000 + i,
            "idMal": None,
            "title": {"romaji": f"Anime {page}-{i}", "english": None, "native": None},
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
            "description": "Sinopsis de prueba con longitud suficiente para pasar el contrato. " * 2,
        }
        for i in range(num_records)
    ]
    return {
        "data": {
            "Page": {
                "pageInfo": {
                    "currentPage": page,
                    "lastPage": 20,
                    "hasNextPage": has_next_page,
                    "total": 1000,
                    "perPage": per_page,
                },
                "media": media,
            }
        }
    }


def json_response(status_code: int, body: dict | None = None, headers: dict | None = None) -> httpx.Response:
    headers = dict(headers or {})
    content = json.dumps(body).encode("utf-8") if body is not None else b""
    headers.setdefault("Content-Type", "application/json")
    return httpx.Response(status_code=status_code, headers=headers, content=content)


def scripted_handler(
    responses: list[httpx.Response], calls_log: list[httpx.Request] | None = None
) -> Callable[[httpx.Request], httpx.Response]:
    """Handler para httpx.MockTransport: devuelve la siguiente respuesta programada por llamada."""
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        if calls_log is not None:
            calls_log.append(request)
        if not queue:
            raise AssertionError("scripted_handler: no quedan respuestas programadas para esta llamada")
        return queue.pop(0)

    return handler
