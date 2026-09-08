import { expect, test, type Route } from '@playwright/test';

const planId = '11111111-1111-4111-8111-111111111111';
const versionId = '22222222-2222-4222-8222-222222222222';
const underlyingId = '99999999-9999-4999-8999-999999999999';
const actorId = '00000000-0000-4000-8000-000000000002';
const now = '2026-09-08T16:00:00Z';
const reference = 'TP-11111111';
const tradePlanApiRoute = /\/api\/api\/v1\/trade-plans(?:\/.*)?(?:\?.*)?$/;

function version(status: 'DRAFT' | 'APPROVED') {
  return {
    id: versionId,
    trade_plan_id: planId,
    version: 1,
    direction: 'LONG',
    thesis: 'Hard-delete E2E qualification',
    entry: {
      type: 'PRICE',
      currency: 'EUR',
      price: '100',
      price_from: null,
      price_to: null,
      trigger: null,
      reference_price: null,
      valid_until: null,
      rationale: null,
    },
    invalidation: { stop_price: '95', invalidation_rule: 'Close below support', rationale: null },
    targets: [{ sequence: 1, price: '110', rationale: null }],
    risk_assumptions: {
      thesis_risk: 'Breakout failure',
      max_loss_assumption: null,
      notes: null,
    },
    status,
    created_at: now,
    created_by: actorId,
    previous_version_id: null,
    change_reason: null,
    candidate_evaluation: null,
    approval: status === 'APPROVED'
      ? {
          approval_id: '77777777-7777-4777-8777-777777777777',
          trade_plan_version_id: versionId,
          version: 1,
          actor: actorId,
          approved_at: now,
          correlation_id: null,
        }
      : null,
    events: [],
  };
}

function detail(status: 'DRAFT' | 'APPROVED') {
  return {
    plan: {
      id: planId,
      underlying_id: underlyingId,
      origin_type: 'MANUAL',
      candidate_id: null,
      candidate_evaluation_id: null,
      created_at: now,
      created_by: actorId,
    },
    latest_version: version(status),
  };
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

for (const scenario of [
  { name: 'DRAFT', status: 'DRAFT' as const, historical: false },
  { name: 'APPROVED', status: 'APPROVED' as const, historical: false },
  { name: 'historically traded APPROVED', status: 'APPROVED' as const, historical: true },
]) {
  test(`${scenario.name} TradePlan requires exact confirmation and is permanently deleted`, async ({ page }) => {
    let deleteRequests = 0;

    await page.route(tradePlanApiRoute, async (route) => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      const method = request.method();

      if (method === 'DELETE' && path.endsWith(`/${planId}`)) {
        deleteRequests += 1;
        return json(route, {
          trade_plan_id: planId,
          trade_plan_versions: 1,
          product_selection_runs: scenario.historical ? 1 : 0,
          trades: scenario.historical ? 1 : 0,
          positions: scenario.historical ? 1 : 0,
          alerts: scenario.historical ? 1 : 0,
          notifications: scenario.historical ? 1 : 0,
          post_trade_observations: scenario.historical ? 1 : 0,
          exit_reviews: scenario.historical ? 1 : 0,
          trade_journals: scenario.historical ? 1 : 0,
          learning_evidence: scenario.historical ? 1 : 0,
          external_observation_trade_links: scenario.historical ? 1 : 0,
        });
      }

      if (method === 'GET' && path.endsWith(`/${planId}/versions`)) {
        return json(route, [version(scenario.status)]);
      }
      if (method === 'GET' && path.endsWith(`/${planId}`)) {
        return json(route, detail(scenario.status));
      }

      return json(route, []);
    });

    await page.goto('/trade-plans');
    await page.getByLabel('TradePlan-ID').fill(planId);
    await page.getByRole('button', { name: 'Laden' }).click();

    await expect(page.getByRole('heading', { name: reference })).toBeVisible();
    const deleteButton = page.getByRole('button', { name: 'TradePlan unwiderruflich löschen' });
    await expect(deleteButton).toBeDisabled();

    await page.getByLabel(new RegExp(`Zur Bestätigung ${reference} eingeben`)).fill('TP-WRONG');
    await expect(deleteButton).toBeDisabled();
    expect(deleteRequests).toBe(0);

    await page.getByLabel(new RegExp(`Zur Bestätigung ${reference} eingeben`)).fill(reference);
    await expect(deleteButton).toBeEnabled();
    await deleteButton.click();

    await expect.poll(() => deleteRequests).toBe(1);
    await expect(page).toHaveURL(/\/trade-plans\/overview$/);
  });
}
