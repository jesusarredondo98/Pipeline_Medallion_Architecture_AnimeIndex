---
name: http-retry-policy
description: Usar cuando se necesite decidir si una respuesta HTTP fallida debe reintentarse y con qué espera, sin conocer el dominio de la petición.
---

## Responsabilidad

Clasificar la respuesta HTTP (o excepción de transporte) y decidir el reintento: `429` →
`Retry-After`; `403` de indisponibilidad y `5xx` → backoff exponencial con jitter, máximo 4
intentos; cualquier otro código → no reintentar.

## Requerimientos que satisface

- REQ-B3.

## Entradas

- `make_request: Callable[[], httpx.Response]` — closure que ejecuta una única petición (provista
  por el orquestador de Bronze, que a su vez usa `anilist-graphql-client`).
- `RetryPolicyConfig(max_attempts=4, sleep_fn=time.sleep, rng=random.Random())` — inyectables para
  pruebas deterministas.
- `on_response: Callable[[httpx.Response], None]` opcional — invocado con cada respuesta recibida
  (incluidas las que se van a reintentar), para que el orquestador conecte `rate-limit-governor`
  sin que esta skill importe esa otra skill (sin acoplamiento cruzado).

## Salidas

- `execute_with_retry(...)` → `httpx.Response` con status `200` en éxito.
- Excepción `RetriesExhausted(last_response, last_exception)` si se agotan los 4 intentos.

## Invariantes

Ninguna INV-* de datos directa; es la puerta que hace posible P4 ("fallar suave en ingesta") sin
que el llamador tenga que implementar backoff a mano.

## Procedimiento

1. Ejecutar `make_request()`.
2. Si lanza `httpx.RequestError` (error de red): tratar como retryable, backoff exponencial+jitter.
3. Si `status == 200`: devolver inmediatamente.
4. Si `status == 429`: dormir `Retry-After` segundos (header, default 1s si ausente) y reintentar.
5. Si `status == 403` con el mensaje de indisponibilidad de AniList, o `5xx`: backoff exponencial
   con jitter (`2**intento + uniform(0,1)`).
6. Cualquier otro código: devolver la respuesta tal cual, sin reintentar — el llamador decide
   (p. ej. un `200` con `errors` en el cuerpo se valida en `anilist-graphql-client`, no aquí).
7. Al agotar `max_attempts` (4): lanzar `RetriesExhausted` con la última respuesta/excepción.

## Criterios de aceptación

- Ante `429` con `Retry-After: 5`, `sleep_fn` se invoca con `5.0`, no con un valor de backoff
  calculado (Prueba de Resiliencia).
- Ante 4 respuestas `5xx` consecutivas, se lanza `RetriesExhausted` y `sleep_fn` se invocó 3 veces
  (entre los 4 intentos) con valores crecientes.
- Un `200` con `errors` en el cuerpo nunca llega a esta skill como fallo — llega como éxito de
  transporte (200) y se rechaza en la capa de parseo, no aquí (INV-8).

## Errores y modos de fallo

- No reintenta indefinidamente bajo ninguna configuración: `max_attempts` es obligatorio y finito.
- No decide qué hacer con `RetriesExhausted` — eso es responsabilidad de `failed-pages-ledger`.
