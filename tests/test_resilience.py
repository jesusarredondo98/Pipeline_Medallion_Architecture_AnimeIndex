"""Pruebas de resiliencia de Bronze (PRD §4): 429/Retry-After, ritmo proactivo, reanudación.
Usa resilience-test-kit para no golpear la red real (P6: evidencia ejecutada, no afirmada)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

import anilist_client
import bronze_batch_writer
import bronze_resume_checkpoint
import http_retry_policy
import rate_limit_governor
import resilience_test_kit as rtk

from pipeline import bronze_pipeline
from pipeline.config import PipelineConfig


def test_429_espera_retry_after_y_reintenta():
    """El cliente espera el valor de Retry-After en lugar de reintentar de inmediato."""
    body_ok = rtk.make_page_body(page=1, per_page=50, num_records=2)
    responses = [
        rtk.json_response(429, headers={"Retry-After": "7"}),
        rtk.json_response(200, body=body_ok),
    ]
    calls = []
    transport = httpx.MockTransport(rtk.scripted_handler(responses, calls))
    sleeps: list[float] = []

    with httpx.Client(transport=transport) as client:
        def make_request():
            return anilist_client.request_page(client, "https://graphql.anilist.co", "ua", 1, 50)

        cfg = http_retry_policy.RetryPolicyConfig(sleep_fn=sleeps.append)
        response = http_retry_policy.execute_with_retry(make_request, cfg)

    assert response.status_code == 200
    assert len(calls) == 2
    assert sleeps == [7.0]  # espera EXACTAMENTE el Retry-After, no un backoff calculado


def test_frenado_proactivo_antes_del_429():
    """Con Remaining bajo el umbral, el gobernador frena ANTES de que ocurra un 429."""
    epoch_now = 1_000_000.0
    reset_at = epoch_now + 30.0

    governor = rate_limit_governor.RateLimitGovernor(
        pausa_base=1.0,
        umbral_remaining=10,
        sleep_fn=lambda s: sleeps.append(s),
        monotonic_fn=lambda: 0.0,
        epoch_fn=lambda: epoch_now,
    )
    sleeps: list[float] = []

    headers_bajo_umbral = {"X-RateLimit-Remaining": "3", "X-RateLimit-Reset": str(reset_at)}
    governor.observe_response_headers(headers_bajo_umbral)

    assert sleeps == [pytest.approx(30.0)]  # durmió hasta Reset, no reaccionó a un 429 que no ocurrió


def test_frenado_proactivo_no_actua_si_remaining_esta_sobre_el_umbral():
    sleeps: list[float] = []
    governor = rate_limit_governor.RateLimitGovernor(
        pausa_base=1.0,
        umbral_remaining=10,
        sleep_fn=lambda s: sleeps.append(s),
        monotonic_fn=lambda: 0.0,
        epoch_fn=lambda: 1_000_000.0,
    )
    governor.observe_response_headers({"X-RateLimit-Remaining": "50", "X-RateLimit-Reset": "1000100"})
    assert sleeps == []


def test_reanudacion_sin_redescarga(tmp_path: Path):
    """5 de 20 páginas ya presentes: una segunda corrida completa las 15 restantes sin
    re-descargar las primeras 5 (REQ-B6)."""
    bronze_dir = tmp_path / "bronze"

    # Simula una corrida previa interrumpida: páginas 1-5 ya escritas.
    for page in range(1, 6):
        bronze_batch_writer.write_batch(
            bronze_dir, page, rtk.make_page_body(page, 50, 1)["data"]["Page"]["media"]
        )

    pendientes = bronze_resume_checkpoint.pages_to_fetch(20, bronze_dir)
    assert pendientes == list(range(6, 21))

    # La segunda corrida sólo debe pedir las 15 páginas pendientes.
    responses = [
        rtk.json_response(200, body=rtk.make_page_body(p, 50, 1)) for p in pendientes
    ]
    calls: list[httpx.Request] = []
    transport = httpx.MockTransport(rtk.scripted_handler(responses, calls))

    config = PipelineConfig(paginas=20, bronze_dir=str(bronze_dir), pausa_base=0.0)

    original_client_cls = httpx.Client
    import unittest.mock as mock

    def client_factory(*args, **kwargs):
        return original_client_cls(transport=transport)

    with mock.patch("pipeline.bronze_pipeline.httpx.Client", side_effect=client_factory):
        resultado = bronze_pipeline.run_bronze(config)

    assert len(calls) == 15  # nunca re-pide las 5 ya presentes
    assert resultado["paginas_saltadas_checkpoint"] == 5
    assert resultado["paginas_escritas"] == 15
    assert resultado["paginas_fallidas"] == 0
    # Los 20 archivos de lote existen al final.
    assert len(bronze_resume_checkpoint.existing_valid_pages(bronze_dir)) == 20


def test_pagina_fallida_no_aborta_la_corrida(tmp_path: Path):
    """5xx agotando reintentos en una página: la corrida continúa con las demás (REQ-B3)."""
    bronze_dir = tmp_path / "bronze"
    responses = [
        rtk.json_response(200, body=rtk.make_page_body(1, 50, 1)),
        rtk.json_response(503),
        rtk.json_response(503),
        rtk.json_response(503),
        rtk.json_response(503),
        rtk.json_response(200, body=rtk.make_page_body(3, 50, 1)),
    ]
    calls: list[httpx.Request] = []
    transport = httpx.MockTransport(rtk.scripted_handler(responses, calls))
    config = PipelineConfig(paginas=3, bronze_dir=str(bronze_dir), pausa_base=0.0)

    import unittest.mock as mock

    real_client_cls = httpx.Client
    no_sleep_config = http_retry_policy.RetryPolicyConfig(sleep_fn=lambda s: None)

    def client_factory(*args, **kwargs):
        return real_client_cls(transport=transport)

    with mock.patch("pipeline.bronze_pipeline.httpx.Client", side_effect=client_factory), \
         mock.patch("pipeline.bronze_pipeline.http_retry_policy.RetryPolicyConfig", return_value=no_sleep_config):
        resultado = bronze_pipeline.run_bronze(config)

    assert resultado["paginas_escritas"] == 2
    assert resultado["paginas_fallidas"] == 1
    failures = json.loads((bronze_dir / "failed_pages.jsonl").read_text().splitlines()[0])
    assert failures["page"] == 2
