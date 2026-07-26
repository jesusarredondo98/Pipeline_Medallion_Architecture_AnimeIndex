"""Registra los directorios scripts/ de cada skill en sys.path, para que los orquestadores
importen skills por nombre de módulo sin acoplarse a rutas ni duplicar código."""

from __future__ import annotations

import sys
from pathlib import Path

_SKILLS_ROOT = Path(__file__).resolve().parent.parent / "skills"


def register_skill_paths() -> None:
    for scripts_dir in sorted(_SKILLS_ROOT.glob("*/scripts")):
        path_str = str(scripts_dir)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


register_skill_paths()
