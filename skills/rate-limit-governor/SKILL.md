---
name: rate-limit-governor
description: Usar cuando se necesite regular el ritmo de peticiones secuenciales a AniList antes y después de cada llamada.
---

## Responsabilidad

Regular el ritmo de peticiones a AniList: pausa base ≥ 1s entre peticiones y frenado proactivo
leyendo `X-RateLimit-Remaining`, deteniéndose antes de tocar el límite.

## Requerimientos que satisface

- REQ-B5.
- INV-5 (sin paralelismo).

## Entradas

- `pausa_base: float` (default 1.0s).
- `umbral_remaining: int` (default 10).
- `sleep_fn`, `monotonic_fn`, `epoch_fn` — inyectables, para pruebas deterministas sin esperar
  tiempo real (`resilience-test-kit` los sustituye por dobles de prueba).

## Salidas

- `wait_before_request()` — bloquea hasta cumplir la pausa base desde la última petición.
- `observe_response_headers(headers)` — registra el instante de la petición y, si
  `X-RateLimit-Remaining < umbral_remaining`, duerme hasta `X-RateLimit-Reset`.

## Invariantes

- INV-5: la skill no expone ningún mecanismo de concurrencia; su contrato es explícitamente
  secuencial (una instancia, una petición a la vez).

## Procedimiento

1. Antes de cada petición: `wait_before_request()`.
2. Ejecutar la petición (delegada a `anilist-graphql-client`).
3. Después de cada respuesta, exitosa o no: `observe_response_headers(response.headers)` — el
   frenado proactivo debe aplicarse incluso en respuestas de error, porque los headers de
   rate-limit vienen en toda respuesta.

## Criterios de aceptación

- Con `pausa_base=1.0`, dos llamadas consecutivas a `wait_before_request()` sin frenado adicional
  distan ≥ 1.0s entre sí (medible con `monotonic_fn` inyectado en la prueba).
- Con `X-RateLimit-Remaining` por debajo del umbral, `observe_response_headers` duerme antes de
  que ocurra un 429 (verificado por `resilience-test-kit`, Prueba de Ritmo Proactivo).

## Errores y modos de fallo

- Si los headers de rate-limit no vienen en la respuesta, no frena de más: aplica sólo la pausa
  base y continúa.
- Nunca reduce la pausa por debajo de `pausa_base` sin importar el valor de `Remaining`.
