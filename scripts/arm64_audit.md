# Auditoría de compatibilidad ARM64 — Fase 0

Verificado contra la API JSON de PyPI (`https://pypi.org/pypi/<paquete>/json`) el 2026-07-26.
Comando de verificación reproducible:

```bash
for pkg in polars deltalake pydantic pydantic-core sentence-transformers torch faiss-cpu hnswlib usearch; do
  echo "=== $pkg ==="
  curl -s "https://pypi.org/pypi/$pkg/json" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('latest:', d['info']['version'])
for u in d['urls']:
    fn = u['filename']
    if 'aarch64' in fn or 'arm64' in fn or fn.endswith('any.whl') or fn.endswith('.tar.gz'):
        print(' ', fn)
"
done
```

## Resultado

| Dependencia | Versión fijada | Wheel `linux/arm64` | Detalle |
|---|---|---|---|
| `polars` | 1.43.0 | Sí | Meta-wheel `py3-none-any` que depende de `polars-runtime-64`, el cual sí publica `manylinux_2_17_aarch64` (abi3, cp310+). |
| `deltalake` | 1.6.2 | Sí | `manylinux_2_28_aarch64` (cp310-abi3, compatible cp310+). |
| `pydantic` | 2.13.4 | Sí | Pure Python; su motor `pydantic-core==2.47.0` publica `manylinux_2_17_aarch64` para cp311/cp312/cp313. |
| `sentence-transformers` | 5.6.1 | Sí | Pure Python; arrastra `torch` (ver fila siguiente). |
| `torch` | 2.10.0+cpu | Sí, con matiz | El paquete `torch` estándar de PyPI publica wheel `manylinux_2_28_aarch64` pero declara dependencias `nvidia-cu13`/`cuda-toolkit` incondicionales en Linux. **Se fija desde el índice CPU dedicado** (`https://download.pytorch.org/whl/cpu`), que publica `torch-2.10.0+cpu-cp312-cp312-manylinux_2_28_aarch64.whl` sin dependencias CUDA. |
| `faiss-cpu` | 1.14.3 | Sí | `manylinux_2_27_aarch64.manylinux_2_28_aarch64` (cp310-abi3). |
| `hnswlib` | 0.8.0 | **No, nunca** | Se revisó el historial completo (0.5.0 → 0.8.0): sólo publica `.tar.gz` (sdist) en todas sus versiones, para cualquier plataforma. Compilarlo exigiría `build-essential`/`cmake` en la imagen. |
| `usearch` (sustituto de `hnswlib`) | 2.26.0 | Sí | `manylinux_2_26_aarch64.manylinux_2_28_aarch64` para cp310–cp314. Implementa un índice HNSW comparable; cumple el mínimo de "≥2 motores" de REQ-G0 sin compilar desde fuente (P7). |
| `pyarrow` | 25.0.0 | Sí | `manylinux_2_28_aarch64` para cp310–cp314. Necesario para la conversión Polars↔Arrow que consume `deltalake.DeltaTable.merge()`; no estaba en la lista original de Fase 0, se detectó al implementar `delta-merge-upsert` (Fase 2) y se audita aquí para no romper P7. |

## Decisiones derivadas (aprobadas por el usuario en el gate de Fase 0)

1. **Motor B de REQ-G0:** `usearch` en lugar de `hnswlib`.
2. **`torch`:** instalado desde `--index-url https://download.pytorch.org/whl/cpu`, no desde PyPI estándar.
3. **Python objetivo:** 3.12 (cobertura arm64 confirmada para las 8 dependencias auditadas).

Ninguna dependencia se compila desde fuente en este stack (P7, INV cumplida).
