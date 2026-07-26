"""Orquestador de la capa Bronze. Compone skills atómicas en el orden: checkpoint → (por cada
página pendiente) rate-limit → request+retry → parseo → escritura, con fallo suave por página
(REQ-B3, P4). No contiene lógica de negocio propia, sólo composición (Agents.md Fase 2)."""

from __future__ import annotations

from pathlib import Path

import httpx

from pipeline import skill_loader  # noqa: F401  (efecto secundario: registra sys.path)
from pipeline.config import PipelineConfig

import anilist_client
import bronze_batch_writer
import bronze_resume_checkpoint
import failed_pages_ledger
import http_retry_policy
import rate_limit_governor


def run_bronze(config: PipelineConfig) -> dict:
    bronze_dir = Path(config.bronze_dir)
    pages = bronze_resume_checkpoint.pages_to_fetch(config.paginas, bronze_dir)
    saltadas = config.paginas - len(pages)

    governor = rate_limit_governor.RateLimitGovernor(
        pausa_base=config.pausa_base,
        umbral_remaining=config.umbral_remaining,
    )
    retry_config = http_retry_policy.RetryPolicyConfig()

    escritas = 0
    fallidas = 0

    with httpx.Client() as client:
        for page in pages:
            governor.wait_before_request()

            def make_request(page=page):
                return anilist_client.request_page(
                    client, config.anilist_url, config.user_agent, page, config.per_page
                )

            try:
                response = http_retry_policy.execute_with_retry(
                    make_request,
                    retry_config,
                    on_response=lambda r: governor.observe_response_headers(r.headers),
                )
            except http_retry_policy.RetriesExhausted as exc:
                failed_pages_ledger.record_failure(bronze_dir, page, f"RetriesExhausted: {exc}")
                fallidas += 1
                continue

            try:
                page_data = anilist_client.parse_page_response(response)
            except anilist_client.AniListQueryError as exc:
                failed_pages_ledger.record_failure(bronze_dir, page, f"AniListQueryError: {exc.errors}")
                fallidas += 1
                continue

            bronze_batch_writer.write_batch(
                bronze_dir, page, page_data["media"], source="anilist_graphql"
            )
            escritas += 1

    return {
        "paginas_solicitadas": config.paginas,
        "paginas_saltadas_checkpoint": saltadas,
        "paginas_escritas": escritas,
        "paginas_fallidas": fallidas,
    }
