---
name: arm64-dependency-audit
description: Usar cuando se necesite verificar que una dependencia candidata publica wheel linux/arm64 para la versión que se va a fijar, antes de escribirla en requirements.txt.
---

## Responsabilidad

Verificar que cada dependencia candidata publica wheel `linux/arm64` para la versión exacta que
se va a fijar, y reportar un sustituto cuando no lo hace.

## Requerimientos que satisface

- §3 Restricción ARM (PRD).
- §6 riesgo `deltalake` (PRD).
- P7 (verificar, no asumir, la matriz ARM64).

## Entradas

- Nombre del paquete y versión candidata.
- Versión de Python objetivo (3.12).

## Salidas

- `scripts/arm64_audit.md`: tabla con paquete, versión, wheels arm64 encontrados (o su ausencia)
  y sustituto propuesto cuando corresponda.

## Invariantes

Ninguna INV-* de datos; es una skill de Fase 0/1, no toca `/bronze`, `/silver` ni `/gold`.

## Procedimiento

1. Consultar `https://pypi.org/pypi/<paquete>/json` (o la versión específica
   `https://pypi.org/pypi/<paquete>/<version>/json`).
2. Filtrar el arreglo `urls` por archivos cuyo nombre contenga `aarch64` o `arm64`.
3. Si el paquete es un meta-paquete pure-Python (`py3-none-any.whl`) que depende de un paquete
   nativo (p. ej. `polars` → `polars-runtime-64`), repetir el paso 2 sobre la dependencia real.
4. Si no hay wheel arm64 para ninguna versión publicada del paquete, proponer un sustituto con
   cobertura arm64 equivalente en funcionalidad.
5. Registrar el resultado en `scripts/arm64_audit.md`, sin asumir compatibilidad no verificada.

## Criterios de aceptación

- Cada fila de la tabla de auditoría cita el nombre de archivo del wheel encontrado (evidencia),
  no una afirmación sin respaldo.
- Toda dependencia sin wheel arm64 tiene un sustituto propuesto explícito en la misma fila.

## Errores y modos de fallo

- Si la API de PyPI no responde, la skill no asume compatibilidad por omisión: reporta la
  verificación como pendiente, nunca la da por buena.
