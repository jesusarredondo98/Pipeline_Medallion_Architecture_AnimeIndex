"""Prueba de Contrato (PRD §4): JSON malformado debe enrutarse a cuarentena con el
motivo_rechazo correcto, nunca colarse a Silver."""

from __future__ import annotations

from pathlib import Path

import anime_data_contract
import contract_test_kit as ctk
import html_description_normalizer as normalizer
import quarantine_writer


def _validate(raw: dict, min_desc_len: int = 50):
    cleaned = normalizer.clean_description(raw.get("description"))
    return anime_data_contract.validate_record(raw, cleaned, min_desc_len)


def test_registro_valido_pasa_el_contrato():
    raw = ctk.make_valid_raw_record(id=1, description_len=80)
    record = _validate(raw)
    assert record.id == 1
    assert record.title_romaji == "Anime de prueba"


def test_id_ausente_va_a_cuarentena(tmp_path: Path):
    raw = ctk.make_record_missing_id()
    try:
        _validate(raw)
        assert False, "debía lanzar ContractViolation"
    except anime_data_contract.ContractViolation as exc:
        assert "id" in exc.motivo_rechazo.lower()
        path = quarantine_writer.write_quarantine(tmp_path, exc.motivo_rechazo, exc.original_payload)
        entries = quarantine_writer.read_quarantine(tmp_path)
        assert path.exists()
        assert len(entries) == 1
        assert entries[0]["motivo_rechazo"] == exc.motivo_rechazo
        assert entries[0]["payload_original"] == raw  # payload original íntegro (INV-7)


def test_description_vacia_va_a_cuarentena_con_motivo_de_longitud(tmp_path: Path):
    raw = ctk.make_record_with_empty_description()
    try:
        _validate(raw, min_desc_len=50)
        assert False, "debía lanzar ContractViolation"
    except anime_data_contract.ContractViolation as exc:
        assert "50" in exc.motivo_rechazo  # motivo específico de longitud, no genérico
        quarantine_writer.write_quarantine(tmp_path, exc.motivo_rechazo, exc.original_payload)

    entries = quarantine_writer.read_quarantine(tmp_path)
    assert len(entries) == 1
    assert entries[0]["payload_original"]["description"] == ""


def test_idmal_nulo_no_rechaza_el_registro():
    """INV-3: idMal es opcional, nunca se usa como llave ni se exige."""
    raw = ctk.make_valid_raw_record(id=42)
    assert raw["idMal"] is None
    record = _validate(raw)
    assert record.id_mal is None
