from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def _constraints(
    session: AsyncSession,
    table: str,
) -> dict[str, str]:
    rows = await session.execute(
        text(
            """
            select c.conname, pg_get_constraintdef(c.oid, true)
            from pg_constraint c
            join pg_class t on t.oid = c.conrelid
            where t.relname = :table
            """
        ),
        {"table": table},
    )
    return {row[0]: row[1] for row in rows}


async def test_trade_link_current_version_fk_is_deferred_same_aggregate(
    learning_session: AsyncSession,
) -> None:
    row = (
        await learning_session.execute(
            text(
                """
                select c.condeferrable, c.condeferred,
                       pg_get_constraintdef(c.oid, true)
                from pg_constraint c
                join pg_class t on t.oid = c.conrelid
                where t.relname = 'external_observation_trade_links'
                  and c.conname =
                      'fk_ext_obs_trade_links_current_version_same_link'
                """
            )
        )
    ).one()
    assert row[0] is True
    assert row[1] is True
    assert "current_version_id" in row[2]
    assert "external_observation_trade_link_id" in row[2]


async def test_trade_link_version_status_and_reasons_are_constrained(
    learning_session: AsyncSession,
) -> None:
    constraints = await _constraints(
        learning_session,
        "external_observation_trade_link_versions",
    )
    checks = [value for value in constraints.values() if value.startswith("CHECK")]
    assert any("ACTIVE" in value and "RETRACTED" in value for value in checks)
    assert any(
        "INITIAL_LINK" in value
        and "TARGET_CORRECTED" in value
        and "LINK_RETRACTED" in value
        and "LINK_REACTIVATED" in value
        and "LINK_REACTIVATED_WITH_TARGET_CORRECTION" in value
        and "SOURCE_REVALIDATED" in value
        for value in checks
    )


async def test_trade_link_v1_initial_link_check_exists(
    learning_session: AsyncSession,
) -> None:
    constraints = await _constraints(
        learning_session,
        "external_observation_trade_link_versions",
    )
    checks = [value for value in constraints.values() if value.startswith("CHECK")]
    assert any(
        "version" in value and "INITIAL_LINK" in value and "supersedes_version_id" in value
        for value in checks
    )


async def test_trade_link_linear_support_uniques_exist(
    learning_session: AsyncSession,
) -> None:
    constraints = await _constraints(
        learning_session,
        "external_observation_trade_link_versions",
    )
    definitions = list(constraints.values())
    assert any(
        "UNIQUE (external_observation_trade_link_id, version)" in value for value in definitions
    )
    assert any("UNIQUE (id, external_observation_trade_link_id)" in value for value in definitions)
