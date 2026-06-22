"""Unit tests for the pure CSV parse/validate function (no DB, no embeddings)."""

import pytest

from app.services.import_service import parse_csv

HEADER = "id,title,content,author,category,published_at"


def _csv(*lines: str) -> bytes:
    return ("\n".join([HEADER, *lines]) + "\n").encode("utf-8")


def test_valid_rows_parsed():
    raw = _csv(
        "1,Title A,Body about backend systems,Alice,Backend,2024-01-02 03:04:05",
        "2,Title B,Body about ml models,Bob,AI/ML,2024-05-06 07:08:09",
    )
    valid, errors, total = parse_csv(raw)
    assert total == 2
    assert errors == []
    assert len(valid) == 2
    assert valid[0]["legacy_id"] == 1
    assert valid[0]["category"] == "Backend"
    assert valid[0]["published_at"].year == 2024


def test_missing_required_field():
    raw = _csv("1,,Body,Alice,Backend,2024-01-01 00:00:00")
    valid, errors, total = parse_csv(raw)
    assert len(valid) == 0
    assert len(errors) == 1
    assert errors[0].row == 2
    assert "missing required" in errors[0].error


def test_invalid_category_rejected():
    raw = _csv("1,T,Body,Alice,Marketing,2024-01-01 00:00:00")
    valid, errors, _ = parse_csv(raw)
    assert not valid
    assert "invalid category" in errors[0].error


def test_invalid_id_rejected():
    raw = _csv("abc,T,Body,Alice,Backend,2024-01-01 00:00:00")
    valid, errors, _ = parse_csv(raw)
    assert not valid
    assert "invalid id" in errors[0].error


def test_duplicate_id_within_file():
    raw = _csv(
        "5,First,Body one,Alice,Backend,2024-01-01 00:00:00",
        "5,Second,Body two,Bob,AI/ML,2024-02-02 00:00:00",
    )
    valid, errors, _ = parse_csv(raw)
    assert len(valid) == 1  # first kept
    assert len(errors) == 1
    assert "duplicate id 5" in errors[0].error


def test_missing_header_column_raises():
    raw = b"title,content\nT,Body\n"
    with pytest.raises(ValueError, match="missing required column"):
        parse_csv(raw)


def test_published_at_defaults_when_blank():
    raw = _csv("1,T,Body,Alice,Backend,")
    valid, errors, _ = parse_csv(raw)
    assert len(valid) == 1
    assert valid[0]["published_at"] is not None  # defaulted to now()


def test_blank_id_allowed_as_null_legacy():
    raw = _csv(",T,Body,Alice,Backend,2024-01-01 00:00:00")
    valid, errors, _ = parse_csv(raw)
    assert len(valid) == 1
    assert valid[0]["legacy_id"] is None


def test_utf8_bom_handled():
    raw = ("﻿" + HEADER + "\n1,T,Body,Alice,Backend,2024-01-01 00:00:00\n").encode("utf-8")
    valid, errors, total = parse_csv(raw)
    assert total == 1 and len(valid) == 1
