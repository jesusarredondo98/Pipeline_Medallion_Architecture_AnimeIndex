---
name: bronze-resume-checkpoint
description: Usar al iniciar una corrida de Bronze, para saltar páginas cuyo archivo ya existe y es válido.
---

## Responsabilidad

Al iniciar, listar `/bronze`, determinar qué páginas ya tienen archivo válido y devolver sólo las
páginas pendientes — nunca reiniciar desde la página 1.

## Requerimientos que satisface

- REQ-B6.

## Entradas

- `bronze_dir: Path`.
- `total_pages: int` — el valor de `paginas` de la corrida actual.

## Salidas

- `existing_valid_pages(bronze_dir) -> set[int]`.
- `pages_to_fetch(total_pages, bronze_dir) -> list[int]` — rango `1..total_pages` menos las ya
  completas, en orden ascendente.

## Invariantes

Ninguna INV-* de datos directa; hace posible REQ-B6 sin duplicar la lógica de nomenclatura de
`bronze-batch-writer` (reutiliza el mismo patrón `anime_catalog_batch_{page:04d}.json`).

## Procedimiento

1. Listar los archivos de `bronze_dir` que calzan con el patrón `anime_catalog_batch_NNNN.json`.
2. Para cada uno, intentar parsear como JSON y verificar que tiene la forma del sobre de Bronze
   (`records`, `source_page`). Un archivo corrupto o a medio escribir no cuenta como válido.
3. Devolver el complemento de ese conjunto contra `1..total_pages`.

## Criterios de aceptación

- Con 5 de 20 páginas ya presentes y válidas, `pages_to_fetch(20, dir)` devuelve exactamente las
  15 restantes, sin incluir ninguna de las 5 ya hechas (Prueba de Reanudación).
- Un archivo `.json.tmp` huérfano (escritura interrumpida) no cuenta como página completa.

## Errores y modos de fallo

- Un archivo con nombre válido pero JSON corrupto se trata como página pendiente, no como error
  fatal: se vuelve a descargar en la siguiente corrida.
