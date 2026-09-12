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
        realized_gross_pnl: '0', stop_price: null, target_price: null, underlying_symbol: null,
        valuation_currency: 'EUR', valuation_status: 'INDICATIVE', monitoring_status: 'MISSING',
        analysis_warning: 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY', quote_source: 'FRANKFURT_QUOTES',
        quote_observed_at: '2026-09-11T17:43:41Z', attention_state: 'DATA_HEALTH', open_alert_count: 0,
        open_alert_types: [], target: '/trade-management?trade_id=trade-1',
      }],
    };
    else if (path.endsWith('/market-data/refresh/status')) body = {
      enabled: true, running: true, leader: true, last_error: null, current_job: null, pending_jobs: 1,
      settings: { warrants_interval_seconds: 300, underlyings_interval_seconds: 3600, discovery_interval_seconds: 3600 },
      jobs: [{ job: 'WARRANT_QUOTES:one', name: 'BNP Call', isin: 'DE000BN00012', status: 'AVAILABLE', reason: 'QUOTE_OBSERVATIONS_AVAILABLE', next_run_at: '2026-09-12T12:05:00Z' }, { job: 'WARRANT_QUOTES:two', name: 'Vontobel Call', isin: 'DE000VV00123', held: true, status: 'PENDING', reason: 'AWAITING_FIRST_REFRESH', next_run_at: null }],
    };
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.goto('/workspace');
  await expect(page.getByText('462 EUR', { exact: true })).toBeVisible();
  await expect(page.getByText(/Quelle: FRANKFURT_QUOTES/)).toBeVisible();
  await expect(page.getByText(/Keine Orderfreigabe/)).toBeVisible();
  await page.getByText('Automatischer Kursabruf', { exact: true }).click();
  await page.getByRole('button', { name: 'Abrufstatus laden' }).click();
  await expect(page.getByText(/Optionsscheine: alle 5 Min/)).toBeVisible();
  await expect(page.getByText(/Erfolgreich · Nächste Prüfung/)).toBeVisible();
  await expect(page.getByText(/Vontobel Call.*Offene Position/)).toBeVisible();
  await expect(page.getByText('Erster Abruf steht aus', { exact: true })).toBeVisible();
  await expect(page.getByText('Invalid Date')).toHaveCount(0);
  expect(writes).toBe(0);
});
