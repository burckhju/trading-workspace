import { expect, test, type Page, type Route } from '@playwright/test';

const planId = '11111111-1111-4111-8111-111111111111';
const version1Id = '22222222-2222-4222-8222-222222222222';
const version2Id = '33333333-3333-4333-8333-333333333333';
const underlyingId = '99999999-9999-4999-8999-999999999999';
const candidateId = '44444444-4444-4444-8444-444444444444';
const evaluationId = '55555555-5555-4555-8555-555555555555';
const actorId = '00000000-0000-4000-8000-000000000002';
const now = '2026-08-11T17:00:00Z';
const proxyApiV1 = '/api/api/v1';
const tradePlanApiRoute = /\/api\/api\/v1\/trade-plans(?:\/.*)?(?:\?.*)?$/;

function entry(type: 'PRICE' | 'TRIGGER' = 'PRICE') {
  return {
    type,
    currency: 'EUR',
    price: type === 'PRICE' ? '100' : null,
    price_from: null,
    price_to: null,
    trigger: type === 'TRIGGER' ? 'Break above 101' : null,
    reference_price: null,
    valid_until: null,
    rationale: null,
  };
}

function version(overrides: Record<string, unknown> = {}) {
  return {
    id: version1Id,
    trade_plan_id: planId,
    version: 1,
    direction: 'LONG',
    thesis: 'Continuation thesis',
    entry: entry(),
    invalidation: { stop_price: '95', invalidation_rule: 'Close below support', rationale: null },
    targets: [{ sequence: 1, price: '110', rationale: 'Prior high' }],
    risk_assumptions: {
      thesis_risk: 'Breakout failure',
      max_loss_assumption: '5%',
      notes: 'No position sizing',
    },
    status: 'DRAFT',
    created_at: now,
    created_by: actorId,
    previous_version_id: null,
    change_reason: null,
    candidate_evaluation: null,
    approval: null,
    events: [],
    ...overrides,
  };
}

function plan(overrides: Record<string, unknown> = {}) {
  return {
    id: planId,
    underlying_id: underlyingId,
    origin_type: 'MANUAL',
    candidate_id: null,
    candidate_evaluation_id: null,
    created_at: now,
    created_by: actorId,
    ...overrides,
  };
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function fillCommonPlan(page: Page) {
  await page.getByLabel('Trade Thesis').fill('Continuation thesis');
  await page.getByLabel('Technischer Stop').fill('95');
  await page.getByLabel('Invalidierungsregel').fill('Close below support');
  await page.getByLabel('Target 1').fill('110');
  await page.getByLabel('Target-Begründung').fill('Prior high');
  await page.getByLabel('Plan-Risiko / Annahme').fill('Breakout failure');
  await page.getByLabel('Max-Loss-Annahme (optional)').fill('5%');
  await page.getByLabel('Risk Notes').fill('No position sizing');
}

test('manual TradePlan flows from DRAFT through explicit approval with append-only audit', async ({ page }) => {
  const observedTradePlanRequests: string[] = [];
  let current = version();
  let submitReviewRequests = 0;
  let approveRequests = 0;
  const history = () => [current];

  await page.route(tradePlanApiRoute, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;

    if (path.endsWith('/trade-plans') && request.method() === 'POST') {
      const body = request.postDataJSON();
      expect(body).toMatchObject({
        origin_type: 'MANUAL',
        underlying_id: underlyingId,
        thesis: 'Continuation thesis',
        entry: { type: 'PRICE', currency: 'EUR', price: '100' },
      });
      expect(body).not.toHaveProperty('candidate_id');
      expect(body).not.toHaveProperty('candidate_evaluation_id');
      expect(JSON.stringify(body)).not.toMatch(/warrant|issuer|leverage|order_quantity/i);
      return json(route, { plan: plan(), latest_version: current }, 201);
    }

    if (path.endsWith(`/${planId}/versions/${version1Id}/submit-review`) && request.method() === 'POST') {
      submitReviewRequests += 1;
      current = version({
        status: 'READY_FOR_REVIEW',
        events: [{
          id: '66666666-6666-4666-8666-666666666661',
          event_type: 'SUBMITTED_FOR_REVIEW',
          from_status: 'DRAFT',
          to_status: 'READY_FOR_REVIEW',
          reason: null,
          actor: actorId,
          correlation_id: request.headers()['x-correlation-id'] ?? null,
          occurred_at: now,
        }],
      });
      return json(route, current);
    }

    if (path.endsWith(`/${planId}/versions/${version1Id}/approve`) && request.method() === 'POST') {
      approveRequests += 1;
      current = version({
        status: 'APPROVED',
        events: [
          {
            id: '66666666-6666-4666-8666-666666666661',
            event_type: 'SUBMITTED_FOR_REVIEW',
            from_status: 'DRAFT',
            to_status: 'READY_FOR_REVIEW',
            reason: null,
            actor: actorId,
            correlation_id: 'corr-review',
            occurred_at: now,
          },
          {
            id: '66666666-6666-4666-8666-666666666662',
            event_type: 'APPROVED',
            from_status: 'READY_FOR_REVIEW',
            to_status: 'APPROVED',
            reason: null,
            actor: actorId,
            correlation_id: request.headers()['x-correlation-id'] ?? null,
            occurred_at: now,
          },
        ],
        approval: {
          approval_id: '77777777-7777-4777-8777-777777777777',
          trade_plan_version_id: version1Id,
          version: 1,
          actor: actorId,
          approved_at: now,
          correlation_id: request.headers()['x-correlation-id'] ?? null,
        },
      });
      return json(route, current);
    }

    if (path.endsWith(`/${planId}/versions`) && request.method() === 'GET') return json(route, history());
    if (path.endsWith(`/${planId}`) && request.method() === 'GET') {
      return json(route, { plan: plan(), latest_version: current });
    }

    return json(route, { code: 'E2E_ROUTE_MISSING', message: `${request.method()} ${path}` }, 500);
  });

  await page.goto('/trade-plans');
  await page.getByLabel('Underlying-ID').fill(underlyingId);
  await fillCommonPlan(page);
  await page.getByLabel('Entry-Preis').fill('100');
  await page.getByRole('button', { name: 'TradePlan als DRAFT erstellen' }).click();

  await expect(page.getByText('TradePlan wurde als DRAFT erstellt.')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'DRAFT' })).toBeVisible();

  await page.getByRole('button', { name: 'Zur Prüfung' }).click();
  await expect(page.getByRole('heading', { name: 'READY_FOR_REVIEW' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Explizit freigeben' })).toBeEnabled();

  await page.getByRole('button', { name: 'Explizit freigeben' }).click();
  await expect.poll(() => approveRequests).toBe(1);
  await expect(page.getByText('APPROVED', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('Approval-Nachweis')).toBeVisible();
  await expect(page.getByText('APPROVED', { exact: true }).first()).toBeVisible();
});

test('CandidateEvaluation origin preserves exact evaluation provenance and never sends underlying override', async ({ page }) => {
  const candidateVersion = version({
    entry: entry('TRIGGER'),
    candidate_evaluation: {
      candidate_id: candidateId,
      evaluation_id: evaluationId,
      evaluation_version: 7,
      direction: 'LONG',
      model_id: 'candidate-qualification',
      model_version: '1.0.0',
      qualification: 'READY_FOR_PLANNING',
      quality_status: 'COMPLETE',
      evaluated_at: now,
      sources: [{
        role: 'MARKET_CONTEXT',
        source_type: 'MARKET_CONTEXT',
        source_id: '88888888-8888-4888-8888-888888888888',
        source_version: 3,
        model_id: 'market-context',
        model_version: '1.0.0',
      }],
    },
  });

  await page.route(tradePlanApiRoute, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith('/trade-plans') && request.method() === 'POST') {
      const body = request.postDataJSON();
      expect(body.origin_type).toBe('CANDIDATE_EVALUATION');
      expect(body.candidate_id).toBe(candidateId);
      expect(body.candidate_evaluation_id).toBe(evaluationId);
      expect(body).not.toHaveProperty('underlying_id');
      return json(route, {
        plan: plan({
          origin_type: 'CANDIDATE_EVALUATION',
          candidate_id: candidateId,
          candidate_evaluation_id: evaluationId,
        }),
        latest_version: candidateVersion,
      }, 201);
    }
    return json(route, { code: 'E2E_ROUTE_MISSING', message: `${request.method()} ${path}` }, 500);
  });

  await page.goto(`/trade-plans?candidate_id=${candidateId}&candidate_evaluation_id=${evaluationId}`);
  await expect(page.getByText(/serverseitig ausschließlich aus der konkreten CandidateEvaluation/)).toBeVisible();
  await fillCommonPlan(page);
  await page.getByLabel('Entry-Art').selectOption('TRIGGER');
  await page.getByRole('textbox', { name: 'Trigger' }).fill('Break above 101');
  await page.getByRole('button', { name: 'TradePlan als DRAFT erstellen' }).click();

  await expect(page.getByText('CandidateEvaluation-Provenance')).toBeVisible();
  await expect(page.getByText(new RegExp(`${evaluationId} · v7`))).toBeVisible();
  await expect(page.getByText(/MARKET_CONTEXT/).first()).toBeVisible();
});

test('approved version can be amended through REST and exact version lineage is visible after reload', async ({ page }) => {
  const observedTradePlanRequests: string[] = [];
  const approvedV1 = version({
    status: 'APPROVED',
    approval: {
      approval_id: '77777777-7777-4777-8777-777777777777',
      trade_plan_version_id: version1Id,
      version: 1,
      actor: actorId,
      approved_at: now,
      correlation_id: 'corr-approve-v1',
    },
  });
  let versions = [approvedV1];
  let latest = approvedV1;
  let detailReads = 0;
  let historyReads = 0;

  await page.route(tradePlanApiRoute, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();

    if (
      method === 'POST' &&
      path.endsWith(`/${planId}/versions/${version1Id}/amendments`)
    ) {
      const body = request.postDataJSON();
      expect(body.change_reason).toBe('Raise target after confirmed breakout');
      latest = version({
        id: version2Id,
        version: 2,
        thesis: 'Continuation thesis amended',
        status: 'DRAFT',
        previous_version_id: version1Id,
        change_reason: body.change_reason,
        approval: null,
      });
      versions = [version({ ...approvedV1, status: 'SUPERSEDED' }), latest];
      return json(route, latest, 201);
    }

    if (method === 'GET' && path.endsWith(`/${planId}/versions`)) {
      historyReads += 1;
      return json(route, versions);
    }

    if (method === 'GET' && path.endsWith(`/${planId}`)) {
      detailReads += 1;
      return json(route, { plan: plan(), latest_version: latest });
    }

    return json(route, { code: 'E2E_ROUTE_MISSING', message: `${method} ${path}` }, 500);
  });

  await page.goto('/trade-plans');

  const amendment = await page.evaluate(async ({ planId: id, versionId }) => {
    const response = await fetch(`/api/api/v1/trade-plans/${id}/versions/${versionId}/amendments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        change_reason: 'Raise target after confirmed breakout',
        thesis: 'Continuation thesis amended',
        entry: { type: 'PRICE', currency: 'EUR', price: '100' },
        invalidation: { stop_price: '95', invalidation_rule: 'Close below support' },
        targets: [{ sequence: 1, price: '115', rationale: 'Extended target' }],
        risk_assumptions: { thesis_risk: 'Breakout failure' },
      }),
    });
    return { status: response.status, body: await response.json() };
  }, { planId, versionId: version1Id });

  expect(amendment.status).toBe(201);
  expect(amendment.body).toMatchObject({
    id: version2Id,
    version: 2,
    previous_version_id: version1Id,
    status: 'DRAFT',
  });

  await page.getByLabel('TradePlan-ID').fill(planId);
  await page.getByRole('button', { name: 'Laden' }).click();
  await expect(page.getByText('DRAFT', { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/Version 1 · SUPERSEDED/)).toBeVisible();
  await expect(page.getByText(/Version 2 · DRAFT/)).toBeVisible();
  await expect(page.getByText(/Raise target after confirmed breakout/)).toBeVisible();
});
