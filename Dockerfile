# syntax=docker/dockerfile:1
FROM --platform=linux/arm64 python:3.12-slim AS base

# Dependencias de sistema mínimas.
# NOTA: usearch sustituye a hnswlib (sin wheels arm64, ver scripts/arm64_audit.md) — no se
# necesita build-essential/cmake, todas las deps de este stack son wheels precompiladas.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Capa dedicada de caché para torch/transformers: cambia poco entre builds, se cachea aparte
# de requirements.txt para no re-descargar ~500MB en cada iteración de código.
COPY requirements.txt .

# torch CPU-only desde el índice dedicado (decisión Fase 0): el paquete estándar de PyPI
# arrastra el stack CUDA (nvidia-cu13, cuda-toolkit) incluso en arm64 sin GPU.
RUN pip install --no-cache-dir torch==2.10.0+cpu --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# Caché del modelo de embeddings en su propia capa: se descarga una vez en build time,
# no en cada `docker compose run` (riesgo de imagen/arranque pesado, PRD §6).
ENV HF_HOME=/app/.hf_cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY skills/ ./skills/
COPY pipeline/ ./pipeline/
COPY tests/ ./tests/
COPY conftest.py .

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

ENTRYPOINT ["python", "-m", "pipeline.main"]
