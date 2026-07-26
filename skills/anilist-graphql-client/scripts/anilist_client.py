"""Cliente GraphQL de AniList: una petición, sin reintentos (eso es http-retry-policy) y sin
pausas (eso es rate-limit-governor). Responsabilidad única: construir la petición y validar
`errors` antes de leer `data` (INV-8)."""

from __future__ import annotations

import httpx

QUERY = """
query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo { currentPage lastPage hasNextPage total perPage }
    media(type: ANIME, sort: ID) {
      id
      idMal
      title { romaji english native }
      format
      status
      episodes
      duration
      season
      seasonYear
      averageScore
      popularity
      favourites
      genres
      studios { nodes { name } }
      startDate { year month day }
      endDate { year month day }
      description(asHtml: false)
    }
  }
}
"""


class AniListQueryError(RuntimeError):
    """200 OK con `errors` en el cuerpo: error de query, no transitorio (REQ-B3, INV-8)."""

    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__(f"AniList devolvió errors en un 200 OK: {errors}")


def request_page(
    client: httpx.Client,
    url: str,
    user_agent: str,
    page: int,
    per_page: int,
    timeout: float = 30.0,
) -> httpx.Response:
    """Ejecuta una única petición POST. No interpreta el resultado ni reintenta."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": user_agent,
    }
    payload = {"query": QUERY, "variables": {"page": page, "perPage": per_page}}
    return client.post(url, json=payload, headers=headers, timeout=timeout)


def parse_page_response(response: httpx.Response) -> dict:
    """Valida `errors` ANTES de leer `data` (INV-8). Devuelve el objeto `Page` de AniList."""
    body = response.json()
    if body.get("errors"):
        raise AniListQueryError(body["errors"])
    return body["data"]["Page"]
