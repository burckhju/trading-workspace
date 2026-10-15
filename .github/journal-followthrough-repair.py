from pathlib import Path
import subprocess

base = '85be220fdef6b21d27e1d3909e99d11a13b274cc'
helpers = {'.github/journal-followthrough-repair.py', '.github/workflows/journal-followthrough.yml'}
assert set(subprocess.check_output(['git', 'diff', '--name-only', base, 'HEAD'], text=True).splitlines()) == helpers

def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)

p = Path('tests/integration/backend/learning/test_journal_write_postgres.py')
s = p.read_text()
s = replace_once(s, '''async def closed(client):
    pid = await product(client)
    bought = await client.post(BASE + "/purchases/external", json=purchase(pid))
''', '''async def planned_purchase(client, pid):
    """Create every provenance parent through its owner, not a SQL reassignment."""
    response = await client.get(f"/api/v1/warrants/{pid}")
    assert response.status_code == 200, response.text
    underlying_id = response.json()["underlying_id"]
    response = await client.get("/api/v1/market-reference-data/trading-venues")
    assert response.status_code == 200, response.text
    venue = next(v for v in response.json()["items"] if v["mic"] == "XETR")
    response = await client.post(
        f"/api/v1/warrants/{pid}/listings",
        json={"trading_venue_id": venue["id"], "quotation_currency_code": "EUR"},
    )
    assert response.status_code == 201, response.text
    response = await client.post(
        "/api/v1/trade-plans",
        json={
            "origin_type": "MANUAL",
            "underlying_id": underlying_id,
            "thesis": "Synthetic planned journal and retention qualification",
            "entry": {"type": "PRICE", "currency": "EUR", "price": "100"},
            "invalidation": {"stop_price": "95"},
            "targets": [{"sequence": 1, "price": "110"}],
            "risk_assumptions": {"thesis_risk": "Synthetic risk, not a trading recommendation"},
        },
    )
    assert response.status_code == 201, response.text
    plan = response.json()
    version_url = f"/api/v1/trade-plans/{plan['plan']['id']}/versions/{plan['latest_version']['id']}"
    for action in ("submit-review", "approve"):
        response = await client.post(f"{version_url}/{action}")
        assert response.status_code == 200, response.text
    response = await client.post(
        "/api/v1/product-selection-runs",
        json={
            "trade_plan_id": plan["plan"]["id"],
            "trade_plan_version_id": plan["latest_version"]["id"],
        },
    )
    assert response.status_code == 201, response.text
    run = response.json()
    assert len(run["evaluations"]) == 1
    evaluation = run["evaluations"][0]
    assert evaluation["warrant_id"] == pid
    assert evaluation["eligibility_status"] == "NOT_EVALUABLE"
    response = await client.post(
        f"/api/v1/product-selection-runs/{run['run']['id']}/selection",
        json={
            "product_evaluation_id": evaluation["id"],
            "rationale": "Synthetic confirmed execution; missing quotes remain missing.",
        },
    )
    assert response.status_code == 201, response.text
    selected = response.json()
    assert selected["evaluations"] == run["evaluations"]
    payload = purchase(pid)
    del payload["product_id"]
    payload["product_selection_id"] = selected["selection"]["id"]
    bought = await client.post(BASE + "/purchases/from-selection", json=payload)
    assert bought.status_code == 201, bought.text
    trade = bought.json()["trade"]
    assert trade["origin"] == "WORKSPACE_SELECTION"
    assert trade["trade_plan_id"] == plan["plan"]["id"]
    assert trade["trade_plan_version_id"] == plan["latest_version"]["id"]
    assert trade["product_selection_id"] == selected["selection"]["id"]
    assert trade["product_evaluation_id"] == evaluation["id"]
    return bought


async def closed(client, *, planned=False):
    pid = await product(client)
    bought = (
        await planned_purchase(client, pid)
        if planned
        else await client.post(BASE + "/purchases/external", json=purchase(pid))
    )
''')
s = replace_once(s, '''            tid, listing, sale, pid = await closed(client)
            await seed_prices''', '''            tid, listing, sale, pid = await closed(client, planned=True)
            response = await client.get(f"{BASE}/trades/{tid}")
            assert response.status_code == 200, response.text
            original_trade = response.json()
            plan = original_trade["trade_plan_id"]
            assert plan is not None and original_trade["origin"] == "WORKSPACE_SELECTION"
            await seed_prices''')
start = s.index('            # Add a synthetic parent link solely')
end = s.index('            blocked = await client.delete', start)
s = s[:start] + '''            # The actual planned capture already owns this parent; never rewrite origin.
            assert (await client.get(f"{BASE}/trades/{tid}")).json() == original_trade
            plan_before = (await client.get(f"/api/v1/trade-plans/{plan}")).json()
''' + s[end:]
s = replace_once(s, '''            ), blocked.text
            assert (await client.get(f"{LEARN}/lessons/{lid}")).json() == old_lesson''', '''            ), blocked.text
            assert (await client.get(f"{BASE}/trades/{tid}")).json() == original_trade
            assert (await client.get(f"/api/v1/trade-plans/{plan}")).json() == plan_before
            assert (await client.get(f"{LEARN}/lessons/{lid}")).json() == old_lesson''')
p.write_text(s)
p = Path('tests/e2e/post-trade-journal-postgres.spec.ts')
s = replace_once(p.read_text(), '// Requires the separately identified CI Compose stack', '// Match the canonical origin used by the existing real-write browser cases.\ntest.use({ baseURL: "http://localhost:8080" });\n\n// Requires the separately identified CI Compose stack')
s = replace_once(s, 'expect(baseURL).toBe("http://127.0.0.1:8080");', 'expect(baseURL).toBe("http://localhost:8080");')
p.write_text(s)
p = Path('docs/implementation/FT012_JOURNAL_WRITE_DOR.md')
p.write_text(p.read_text() + '''
## Qualification continuation 2026-10-15 — acceptance before test repair

Continue PR #260 from `85be220fdef6b21d27e1d3909e99d11a13b274cc`, not a
new journal owner. Run 38634613102 was red: one invalid retention fixture and
12 browser failures. The retained browser traces show cross-origin requests from
`localhost:8080` to `127.0.0.1:8080` rejected by CORS. The new journal journey
passed, but did not qualify those regressions.

- Build the retention case through actual synthetic plan approval, product
  selection and keyed BUY, then SELL. Never reassign EXTERNAL trade provenance
  with SQL. Assert the full original provenance before and after refused delete;
  preserve journal, Lesson, execution-count and successor assertions.
- Keep the new real journal browser on the existing suite's `localhost:8080`
  origin and its matching API build URL. Keep explicit CI/database/port/write
  guards. Do not widen production CORS, change legacy tests or relax assertions.
- Run targeted PostgreSQL/browser checks followed by the three unchanged full
  scripts on an identified common commit. A passed new journey is not a passed
  suite; failed, skipped and flaky cases must remain visible.
- Update PB-019 and traceability with actual results, remove the temporary CI
  helper after use, and leave both stacked PRs unmerged. No release or deployment.
''')
paths = {'tests/integration/backend/learning/test_journal_write_postgres.py', 'tests/e2e/post-trade-journal-postgres.spec.ts', 'docs/implementation/FT012_JOURNAL_WRITE_DOR.md'}
assert set(subprocess.check_output(['git', 'diff', '--name-only'], text=True).splitlines()) == paths
subprocess.run(['git', 'add', '--', *sorted(paths)], check=True)
subprocess.run(['git', 'rm', '--', *sorted(helpers)], check=True)
subprocess.run(['git', 'diff', '--cached', '--check'], check=True)
assert subprocess.check_output(['git', 'write-tree'], text=True).strip() == 'd860763b7ce989f8fa72ab44bc2a05c72ad4314b'
