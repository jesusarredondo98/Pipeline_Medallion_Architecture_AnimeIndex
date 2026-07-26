"""Emite las 6 métricas de REQ-S4, leyendo filas_nuevas/filas_actualizadas DIRECTAMENTE del
resultado de merge().execute() — nunca recalculadas a mano en Polars (Agents.md §6, trampa
conocida: duplicar esa lógica agrega bugs)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SilverRunMetrics:
    filas_leidas: int
    filas_validas: int
    filas_en_cuarentena: int
    filas_nuevas: int
    filas_actualizadas: int
    filas_totales_silver: int

    def as_dict(self) -> dict:
        return {
            "filas_leidas": self.filas_leidas,
            "filas_validas": self.filas_validas,
            "filas_en_cuarentena": self.filas_en_cuarentena,
            "filas_nuevas": self.filas_nuevas,
            "filas_actualizadas": self.filas_actualizadas,
            "filas_totales_silver": self.filas_totales_silver,
        }


def build_metrics(
    filas_leidas: int,
    filas_validas: int,
    filas_en_cuarentena: int,
    merge_result: dict,
    filas_totales_silver: int,
) -> SilverRunMetrics:
    """`merge_result` es el dict crudo devuelto por `delta_merge_upsert.upsert(...)`."""
    return SilverRunMetrics(
        filas_leidas=filas_leidas,
        filas_validas=filas_validas,
        filas_en_cuarentena=filas_en_cuarentena,
        filas_nuevas=merge_result["num_target_rows_inserted"],
        filas_actualizadas=merge_result["num_target_rows_updated"],
        filas_totales_silver=filas_totales_silver,
    )
