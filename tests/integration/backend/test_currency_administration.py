"""Real migration / catalog / local permission / warrant REST boundary on disposable DBs."""

import asyncio
import json

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from tests.integration.backend.test_usd_chf_currency_references import (
    _client,
    _migrate,
    _product_payload,
)
from tests.integration.backend.test_usd_chf_currency_references import (
    currency_database as base_currency_database,
)

from app.features.market.service.currency_administration import (
    CurrencyAdministrationService,
)
from app.features.market.service.currency_catalog_contract import bundled_catalog


@pytest.fixture
def currency_database():
    yield from base_currency_database.__wrapped__()


BASE = "/api/v1/market-reference-data/currencies"


async def _rows(url):
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            return (await connection.execute(text("SELECT * FROM currencies ORDER BY code"))).all()
    finally:
        await engine.dispose()


async def _import(client, document=None):
    payload = {"catalog_json": json.dumps(document)} if document else {}
    response = await client.post(BASE + "/catalog/preview", json=payload)
    assert response.status_code == 200, response.text
    preview = response.json()
    result = await client.post(
        BASE + "/catalog/import",
        json={
            **payload,
            "expected_preview_token": preview["preview_token"],
            "reviewed": True,
        },
        headers={"X-Actor-Name": "Currency integration operator"},
    )
    assert result.status_code == 200, result.text
    return preview, result.json()


async def _row(client, code):
    response = await client.get(BASE + "/admin")
    assert response.status_code == 200, response.text
    return next(row for row in response.json()["items"] if row["code"] == code)


def test_catalog_import_never_enables_and_activation_preserves_warrant_history(
    currency_database,
):
    _migrate(currency_database, "head")

    async def exercise():
        before = await _rows(currency_database)
        async with _client(currency_database) as client:
            empty = (await client.get(BASE + "/admin")).json()
            assert empty["catalog"] is None
            assert {row["code"] for row in empty["items"]} == {"EUR", "USD", "CHF"}
            preview = await client.post(BASE + "/catalog/preview", json={})
            assert preview.status_code == 200
            token = preview.json()["preview_token"]
            unreviewed = await client.post(
                BASE + "/catalog/import",
                json={"expected_preview_token": token, "reviewed": False},
            )
            assert unreviewed.status_code == 422
            assert (await client.get(BASE + "/admin")).json() == empty
            _, imported = await _import(client)
            assert imported["applied"] is True
            assert await _rows(currency_database) == before
            _, repeated = await _import(client)
            assert repeated["applied"] is False
            assert len((await client.get(BASE + "/admin/history")).json()["items"]) == 1
            payload = await _product_payload(client)
            for code in ("GBP", "JPY", "KWD"):
                row = await _row(client, code)
                assert not row["local_exists"] and row["can_activate"]
                body = {"expected_token": row["state_token"]}
                activated = await client.post(BASE + f"/{code}/activate", json=body)
                assert activated.status_code == 200, activated.text
                old_token = await client.post(BASE + f"/{code}/deactivate", json=body)
                assert old_token.status_code == 409
                active_row = await _row(client, code)
                same = await client.post(
                    BASE + f"/{code}/activate",
                    json={"expected_token": active_row["state_token"]},
                )
                assert same.json()["changed"] is False
                created = await client.post(
                    "/api/v1/warrants", json={**payload, "strike_currency_code": code}
                )
                assert created.status_code == 201, created.text
                history_url = f"/api/v1/warrants/{created.json()['id']}/terms"
                history = (await client.get(history_url)).json()
                assert history[0]["strike_currency_code"] == code
                deactivated = await client.post(
                    BASE + f"/{code}/deactivate",
                    json={"expected_token": active_row["state_token"]},
                )
                assert deactivated.status_code == 200
                assert (await client.get(history_url)).json() == history
                rejected = await client.post(
                    "/api/v1/warrants", json={**payload, "strike_currency_code": code}
                )
                assert rejected.status_code == 422, rejected.text
                current = await _row(client, code)
                assert current["local_exists"] and not current["is_active"]
                response = await client.post(
                    BASE + f"/{code}/activate",
                    json={"expected_token": current["state_token"]},
                )
                assert response.status_code == 200
            refs = {r["code"]: r for r in (await client.get(BASE)).json()["items"]}
            assert refs["JPY"]["minor_unit"] == 0
            assert refs["KWD"]["minor_unit"] == 3
            audit = (await client.get(BASE + "/admin/history")).json()["items"]
            assert len(audit) == 10
            assert audit[-1]["actor"] == "Currency integration operator"

    asyncio.run(exercise())


def test_conflicts_stale_import_and_omission_never_overwrite_local_data(
    currency_database,
):
    _migrate(currency_database, "head")

    async def exercise():
        engine = create_async_engine(currency_database, poolclass=NullPool)
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "UPDATE currencies SET name='Local dollar', "
                        "is_active=false WHERE code='USD'"
                    )
                )
                await connection.execute(
                    text("UPDATE currencies SET minor_unit=3, is_active=false WHERE code='CHF'")
                )
            before = await _rows(currency_database)
            async with _client(currency_database) as client:
                old = (await client.post(BASE + "/catalog/preview", json={})).json()
                doc = bundled_catalog().document()
                doc["version"] = "LOCAL-REVIEWED-V2"
                await _import(client, doc)
                assert await _rows(currency_database) == before
                usd, chf = await _row(client, "USD"), await _row(client, "CHF")
                assert usd["name"] == "Local dollar" and usd["can_activate"]
                assert chf["minor_unit_conflict"] and not chf["can_activate"]
                rejected = await client.post(
                    BASE + "/CHF/activate", json={"expected_token": chf["state_token"]}
                )
                assert rejected.status_code == 409
                stale = await client.post(
                    BASE + "/catalog/import",
                    json={
                        "expected_preview_token": old["preview_token"],
                        "reviewed": True,
                    },
                )
                assert stale.status_code == 409
                changed = json.loads(json.dumps(doc))
                changed["entries"][0]["name"] = "Changed name"
                conflict = await client.post(
                    BASE + "/catalog/preview",
                    json={"catalog_json": json.dumps(changed)},
                )
                assert conflict.status_code == 409
                # Removing an entry from a reviewed subset is not a deactivation command.
                doc["version"] = "LOCAL-REVIEWED-V3"
                doc["entries"] = [r for r in doc["entries"] if r["code"] != "EUR"]
                preview, _ = await _import(client, doc)
                assert any(
                    r["code"] == "EUR" and r["change"] == "NOT_IN_NEW_CATALOG"
                    for r in preview["changes"]
                )
                eur = await _row(client, "EUR")
                assert eur["is_active"] and not eur["catalog_available"]
                assert await _rows(currency_database) == before
                doc["version"] = "OLD-SOURCE"
                doc["source_published_on"] = "2020-01-01"
                assert (
                    await client.post(
                        BASE + "/catalog/preview",
                        json={"catalog_json": json.dumps(doc)},
                    )
                ).status_code == 409
                invalid = await client.post(BASE + "/catalog/preview", json={"catalog_json": "[]"})
                assert invalid.status_code == 422
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_concurrent_activation_has_one_winner(currency_database):
    _migrate(currency_database, "head")

    async def exercise():
        async with _client(currency_database) as client:
            await _import(client)
            row = await _row(client, "GBP")
            responses = await asyncio.gather(
                *[
                    client.post(
                        BASE + "/GBP/activate",
                        json={"expected_token": row["state_token"]},
                    )
                    for _ in range(2)
                ]
            )
            assert sorted(r.status_code for r in responses) == [200, 409]
            assert len((await client.get(BASE + "/admin/history")).json()["items"]) == 2

    asyncio.run(exercise())


def test_failed_audit_rolls_back_catalog_and_currency_writes(currency_database, monkeypatch):
    _migrate(currency_database, "head")

    async def exercise():
        def fail(*args, **kwargs):
            raise RuntimeError("audit storage unavailable")

        async with _client(currency_database) as client:
            with monkeypatch.context() as scope:
                scope.setattr(CurrencyAdministrationService, "_audit", fail)
                with pytest.raises(RuntimeError, match="audit storage"):
                    await _import(client)
            assert (await client.get(BASE + "/admin")).json()["catalog"] is None
            await _import(client)
            row = await _row(client, "GBP")
            with monkeypatch.context() as scope:
                scope.setattr(CurrencyAdministrationService, "_audit", fail)
                with pytest.raises(RuntimeError, match="audit storage"):
                    await client.post(
                        BASE + "/GBP/activate",
                        json={"expected_token": row["state_token"]},
                    )
            assert not (await _row(client, "GBP"))["local_exists"]

    asyncio.run(exercise())
