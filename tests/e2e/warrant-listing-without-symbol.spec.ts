import { randomUUID } from 'node:crypto';
import { expect, test, type APIResponse } from '@playwright/test';

test.use({ baseURL: 'http://localhost:8080', timezoneId: 'Europe/Berlin' });
test.skip(
  process.env.TRADE_E2E_WRITES_ALLOWED !== '1',
  'Requires an explicitly disposable test stack; never enable on a user depot',
);

async function body(response: APIResponse, status = 201) {
  expect(response.status(), await response.text()).toBe(status);
  return response.json();
}

test('existing administration records a symbol-less listing and unblocks the existing confirmation and BUY', async ({ page, request }) => {
  const root = 'http://127.0.0.1:8000/api/v1';
  const token = randomUUID().slice(0, 8);
  const issuer = await body(await request.post(`${root}/market-reference-data/issuers`, {
    data: { legal_name: `Synthetic symbol-less ${randomUUID()}`, display_name: 'Synthetic symbol-less' },
  }));
  const venues = await body(await request.get(`${root}/market-reference-data/trading-venues`), 200);
  const venueId = venues.items.find((venue: { mic: string }) => venue.mic === 'XETR').id;
  const underlying = await body(await request.post(`${root}/underlyings`, {
    data: {
      name: `Synthetic symbol-less stock ${token}`, type: 'STOCK',
      primary_listing: { trading_venue_id: venueId, ticker: `SL${token}`, currency_code: 'EUR' },
    },
  }));
  const warrant = await body(await request.post(`${root}/warrants`, {
    data: {
      issuer_id: issuer.id, underlying_id: underlying.id,
      display_name: `Synthetic symbol-less warrant ${token}`,
      option_direction: 'CALL', strike: '100', strike_currency_code: 'EUR',
      maturity_date: '2099-12-31', ratio: '0.1',
    },
  }));
  const plan = await body(await request.post(`${root}/trade-plans`, {
    data: {
      origin_type: 'MANUAL', underlying_id: underlying.id,
      thesis: 'Synthetic listing regression, not an investment recommendation',
      entry: { type: 'PRICE', currency: 'EUR', price: '100' },
      invalidation: { stop_price: '95' }, targets: [{ sequence: 1, price: '110' }],
      risk_assumptions: { thesis_risk: 'Synthetic risk' },
    },
  }));
  const versionUrl = `${root}/trade-plans/${plan.plan.id}/versions/${plan.latest_version.id}`;
  await body(await request.post(`${versionUrl}/submit-review`), 200);
  await body(await request.post(`${versionUrl}/approve`), 200);
  const evaluate = async () => body(await request.post(`${root}/product-selection-runs`, {
    data: { trade_plan_id: plan.plan.id, trade_plan_version_id: plan.latest_version.id },
  }));
  const before = await evaluate();
  expect(before.evaluations).toHaveLength(0);
  expect(before.universe_omissions).toEqual([
    expect.objectContaining({ warrant_id: warrant.id, reason: 'NO_LISTING' }),
  ]);

  await page.goto(`/product-selection?run_id=${before.run.id}`);
  await page.getByRole('link', { name: 'Notierung ergänzen' }).click();
  await expect(page.getByRole('heading', { name: warrant.display_name, exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Optionsschein anlegen', exact: true })).toHaveCount(0);
  const symbol = page.getByLabel('Symbol', { exact: true });
  await expect(symbol).not.toHaveAttribute('required');
  await expect(symbol).toHaveAttribute('maxlength', '64');
  await expect(page.getByText(/Veröffentlicht der Handelsplatz kein Börsensymbol/)).toBeVisible();
  const add = page.getByRole('button', { name: 'Notierung hinzufügen' });
  // Venue is still mandatory. Navigation and an incomplete form create no listing.
  await add.click();
  expect(await body(await request.get(`${root}/warrants/${warrant.id}/listings`), 200)).toEqual([]);
  await page.getByLabel('Handelsplatz', { exact: true }).selectOption(venueId);
  await page.getByLabel('Handelswährung', { exact: true }).fill('EUR');
  const addedResponse = page.waitForResponse(response =>
    response.request().method() === 'POST' && response.url().endsWith(`/warrants/${warrant.id}/listings`),
  );
  await add.click();
  const added = await body(await addedResponse);
  expect(added).toMatchObject({ warrant_id: warrant.id, trading_venue_id: venueId, symbol: null, quotation_currency_code: 'EUR' });
  await expect(page.getByText('Ohne Börsensymbol', { exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: new RegExp(warrant.display_name) }).click();
  await expect(page.getByText('Ohne Börsensymbol', { exact: true })).toBeVisible();
  const persisted = await body(await request.get(`${root}/warrants/${warrant.id}/listings`), 200);
  expect(persisted).toHaveLength(1);
  expect(persisted[0]).toMatchObject({ id: added.id, symbol: null, quotation_currency_code: 'EUR' });
  // No duplicate listing and no rewriting of the immutable empty run.
  await body(await request.post(`${root}/warrants/${warrant.id}/listings`, {
    data: { trading_venue_id: venueId, symbol: null, quotation_currency_code: 'EUR' },
  }), 409);
  expect(await body(await request.get(`${root}/product-selection-runs/${before.run.id}`), 200)).toEqual(before);
  await page.getByRole('link', { name: 'Zurück zur Produktauswahl', exact: true }).click();
  await expect(page).toHaveURL(`/product-selection?run_id=${before.run.id}`);
  await expect(page.getByRole('link', { name: 'Notierung ergänzen' })).toBeVisible();
  const reevaluated = page.waitForResponse(response =>
    response.request().method() === 'POST' && response.url().endsWith('/product-selection-runs'),
  );
  await page.getByRole('button', { name: 'Produkte neu bewerten', exact: true }).click();
  const after = await body(await reevaluated);
  expect(after.run).toMatchObject({ trade_plan_id: plan.plan.id, trade_plan_version_id: plan.latest_version.id });
  expect(after.universe_omissions).toEqual([]);
  expect(after.evaluations).toHaveLength(1);
  expect(after.evaluations[0]).toMatchObject({ warrant_id: warrant.id, warrant_listing_id: added.id, eligibility_status: 'NOT_EVALUABLE' });
  expect(after.selection).toBeNull();

  await page.getByRole('button', { name: 'Dieses Produkt auswählen' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('button', { name: 'Auswahl dokumentieren' })).toBeDisabled();
  await dialog.getByLabel(/Begründung/).fill('Synthetic executed purchase; quote data remains missing.');
  await dialog.getByRole('button', { name: 'Auswahl dokumentieren' }).click();
  await expect(page.getByRole('heading', { name: /tatsächlichen Kauf erfassen/ })).toBeVisible();
  await page.getByLabel('Kaufdatum', { exact: true }).fill('2026-08-17');
  await page.getByLabel('Kaufmenge').fill('10');
  await page.getByLabel('Kaufpreis').fill('2,35');
  const capturedResponse = page.waitForResponse(response =>
    response.request().method() === 'POST' && response.url().endsWith('/purchases/from-selection'),
  );
  await page.getByRole('button', { name: 'BUY erfassen und Position eröffnen' }).click();
  const captured = await body(await capturedResponse);
  expect(captured.trade).toMatchObject({ product_id: warrant.id, trade_plan_id: plan.plan.id, trade_plan_version_id: plan.latest_version.id, product_evaluation_id: after.evaluations[0].id });
  expect(captured.position.open_quantity).toBe(10);
  expect(Number(captured.position.cost_basis)).toBe(23.5);
  expect((await body(await request.get(`${root}/product-selection-runs/${after.run.id}`), 200)).evaluations).toEqual(after.evaluations);
});

test('an empty selection continues into existing product administration with the exact underlying', async ({ page, request }) => {
  const root = 'http://127.0.0.1:8000/api/v1';
  const token = randomUUID().slice(0, 8);
  const issuer = await body(await request.post(`${root}/market-reference-data/issuers`, {
    data: { legal_name: `Synthetic empty repair ${randomUUID()}`, display_name: `Synthetic repair ${token}` },
  }));
  const venues = await body(await request.get(`${root}/market-reference-data/trading-venues`), 200);
  const venueId = venues.items.find((venue: { mic: string }) => venue.mic === 'XETR').id;
  const underlying = await body(await request.post(`${root}/underlyings`, {
    data: { name: `Synthetic empty repair stock ${token}`, type: 'STOCK',
      primary_listing: { trading_venue_id: venueId, ticker: `ER${token}`, currency_code: 'EUR' },
    },
  }));
  const plan = await body(await request.post(`${root}/trade-plans`, {
    data: { origin_type: 'MANUAL', underlying_id: underlying.id,
      thesis: 'Synthetic empty selection repair only',
      entry: { type: 'PRICE', currency: 'EUR', price: '100' },
      invalidation: { stop_price: '95' }, targets: [{ sequence: 1, price: '110' }],
      risk_assumptions: { thesis_risk: 'Synthetic risk' },
    },
  }));
  const versionUrl = `${root}/trade-plans/${plan.plan.id}/versions/${plan.latest_version.id}`;
  await body(await request.post(`${versionUrl}/submit-review`), 200);
  await body(await request.post(`${versionUrl}/approve`), 200);
  const before = await body(await request.post(`${root}/product-selection-runs`, {
    data: { trade_plan_id: plan.plan.id, trade_plan_version_id: plan.latest_version.id },
  }));
  expect(before.evaluations).toEqual([]);
  expect(before.universe_omissions).toEqual([]);
  const writes: string[] = [];
  page.on('request', outgoing => {
    if (outgoing.method() === 'POST') writes.push(outgoing.url());
  });
  await page.goto(`/product-selection?run_id=${before.run.id}`);
  await page.getByRole('link', { name: 'Optionsscheinstammdaten prüfen' }).click();
  const underlyingField = page.getByLabel('Basiswert *', { exact: true });
  await expect(underlyingField).toHaveValue(underlying.id);
  await expect(underlyingField).toBeDisabled();
  await page.reload();
  await expect(underlyingField).toHaveValue(underlying.id);
  expect(writes).toEqual([]);
  await page.getByLabel('Anzeigename *', { exact: true }).fill(`Synthetic repaired warrant ${token}`);
  await page.getByLabel('Emittent *', { exact: true }).selectOption(issuer.id);
  await page.getByLabel('Strike *', { exact: true }).fill('100');
  await page.getByLabel('Fälligkeit *', { exact: true }).fill('2099-12-31');
  await page.getByLabel(/^Bezugsverhältnis/).fill('0.1');
  const createdResponse = page.waitForResponse(response =>
    response.request().method() === 'POST' && response.url().endsWith('/warrants'),
  );
  await page.getByRole('button', { name: 'Optionsschein anlegen', exact: true }).click();
  const created = await body(await createdResponse);
  expect(created.underlying_id).toBe(underlying.id);
  await expect(page.getByRole('heading', { name: created.display_name, exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Zurück zur Produktauswahl' }).click();
  await expect(page).toHaveURL(`/product-selection?run_id=${before.run.id}`);
  await expect(page.getByRole('link', { name: 'Optionsscheinstammdaten prüfen' })).toBeVisible();
  expect(await body(await request.get(`${root}/product-selection-runs/${before.run.id}`), 200)).toEqual(before);
  expect(writes).toHaveLength(1);
  expect(writes[0]).toMatch(/\/warrants$/);
  // No automatic evaluation, selection or BUY, and no invented listing.
  expect(await body(await request.get(`${root}/warrants/${created.id}/listings`), 200)).toEqual([]);
});
