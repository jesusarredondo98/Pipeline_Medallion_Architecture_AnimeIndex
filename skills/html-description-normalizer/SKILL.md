---
name: html-description-normalizer
description: Usar cuando se necesite limpiar el campo description de un registro crudo de Bronze antes de validarlo contra el contrato de Silver.
---

## Responsabilidad

Limpiar `description` de forma determinista: strip de tags HTML, decodificación de entidades,
normalización de espacios.

## Requerimientos que satisface

- REQ-S5.
- P3 (determinismo antes que conveniencia) — condición necesaria para INV-4/REQ-S4.

## Entradas

- `raw: str | None` — el `description(asHtml: false)` crudo de AniList (puede traer `<br>`,
  `<i>` y entidades residuales, ver nota del PRD §3.0).

## Salidas

- `clean_description(raw) -> str` — texto limpio, nunca `None` (cadena vacía si `raw` es
  `None`/vacío).

## Invariantes

- Ninguna INV-* directa, pero es condición de INV-4: el mismo `raw` debe producir siempre el
  mismo resultado, en cualquier corrida, en cualquier orden de ejecución.

## Procedimiento

1. Reemplazar `<br>`/`<br/>` (case-insensitive) por un espacio.
2. Eliminar cualquier otro tag HTML sin reemplazo.
3. Decodificar entidades HTML (`html.unescape`).
4. Colapsar cualquier secuencia de espacios/saltos de línea a un solo espacio y recortar bordes.

El orden es parte del contrato — no es intercambiable (ver docstring del script).

## Criterios de aceptación

- `clean_description(raw)` llamado dos veces con el mismo `raw` devuelve exactamente el mismo
  string (byte a byte) — verificado por `idempotency-test-kit` vía `content-hash-builder`.
- `<br>Hola<br/>Mundo<i>!</i>` produce `"Hola Mundo !"` (tags fuera, espacio donde había `<br>`).

## Errores y modos de fallo

- `raw=None` o cadena vacía → devuelve `""`, nunca lanza excepción. La decisión de rechazar por
  longitud insuficiente es responsabilidad de `anime-data-contract`, no de esta skill.
