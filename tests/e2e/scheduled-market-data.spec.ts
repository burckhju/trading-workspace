import { expect, test } from '@playwright/test';

test('workspace shows automatic refresh coverage and indicative Frankfurt valuation', async ({ page }) => {
  let writes = 0;
  await page.route('**/api/**', async (route) => {
    if (route.request().method() !== 'GET') writes += 1;
    const path = new URL(route.request().url()).pathname;
    let body: unknown = {};
    if (path.endsWith('/operational-workspace/actions')) body = { generated_at: '2026-09-12T12:00:00Z', actions: [] };
    else if (path.endsWith('/operational-workspace/positions')) body = {
      generated_at: '2026-09-12T12:00:00Z', positions: [{
        trade_id: 'trade-1', position_id: 'position-1', product_name: 'BNP Call', product_symbol: null,
        open_quantity: 2000, average_entry_price: '0.51', market_value: '462', unrealized_gross_pnl: '-558',
        unrealized_pnl_usable: true, unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
        realized_gross_pnl: '0', stop_price: null, target_price: null, underlying_symbol: null,
        valuation_currency: 'EUR', valuation_status: 'INDICATIVE', monitoring_status: 'MISSING',
        analysis_warning: 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY', quote_source: 'FRANKFURT_QUOTES',
        quote_observed_at: '2026-09-11T17:43:41Z', attention_state: 'DATA_HEALTH', open_alert_count: 0,
        open_alert_types: [], target: '/trade-management?trade_id=trade-1',
      }],
    };
    else if (path.endsWith('/market-data/refresh/status')) body = {
      enabled: true, running: true, leader: true, last_error: null, current_job: 'WARRANT_QUOTES:three', pending_jobs: 3,
      current_jobs: { WARRANTS: 'WARRANT_QUOTES:three', UNDERLYINGS: 'UNDERLYING_EOD:one' },
      lanes: {
        WARRANTS: { running: true, current_job: 'WARRANT_QUOTES:three', pending_jobs: 2, last_error: null },
        UNDERLYINGS: { running: true, current_job: 'UNDERLYING_EOD:one', pending_jobs: 1, last_error: null },
      },
      settings: { warrants_interval_seconds: 300, underlyings_interval_seconds: 3600, discovery_interval_seconds: 3600 },
      jobs: [{ job: 'WARRANT_QUOTES:one', name: 'BNP Call', isin: 'DE000BN00012', status: 'AVAILABLE', reason: 'QUOTE_OBSERVATIONS_AVAILABLE', next_run_at: '2026-09-12T12:05:00Z' }, { job: 'WARRANT_QUOTES:two', name: 'Vontobel Call', isin: 'DE000VV00123', held: true, status: 'PENDING', reason: 'AWAITING_FIRST_REFRESH', next_run_at: null },
        { job: 'WARRANT_QUOTES:three', name: 'Running Call', isin: null, held: true, status: 'PENDING', reason: 'AWAITING_FIRST_REFRESH', next_run_at: null },
        { job: 'UNDERLYING_EOD:one', name: 'Running Stock', isin: null, held: true, status: 'PENDING', reason: 'AWAITING_FIRST_REFRESH', next_run_at: null }],
    };
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.goto('/workspace');
  await expect(page.getByText('462,00 EUR', { exact: true })).toBeVisible();
  await page.getByRole('button', {name: 'Details',exact:true}).click();
  await expect(page.getByText(/Quelle: FRANKFURT_QUOTES/)).toBeVisible();
  await expect(page.getByText(/Keine Orderfreigabe/).first()).toBeVisible();
  await page.getByText('Automatischer Kursabruf', { exact: true }).click();
  await page.getByRole('button', { name: 'Abrufstatus laden' }).click();
  await expect(page.getByText(/Optionsscheine: alle 5 Min/)).toBeVisible();
  await expect(page.getByText(/Schedulerlauf abgeschlossen · Nächste Prüfung/)).toBeVisible();
  await expect(page.getByText(/Vontobel Call.*Offene Position/)).toBeVisible();
  await expect(page.getByText('Erster Abruf steht aus', { exact: true })).toBeVisible();
  await expect(page.getByText('Abruf läuft', { exact: true })).toHaveCount(2);
  await expect(page.getByText(/Basiswerte: Abruf läuft · 1 Aufgabe/)).toBeVisible();
  await expect(page.getByText(/Optionsscheine: Abruf läuft · 2 Aufgaben/)).toBeVisible();
  await expect(page.getByText('Invalid Date')).toHaveCount(0);
  expect(writes).toBe(0);
});

test('monitoring separates an available scheduler run, retained quote and qualified source recovery', async ({ page }) => {
  let writes = 0;
  let recovered = false;
  const failureTime = '2026-10-30T10:00:00Z';
  const successTime = '2026-10-30T10:05:00Z';
  await page.route('**/api/**', async (route) => {
    if (route.request().method() !== 'GET') writes += 1;
    const path = new URL(route.request().url()).pathname;
    let body: unknown = {};
    if (path.endsWith('/operational-workspace/actions')) {
      body = { generated_at: failureTime, actions: [] };
    } else if (path.endsWith('/operational-workspace/positions')) {
      body = { generated_at: failureTime, positions: [] };
    } else if (path.endsWith('/market-data/refresh/status')) {
      body = {
        enabled: true, running: false, leader: true, last_error: null,
        settings: { warrants_interval_seconds: 300, underlyings_interval_seconds: 3600, discovery_interval_seconds: 3600 },
        jobs: [{
          job: 'WARRANT_QUOTES:diagnostic', name: 'Synthetic monitored call', isin: 'DE000AB00001',
          status: 'AVAILABLE', reason: 'QUOTE_OBSERVATIONS_AVAILABLE', next_run_at: null,
          diagnostics: { scope: 'PROCESS_LOCAL', checks: [{
            kind: 'SOURCE', source: 'FRANKFURT_QUOTES', listing_id: 'listing-diagnostic', identity_key: 'verified-source-identity',
            status: 'AVAILABLE', category: recovered ? null : 'PROVIDER_ERROR', reason: recovered ? null : 'FRANKFURT_HTTP_503',
            consecutive_failures: recovered ? 0 : 2, first_failure_at: recovered ? null : failureTime,
            last_failure_at: failureTime, last_success_at: recovered ? successTime : null,
            recovered_at: recovered ? successTime : null, last_checked_at: recovered ? successTime : failureTime,
            observed_in_latest_run: true, retained_quote: !recovered, qualified_success: recovered,
            quote_status: 'FRESH', quote_usable: true, provider_reachable: true, response_valid: recovered,
            quote_observed_at: recovered ? successTime : failureTime,
            quote_retrieved_at: recovered ? successTime : failureTime,
          }] },
        }],
      };
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.goto('/workspace');
  await page.getByText('Automatischer Kursabruf', { exact: true }).click();
  await page.getByRole('button', { name: 'Abrufstatus laden' }).click();
  await expect(page.getByText('Schedulerlauf abgeschlossen', { exact: true })).toBeVisible();
  await expect(page.getByText(/Offene Quellenbefunde/)).toBeVisible();
  await page.getByText('Diagnose · 1 Abrufnachweis', { exact: true }).click();
  await expect(page.getByText('Providerfehler · 2 Prüfungen in Folge mit Befund', { exact: true })).toBeVisible();
  await expect(page.getByText(/Gespeicherter Ersatzkurs vorhanden/)).toBeVisible();
  await expect(page.getByText('Qualifizierter Erfolg dieser Prüfung: Nein', { exact: true })).toBeVisible();
  await expect(page.getByText(/Kursversorgung wiederhergestellt/)).toHaveCount(0);
  recovered = true;
  await page.getByRole('button', { name: 'Abrufstatus laden' }).click();
  const diagnosis = page.locator('details').filter({ has: page.locator('summary').getByText('Diagnose · 1 Abrufnachweis', { exact: true }) }).last();
  await expect(diagnosis).toBeVisible();
  if ((await diagnosis.getAttribute('open')) === null) {
    await page.getByText('Diagnose · 1 Abrufnachweis', { exact: true }).click();
  }
  await expect(page.getByText(/Kursversorgung wiederhergestellt/)).toBeVisible();
  await expect(page.getByText('Qualifizierter Erfolg dieser Prüfung: Ja', { exact: true })).toBeVisible();
  await expect(page.getByText(/Letzter fehlgeschlagener Abruf/)).toBeVisible();
  await expect(page.getByText(/Offene Quellenbefunde|Gespeicherter Ersatzkurs vorhanden/)).toHaveCount(0);
  expect(writes).toBe(0);
});
