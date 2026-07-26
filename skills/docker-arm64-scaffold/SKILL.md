---
name: docker-arm64-scaffold
description: Usar cuando se necesite generar o actualizar Dockerfile, docker-compose.yml y requirements.txt fijados para arm64.
---

## Responsabilidad

Generar `Dockerfile`, `docker-compose.yml` y `requirements.txt` con versiones fijadas y
compatibles con `linux/arm64`.

## Requerimientos que satisface

- §5 Entregables Esperados del Agente (PRD).
- §6 riesgo "Imagen Docker pesada" (PRD).

## Entradas

- Matriz de compatibilidad ARM64 producida por `arm64-dependency-audit`.
- Versión de Python fijada en Fase 0 (3.12).

## Salidas

- `requirements.txt` con versiones exactas (`==`), sin rangos.
- `Dockerfile` con base `linux/arm64`, instalación de `torch` desde el índice CPU dedicado, capa
  de caché del modelo de embeddings separada de la capa de código.
- `docker-compose.yml` con volúmenes locales (`/bronze`, `/silver`, `/gold`) y variables de
  entorno para los parámetros configurables del pipeline.

## Invariantes

Ninguna INV-* específica de datos; garantiza que el entorno de ejecución no requiere compilar
dependencias desde fuente (P7).

## Procedimiento

1. Tomar la matriz de `arm64-dependency-audit` y fijar cada versión en `requirements.txt`.
2. Excluir `torch` de `requirements.txt` (se instala en el Dockerfile desde el índice CPU).
3. Escribir el `Dockerfile`: base slim, `apt-get` mínimo, instalación de `torch` CPU, instalación
   de `requirements.txt`, pre-descarga del modelo `all-MiniLM-L6-v2` en su propia capa, copia de
   código al final (para maximizar reuso de caché de capas).
4. Escribir `docker-compose.yml` con un servicio `pipeline`, volúmenes de datos y variables de
   entorno con los defaults de Fase 0.

## Criterios de aceptación

- `docker compose build` termina sin error en arquitectura `arm64`.
- Ninguna dependencia se compila desde fuente durante el build (verificable en el log: no debe
  aparecer invocación a `cc`/`gcc`/`cargo build` para las dependencias de `requirements.txt`).

## Errores y modos de fallo

- Si una dependencia no tiene wheel arm64 para la versión fijada, no se agrega al
  `requirements.txt` sin antes pasar por `arm64-dependency-audit` con su sustituto documentado.
