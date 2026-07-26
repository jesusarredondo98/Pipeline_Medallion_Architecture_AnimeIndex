"""Gobierna el ritmo de peticiones a AniList: pausa base entre peticiones + frenado proactivo
leyendo X-RateLimit-Remaining. Nunca paraleliza (INV-5) — es estado secuencial por diseño."""

from __future__ import annotations

import time
from typing import Callable


class RateLimitGovernor:
    def __init__(
        self,
        pausa_base: float,
        umbral_remaining: int,
        sleep_fn: Callable[[float], None] = time.sleep,
        monotonic_fn: Callable[[], float] = time.monotonic,
        epoch_fn: Callable[[], float] = time.time,
    ):
        self.pausa_base = pausa_base
        self.umbral_remaining = umbral_remaining
        self._sleep = sleep_fn
        self._monotonic = monotonic_fn
        self._epoch = epoch_fn
        self._last_request_at: float | None = None

    def wait_before_request(self) -> None:
        """Aplica la pausa base ≥ 1s desde la última petición (REQ-B5). Nunca se salta."""
        if self._last_request_at is None:
            return
        elapsed = self._monotonic() - self._last_request_at
        remaining_wait = self.pausa_base - elapsed
        if remaining_wait > 0:
            self._sleep(remaining_wait)

    def observe_response_headers(self, headers: dict) -> None:
        """Frenado proactivo: si Remaining cae bajo el umbral, esperar hasta Reset ANTES del 429."""
        self._last_request_at = self._monotonic()
        remaining = headers.get("X-RateLimit-Remaining")
        reset = headers.get("X-RateLimit-Reset")
        if remaining is None or reset is None:
            return
        if int(remaining) < self.umbral_remaining:
            sleep_for = float(reset) - self._epoch()
            if sleep_for > 0:
                self._sleep(sleep_for)
