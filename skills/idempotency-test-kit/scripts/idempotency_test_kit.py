"""Aserciones reutilizables para las pruebas de idempotencia de Silver y Gold (PRD §4)."""

from __future__ import annotations


def assert_silver_idempotent(metrics_segunda_corrida, total_antes: int, total_despues: int) -> None:
    """Criterio de aceptación de REQ-S4: segunda corrida del mismo lote produce
    filas_nuevas=0, filas_actualizadas=0, sin cambio en filas_totales_silver."""
    assert metrics_segunda_corrida.filas_nuevas == 0, (
        f"esperaba 0 filas_nuevas en la 2a corrida, obtuve {metrics_segunda_corrida.filas_nuevas}"
    )
    assert metrics_segunda_corrida.filas_actualizadas == 0, (
        f"esperaba 0 filas_actualizadas en la 2a corrida, obtuve {metrics_segunda_corrida.filas_actualizadas}"
    )
    assert total_antes == total_despues, (
        f"filas_totales_silver cambió: {total_antes} -> {total_despues}"
    )


def assert_gold_no_growth(vector_count_antes: int, vector_count_despues: int) -> None:
    """REQ-G4: reconstruir el índice sin cambios en Silver produce 0 embeddings nuevos."""
    assert vector_count_antes == vector_count_despues, (
        f"el índice creció sin cambios en Silver: {vector_count_antes} -> {vector_count_despues}"
    )
