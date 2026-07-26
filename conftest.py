import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import skill_loader  # noqa: E402,F401  (registra sys.path de las skills)
