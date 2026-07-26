"""Clasifica la respuesta HTTP y decide el reintento (REQ-B3). No conoce AniList ni GraphQL:
opera sobre httpx.Response / excepciones de transporte de forma genérica."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable

import httpx


class RetriesExhausted(RuntimeError):
    """Se agotaron los intentos sin obtener una respuesta 200. El llamador decide (failed-pages-ledger)."""

    def __init__(self, last_response: httpx.Response | None, last_exception: Exception | None):
        self.last_response = last_response
        self.last_exception = last_exception
        detail = (
            f"status={last_response.status_code}" if last_response is not None else str(last_exception)
        )
        super().__init__(f"Reintentos agotados: {detail}")


@dataclass
class RetryPolicyConfig:
    max_attempts: int = 4
    sleep_fn: Callable[[float], None] = time.sleep
    rng: random.Random = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.rng is None:
            self.rng = random.Random()


def _is_temporarily_disabled(response: httpx.Response) -> bool:
    return response.status_code == 403 and "temporarily disabled" in response.text.lower()


def _backoff_seconds(attempt: int, rng: random.Random) -> float:
    return (2 ** attempt) + rng.uniform(0, 1)


def execute_with_retry(
    make_request: Callable[[], httpx.Response],
    config: RetryPolicyConfig | None = None,
    on_response: Callable[[httpx.Response], None] | None = None,
) -> httpx.Response:
    """`make_request` ejecuta UNA petición (sin reintentar por su cuenta). Devuelve la Response
    200; lanza RetriesExhausted si se agotan los intentos en casos retryable.

    `on_response`, si se provee, se invoca con CADA respuesta recibida (incluidas las que van a
    reintentarse) — permite que el llamador observe headers de rate-limit en cada respuesta
    (REQ-B5) sin que esta skill conozca `rate-limit-governor` (sin acoplamiento cruzado)."""
    cfg = config or RetryPolicyConfig()
    attempt = 0
    last_response: httpx.Response | None = None
    last_exception: Exception | None = None

    while attempt < cfg.max_attempts:
        try:
            response = make_request()
        except httpx.RequestError as exc:
            attempt += 1
            last_exception = exc
            last_response = None
            if attempt >= cfg.max_attempts:
                break
            cfg.sleep_fn(_backoff_seconds(attempt, cfg.rng))
            continue

        if on_response is not None:
            on_response(response)

        status = response.status_code
        if status == 200:
            return response

        last_response = response
        last_exception = None

        if status == 429:
            attempt += 1
            if attempt >= cfg.max_attempts:
                break
            retry_after = float(response.headers.get("Retry-After", "1"))
            cfg.sleep_fn(retry_after)
            continue

        if _is_temporarily_disabled(response) or 500 <= status < 600:
            attempt += 1
            if attempt >= cfg.max_attempts:
                break
            cfg.sleep_fn(_backoff_seconds(attempt, cfg.rng))
            continue

        # Cualquier otro código (4xx no contemplado, distinto de 429/403-disponibilidad): no se
        # reintenta, se devuelve tal cual para que el llamador decida (p. ej. 200+errors se
        # valida aparte, fuera de esta skill).
        return response

    raise RetriesExhausted(last_response, last_exception)
