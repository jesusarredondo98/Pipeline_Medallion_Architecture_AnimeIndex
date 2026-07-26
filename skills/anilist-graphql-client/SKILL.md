---
name: anilist-graphql-client
description: Usar cuando se necesite ejecutar la query GraphQL paginada contra AniList y validar la respuesta antes de que otra skill la consuma.
---

## Responsabilidad

Ejecutar la query GraphQL paginada contra `https://graphql.anilist.co` vía `POST`, con los
headers correctos, y validar `errors` antes de leer `data`.

## Requerimientos que satisface

- REQ-B1 (extracción paginada).
- INV-8 (`errors` antes que `data`).
- §3.0 del PRD (contrato de la fuente).

## Entradas

- `client: httpx.Client` — inyectado, la skill no crea ni gestiona el ciclo de vida del cliente.
- `url: str` — endpoint, por defecto `https://graphql.anilist.co`.
- `user_agent: str` — descriptivo del proyecto (no se disfraza de navegador; el 504 de v1.0 no
  era una defensa anti-bot, ver changelog del PRD).
- `page: int`, `per_page: int` (máximo 50).

## Salidas

- `request_page(...)` → `httpx.Response` cruda, sin interpretar.
- `parse_page_response(response)` → `dict` con `pageInfo` y `media`, sólo si no hay `errors`.
- Excepción `AniListQueryError` si el cuerpo trae `errors` (contiene la lista completa de errores
  para que `failed-pages-ledger` la registre).

## Invariantes

- INV-8: `parse_page_response` nunca lee `data` sin antes comprobar `errors`.

## Procedimiento

1. Construir el payload GraphQL con la query de referencia (`sort: ID` para orden determinista,
   requisito de las pruebas de idempotencia).
2. Ejecutar un único `POST` con los headers de §3.0.
3. Devolver la respuesta cruda sin decidir reintentos (responsabilidad de `http-retry-policy`).
4. Al parsear: comprobar `errors` primero; si están presentes y no vacíos, lanzar
   `AniListQueryError`; si no, devolver `data.Page`.

## Criterios de aceptación

- Una respuesta con `{"errors": [...]}` y `data: null` nunca llega a devolver `media`.
- El payload incluye `sort: ID` literalmente.

## Errores y modos de fallo

- No reintenta bajo ninguna circunstancia — fuera de su alcance, delega en `http-retry-policy`.
- No aplica pausas ni backoff — fuera de su alcance, delega en `rate-limit-governor`.
