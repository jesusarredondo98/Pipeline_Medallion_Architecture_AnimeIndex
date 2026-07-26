---
name: resilience-test-kit
description: Usar para construir las pruebas de resiliencia de Bronze (429, ritmo proactivo, reanudación) sin golpear la red real.
---

## Responsabilidad

Simular `429` con `Retry-After`; simular `X-RateLimit-Remaining` bajo umbral y verificar
frenado anticipado; simular extracción parcial 5/20 e interrupción, verificando reanudación sin
re-descarga.

## Requerimientos que satisface

- Prueba de Resiliencia, Prueba de Ritmo Proactivo, Prueba de Reanudación (PRD §4).
- REQ-B3, REQ-B5, REQ-B6.

## Entradas

Ninguna externa: construye sus propios dobles de prueba.

## Salidas

- `make_page_body(page, per_page, num_records, has_next_page)` — cuerpo `data.Page` válido.
- `json_response(status_code, body, headers)` — `httpx.Response` cruda para pruebas.
- `scripted_handler(responses, calls_log)` — handler para `httpx.MockTransport` que devuelve una
  secuencia programada de respuestas y registra las peticiones realizadas.

## Invariantes

No aplica: es infraestructura de prueba, no toca `/bronze` real salvo que la prueba se lo pida
explícitamente sobre un directorio temporal (`tmp_path` de pytest).

## Procedimiento

1. Programar una secuencia de respuestas (`[429 con Retry-After, 200 con datos]`, o
   `[200 con Remaining bajo umbral]`, etc.).
2. Instanciar `httpx.Client(transport=httpx.MockTransport(scripted_handler(...)))`.
3. Ejecutar el componente bajo prueba (`http_retry_policy.execute_with_retry`,
   `rate_limit_governor.RateLimitGovernor`, o `bronze_pipeline.run_bronze` completo) contra ese
   cliente.
4. Verificar el número de llamadas realizadas (`calls_log`) y los argumentos con que se invocó
   `sleep_fn` (inyectado, nunca tiempo real).

## Criterios de aceptación

- Ver `tests/test_resilience.py`: assunciones concretas por cada prueba del PRD §4.

## Errores y modos de fallo

- Si el componente bajo prueba pide más respuestas de las programadas, `scripted_handler` lanza
  `AssertionError` inmediatamente — nunca golpea la red real por accidente.
