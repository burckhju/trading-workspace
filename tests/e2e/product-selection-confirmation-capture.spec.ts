import { randomUUID } from 'node:crypto';
import { expect, test, type APIResponse, type Request } from '@playwright/test';

test.use({ baseURL: 'http://localhost:8080', timezoneId: 'Europe/Berlin' });
test.skip(
  process.env.TRADE_E2E_WRITES_ALLOWED !== '1',
  'Requires an explicitly disposable test stack; never enable on a user depot',
);

async function body(response: Pick<APIResponse, 'status' | 'text' | 'json'>, status = 201) {
  expect(response.status(), await response.text()).toBe(status);
  return response.json();
}

test('existing incomplete-evaluation confirmation leads to one persisted BUY without a new entry', async ({
  page,
  request,
}) => {
  const root = 'http://127.0.0.1:8000/api/v1';
  const token = randomUUID().slice(0, 8);
  const issuer = await body(await request.post(`${root}/market-reference-data/issuers`, {
    data: { legal_name: `Synthetic confirmation ${randomUUID()}`, display_name: 'Synthetic confirmation' },
  }));
  const venues = await body(await request.get(`${root}/market-reference-data/trading-venues`), 200);
  const venueId = venues.items.find((venue: { mic: string }) => venue.mic === 'XETR').id;
  const underlying = await body(await request.post(`${root}/underlyings`, {
    data: {
      name: `Synthetic confirmation stock ${token}`,
      type: 'STOCK',
      primary_listing: { trading_venue_id: venueId, ticker: `CF${token}`, currency_code: 'EUR' },
    },
  }));
  const warrant = await body(await request.post(`${root}/warrants`, {
    data: {
      issuer_id: issuer.id, underlying_id: underlying.id,
      display_name: `Synthetic confirmation warrant ${token}`,
      option_direction: 'CALL', strike: '100', strike_currency_code: 'EUR',
      maturity_date: '2099-12-31', ratio: '0.1',
    },
  }));
  await body(await request.post(`${root}/warrants/${warrant.id}/listings`, {
    data: { trading_venue_id: venueId, symbol: `CFL${token}`, quotation_currency_code: 'EUR' },
  }));
  const plan = await body(await request.post(`${root}/trade-plans`, {
    data: {
      origin_type: 'MANUAL', underlying_id: underlying.id,
      thesis: 'Synthetic confirmation workflow, not an investment recommendation',
      entry: { type: 'PRICE', currency: 'EUR', price: '100' },
      invalidation: { stop_price: '95' },
      targets: [{ sequence: 1, price: '110' }],
      risk_assumptions: { thesis_risk: 'Synthetic test risk' },
    },
  }));
  const versionUrl = `${root}/trade-plans/${plan.plan.id}/versions/${plan.latest_version.id}`;
  await body(await request.post(`${versionUrl}/submit-review`), 200);
  await body(await request.post(`${versionUrl}/approve`), 200);
  const started = await body(await request.post(`${root}/product-selection-runs`, {
    data: { trade_plan_id: plan.plan.id, trade_plan_version_id: plan.latest_version.id },
  }));
  const runId = started.run.id;
  const runUrl = `${root}/product-selection-runs/${runId}`;
  expect(started.evaluations).toHaveLength(1);
  expect(started.evaluations[0].eligibility_status).toBe('NOT_EVALUABLE');
  expect(started.selection).toBeNull();
  const evaluationId = started.evaluations[0].id;
  const actions = async () => (await body(await request.get(`${root}/operational-workspace/actions`), 200)).actions;
  const choices = (await actions()).filter((action: { resource_id: string }) => action.resource_id === runId);
  expect(choices).toHaveLength(1);
  expect(choices[0].action_type).toBe('PRODUCT_SELECTION_CHOICE');
  expect(choices[0].detail).toContain('Begründung und Bestätigung');
  // No missing-data override can be recorded without the existing rationale.
  await body(await request.post(`${runUrl}/selection`, {
    data: { product_evaluation_id: evaluationId, rationale: '   ' },
  }), 422);
  expect((await body(await request.get(runUrl), 200)).selection).toBeNull();

  const writes: Request[] = [];
  page.on('request', outgoing => {
    if (outgoing.method() === 'POST' && (
      outgoing.url().includes('/product-selection-runs') || outgoing.url().includes('/trade-position/')
    )) writes.push(outgoing);
  });
  await page.goto('/workspace');
  await page.locator(`a[href="/product-selection?run_id=${runId}"]`).click();
  await expect(page.getByRole('heading', { name: 'Produktvergleich' })).toBeVisible();
  const choose = page.getByRole('button', { name: 'Dieses Produkt auswählen' });
  await choose.click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByText('Bewertung unvollständig')).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'Auswahl dokumentieren' })).toBeDisabled();
  await dialog.getByRole('button', { name: 'Abbrechen' }).click();
  expect(writes).toHaveLength(0);
  expect((await body(await request.get(runUrl), 200)).selection).toBeNull();

  await choose.click();
  const rationale = 'Synthetic broker execution verified; evaluation data remains incomplete.';
  await dialog.getByLabel(/Begründung/).fill(rationale);
  await dialog.getByRole('button', { name: 'Auswahl dokumentieren' }).click();
  await expect(page.getByRole('heading', { name: /tatsächlichen Kauf erfassen/ })).toBeVisible();
  expect(writes).toHaveLength(1);
  expect(writes[0].url()).toContain(`/${runId}/selection`);
  const selected = await body(await request.get(runUrl), 200);
  expect(selected.selection.rationale).toBe(rationale);
  expect(selected.selection.product_evaluation_id).toBe(evaluationId);
  // Confirmation never rewrites the immutable incomplete evaluation or invents quotes.
  expect(selected.evaluations).toEqual(started.evaluations);
  let currentActions = await actions();
  expect(currentActions.some((action: { resource_id: string }) => action.resource_id === runId)).toBe(false);
  const initial = currentActions.filter((action: { resource_id: string }) => action.resource_id === selected.selection.id);
  expect(initial).toHaveLength(1);
  expect(initial[0].action_type).toBe('INITIAL_PURCHASE');

  await page.getByLabel('Kaufdatum', { exact: true }).fill('2026-08-17');
  await page.getByLabel('Kaufmenge').fill('10');
  await page.getByLabel('Kaufpreis').fill('2,35');
  const capturedResponse = page.waitForResponse(response =>
    response.request().method() === 'POST' && response.url().endsWith('/purchases/from-selection'),
  );
  await page.getByRole('button', { name: 'BUY erfassen und Position eröffnen' }).click();
  const captured = await body(await capturedResponse);
  await expect(page.getByText(/Kauf wurde als BUY erfasst/)).toBeVisible();
  expect(writes).toHaveLength(2);
  expect(captured.trade).toMatchObject({
    product_id: warrant.id, origin: 'WORKSPACE_SELECTION', trade_plan_id: plan.plan.id,
    trade_plan_version_id: plan.latest_version.id, product_selection_id: selected.selection.id,
    product_evaluation_id: evaluationId,
  });
  expect(captured.execution).toMatchObject({
    quantity: 10, executed_on: '2026-08-17', execution_timezone: 'Europe/Berlin', side: 'BUY',
  });
  expect(Number(captured.execution.price_per_unit)).toBe(2.35);
  expect(Number(captured.position.cost_basis)).toBe(23.5);
  expect(captured.position.open_quantity).toBe(10);
  expect(new Date(captured.execution.recorded_at).getTime()).toBeGreaterThan(new Date(captured.execution.executed_at).getTime());
  const tradeUrl = `${root}/trade-position/trades/${captured.trade.id}`;
  const timeline = await body(await request.get(`${tradeUrl}/timeline`), 200);
  // The same keyed request remains one execution, while a new first BUY is blocked.
  const payload = writes[1].postDataJSON();
  expect(payload.executed_at).toBeUndefined();
  expect(payload.request_id).toBeTruthy();
  const replay = await body(await request.post(`${root}/trade-position/purchases/from-selection`, { data: payload }));
  expect(replay.trade.id).toBe(captured.trade.id);
  expect(replay.execution.id).toBe(captured.execution.id);
  const duplicate = await body(await request.post(`${root}/trade-position/purchases/from-selection`, {
    data: { ...payload, request_id: randomUUID() },
  }), 409);
  expect(duplicate.code).toBe('OPEN_TRADE_EXISTS');
  expect(await body(await request.get(`${tradeUrl}/timeline`), 200)).toEqual(timeline);
  expect((await body(await request.get(`${tradeUrl}/position`), 200)).open_quantity).toBe(10);
  currentActions = await actions();
  expect(currentActions.some((action: { resource_id: string }) => action.resource_id === selected.selection.id)).toBe(false);
  expect(currentActions.some((action: { resource_id: string; action_type: string }) =>
    action.resource_id === captured.trade.id && ['OPEN_POSITION_MANAGEMENT', 'POSITION_DATA_HEALTH'].includes(action.action_type),
  )).toBe(true);
  await page.getByRole('link', { name: 'Arbeitsbereich', exact: true }).click();
  await expect(page.locator(`a[href="/product-selection?run_id=${runId}"]`)).toHaveCount(0);
  await expect(page.locator(`a[href="/trade-management?trade_id=${captured.trade.id}"]`).first()).toBeVisible();
  await page.reload();
  await expect(page.locator(`a[href="/trade-management?trade_id=${captured.trade.id}"]`).first()).toBeVisible();
  expect((await body(await request.get(runUrl), 200)).evaluations).toEqual(started.evaluations);
});
