"""A document describes bounded product units, never inferred terms validity or adjustments."""

from datetime import timedelta

import pytest
from pydantic import TypeAdapter, ValidationError
from tests.unit.backend.features.product import (
    test_price_scale_evidence_service as examples,
)

from app.core.exceptions import ApplicationError
from app.features.product.domain.price_scale_evidence import (
    MAX_DOCUMENT_BYTES,
    MAX_MANIFEST_BYTES,
    ProductPriceScaleManifest,
)
from app.features.product.service.price_scale_evidence import validate_import


@pytest.mark.parametrize(
    "change",
    [
        {"axis": "UNDERLYING"},
        {"unit": "CENTS_PER_WARRANT"},
        {"unit": "WARRANTS_PER_UNDERLYING"},
        {"currency": "eur"},
        {"currency": "EU"},
        {"currency": "€UR"},
        {"status": "VERIFIED_ADJUSTED"},
        {"schema_version": "unapproved-v2"},
        {"valid_from": "2026-10-01T00:00:00"},
        {"valid_until": "2026-12-01T00:00:00"},
        {"valid_from": "2026-12-02T00:00:00+01:00"},
        {"valid_until": "2026-10-01T00:00:00+02:00"},
        {"valid_until": "9999-12-31T23:59:59+00:00"},
        {"source_published_at": "2026-09-30T11:00:00"},
        {"source_published_at": "2026-09-30T11:00:00+02:00"},  # Cannot also keep published_on.
        {"source_reference": " "},
        {"scale_id": " "},
        {"source_version": " "},
        {"source_document_sha256": "A" * 64},
        {"source_document_sha256": "0" * 63},
        {"adjustment_factor": "0.5"},
        {"verified": True},
        {"automatic_activation": True},
    ],
)
def test_unsupported_or_implicit_facts_cannot_become_a_scale(change):
    with pytest.raises(ValidationError):
        TypeAdapter(ProductPriceScaleManifest).validate_python(examples.manifest(**change))


@pytest.mark.parametrize("isin", ["DE000VH2LU2", "de000vh2lu21", "XX!00VH2LU21", "DE000VH2LU2X"])
def test_original_product_binding_requires_exact_isin(isin):
    value = examples.manifest(binding=examples.manifest()["binding"] | {"isin": isin})
    with pytest.raises(ValidationError):
        TypeAdapter(ProductPriceScaleManifest).validate_python(value)


@pytest.mark.parametrize(
    "change",
    [
        {"document_sha256": "0" * 64},
        {"manifest_sha256": "0" * 64},
        {"document_base64": "not base64"},
        {"document_base64": ""},
        {"document_base64": "A" * (((MAX_DOCUMENT_BYTES + 2) // 3) * 4 + 1)},
        {"manifest_json": "a" * (MAX_MANIFEST_BYTES + 1)},
        {"document_filename": "../private.txt"},
        {"document_filename": "folder\\source.pdf"},
        {"document_filename": "x\x00y"},
        {"document_filename": " "},
        {"document_media_type": "application/octet-stream"},
        {"review_reference": " "},
        {"reviewed_at": examples.NOW + timedelta(microseconds=1)},
        {"reviewed_at": examples.NOW.replace(tzinfo=None)},
        {"retrieved_at": examples.NOW + timedelta(microseconds=1)},
        {"retrieved_at": examples.NOW.replace(tzinfo=None)},
    ],
)
def test_import_requires_original_bytes_hashes_and_separate_known_clocks(change):
    with pytest.raises(ApplicationError) as captured:
        validate_import(examples.command(**change), examples.NOW)
    assert captured.value.code == "PRODUCT_PRICE_SCALE_INVALID"


@pytest.mark.parametrize(
    "change",
    [
        {"source_document_sha256": "0" * 64},
        {"source_published_on": "2026-11-20"},
        {
            "source_published_on": None,
            "source_published_at": "2026-11-16T10:00:01+00:00",
        },
        {"valid_from": 1790805600},
        {"valid_until": 1796079600},
        {"source_published_on": None, "source_published_at": 1790805600},
        {"source_published_on": 1790726400},
        {"source_published_on": "20260930"},
        {"source_published_on": "2026-09-30T00:00:00Z"},
        {"source_published_on": "2026-09-31"},
        {"valid_from": "2026-10-01T00:00:00+0200"},
        {"valid_until": "2026-12-01T00:00:00+01"},
        {"source_published_on": None, "source_published_at": "2026-09-30T11:00:00+0200"},
    ],
)
def test_no_foreign_document_future_publication_or_epoch_invented_original_text(change):
    with pytest.raises(ApplicationError):
        validate_import(examples.command(examples.manifest(**change)), examples.NOW)


@pytest.mark.parametrize(
    "raw",
    [
        '{"status": "UNCHANGED_ORIGINAL", "status": "WITHDRAWN"}',
        '{"nested": {"key": 1, "key": 2}}',
        '{"not_json": NaN}',
        "[]",
        "null",
        "{broken}",
    ],
)
def test_duplicate_keys_invalid_constants_and_wrong_json_shape_are_not_silently_normalized(
    raw,
):
    with pytest.raises(ApplicationError):
        validate_import(
            examples.command(manifest_json=raw, manifest_sha256=examples.digest(raw.encode())),
            examples.NOW,
        )


def test_date_precision_and_explicit_future_interval_claim_remain_distinct_from_verification():
    manifest, document = validate_import(examples.command(), examples.NOW)
    assert document == examples.DOCUMENT
    assert manifest.source_published_at is None
    assert manifest.source_published_on.isoformat() == "2026-09-30"
    assert manifest.valid_until > examples.NOW
    assert manifest.valid_from.isoformat() == "2026-10-01T00:00:00+02:00"
    assert manifest.valid_until.isoformat() == "2026-12-01T00:00:00+01:00"


def test_equal_instants_with_different_offsets_are_an_empty_interval():
    value = examples.manifest(
        valid_from="2026-10-01T00:00:00+02:00", valid_until="2026-09-30T22:00:00+00:00"
    )
    with pytest.raises(ApplicationError):
        validate_import(examples.command(value), examples.NOW)


def test_explicit_adjustment_and_withdrawal_are_preserved_without_any_factor():
    for status in ("ADJUSTMENT_REQUIRED", "WITHDRAWN"):
        manifest, _ = validate_import(
            examples.command(examples.manifest(status=status)), examples.NOW
        )
        assert manifest.status == status
        assert not hasattr(manifest, "adjustment_factor")
