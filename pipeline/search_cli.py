"""CLI ligero para probar búsqueda semántica (REQ-G3) sobre un índice de Gold YA CONSTRUIDO,
sin re-ejecutar Bronze/Silver/Gold — útil para iterar rápido sobre distintos prompts."""

from __future__ import annotations

import argparse

from pipeline import skill_loader  # noqa: F401
from pipeline import gold_pipeline
from pipeline.config import PipelineConfig


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Búsqueda semántica sobre el índice de Gold existente")
    parser.add_argument("query", type=str, help="Texto de búsqueda, en el idioma de las descripciones (inglés)")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--bronze-dir", type=str, default="bronze")
    parser.add_argument("--silver-dir", type=str, default="silver")
    parser.add_argument("--gold-dir", type=str, default="gold")
    args = parser.parse_args(argv)

    config = PipelineConfig(
        bronze_dir=args.bronze_dir, silver_dir=args.silver_dir, gold_dir=args.gold_dir, k=args.k
    )
    results = gold_pipeline.search(config, args.query, k=args.k)

    print(f'Query: "{args.query}"')
    for r in results:
        synopsis = (r.get("description") or "").replace("\n", " ")
        if len(synopsis) > 160:
            synopsis = synopsis[:160].rstrip() + "…"
        print(f"  {r['score']:.4f}  [{r['id']:>6}]  {r['title_romaji']}")
        print(f"           {synopsis}")


if __name__ == "__main__":
    main()
