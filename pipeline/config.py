"""Configuración compartida del pipeline. Todos los parámetros son de entrada (CLI/env),
nunca constantes hardcodeadas en la lógica de negocio (REQ-B1, Agents.md P1)."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineConfig:
    paginas: int = 20
    per_page: int = 50
    pausa_base: float = 1.0
    umbral_remaining: int = 10
    min_desc_len: int = 50
    k: int = 5

    bronze_dir: str = "bronze"
    silver_dir: str = "silver"
    gold_dir: str = "gold"
    reports_dir: str = "reports"

    anilist_url: str = "https://graphql.anilist.co"
    user_agent: str = "arq-medallion-pipeline/1.0 (+https://anilist.co; educational project)"


def _env_default(name: str, default, cast):
    val = os.environ.get(name)
    return cast(val) if val is not None else default


def from_args(argv: list[str] | None = None) -> PipelineConfig:
    parser = argparse.ArgumentParser(description="Pipeline medallón AniList → Bronze → Silver → Gold")
    parser.add_argument("--paginas", type=int, default=_env_default("PAGINAS", 20, int))
    parser.add_argument("--per-page", type=int, default=_env_default("PER_PAGE", 50, int))
    parser.add_argument("--pausa-base", type=float, default=_env_default("PAUSA_BASE", 1.0, float))
    parser.add_argument("--umbral-remaining", type=int, default=_env_default("UMBRAL_REMAINING", 10, int))
    parser.add_argument("--min-desc-len", type=int, default=_env_default("MIN_DESC_LEN", 50, int))
    parser.add_argument("--k", type=int, default=_env_default("SEARCH_K", 5, int))
    parser.add_argument("--bronze-dir", type=str, default=os.environ.get("BRONZE_DIR", "bronze"))
    parser.add_argument("--silver-dir", type=str, default=os.environ.get("SILVER_DIR", "silver"))
    parser.add_argument("--gold-dir", type=str, default=os.environ.get("GOLD_DIR", "gold"))
    parser.add_argument("--reports-dir", type=str, default=os.environ.get("REPORTS_DIR", "reports"))
    args = parser.parse_args(argv)

    return PipelineConfig(
        paginas=args.paginas,
        per_page=args.per_page,
        pausa_base=args.pausa_base,
        umbral_remaining=args.umbral_remaining,
        min_desc_len=args.min_desc_len,
        k=args.k,
        bronze_dir=args.bronze_dir,
        silver_dir=args.silver_dir,
        gold_dir=args.gold_dir,
        reports_dir=args.reports_dir,
    )
