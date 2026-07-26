"""Genera embeddings con all-MiniLM-L6-v2 a partir EXCLUSIVAMENTE de `description` (REQ-G1,
INV-2). La invariante se cumple estructuralmente: la función sólo acepta `descriptions`, no hay
ningún parámetro por el que un título pueda colarse al texto a embeber. Se verifica por
inspección de código (DoD de Gold), no por un guard de contenido en tiempo de ejecución: se
probó un guard basado en "el texto contiene el título" y se detectó, en la corrida real contra
AniList, que produce falsos positivos legítimos — muchas sinopsis mencionan el título de la obra
dentro de la narrativa (p. ej. "Eyeshield 21": el protagonista recibe ese alias dentro de la
propia sinopsis). Un guard de contenido no puede distinguir esa mención orgánica de una
concatenación real, así que se retiró."""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"

_model_cache: dict[str, SentenceTransformer] = {}


def load_model(model_name: str = MODEL_NAME) -> SentenceTransformer:
    if model_name not in _model_cache:
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


def embed_descriptions(descriptions: list[str], model: SentenceTransformer | None = None) -> np.ndarray:
    m = model or load_model()
    vectors = m.encode(
        descriptions,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vectors.astype("float32")
