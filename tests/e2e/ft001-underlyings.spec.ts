import { expect, test, type Page, type Route } from '@playwright/test';

const underlyingId = '11111111-1111-4111-8111-111111111111';
const listingId = '22222222-2222-4222-8222-222222222222';
const venueId = '00000000-0000-4000-8001-000000000001';
const now = '2026-08-04T18:00:00Z';

const summary = {
  id: underlyingId,
  type: 'STOCK',
  name: 'Siemens AG',
  isin: 'DE0007236101',
  wkn: '723610',
  lifecycle_status: 'ACTIVE',
  quality_status: 'COMPLETE',
  version: 1,
  created_at: now,
  updated_at: now,
  primary_listing: {
    id: listingId,
    ticker: 'SIE',
    trading_venue_id: venueId,
    trading_venue_mic: 'XETR',
    trading_venue_name: 'Xetra',
    currency_code: 'EUR',
  },
};

const listing = {
  id: listingId,
  underlying_id: underlyingId,
  trading_venue_id: venueId,
  trading_venue_mic: 'XETR',
  trading_venue_name: 'Xetra',
  ticker: 'SIE',
  currency_code: 'EUR',
  lifecycle_status: 'ACTIVE',
  is_primary: true,
  version: 1,
  created_at: now,
  updated_at: now,
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function installMarketApi(page: Page) {
  let currentSummary = { ...summary };
  let deleted = false;

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path.endsWith('/market-reference-data/trading-venues')) {
      return json(route, {
        items: [
          {
            id: venueId,
            mic: 'XETR',
            name: 'Xetra',
            country_code: 'DE',
            timezone: 'Europe/Berlin',
            reference_version: 'FT-001-V1',
          },
        ],
      });
    }
    if (path.endsWith('/market-reference-data/currencies')) {
      return json(route, {
        items: [
          { code: 'EUR', name: 'Euro', minor_unit: 2, reference_version: 'FT-001-V1' },
        ],
      });
    }
    if (path.endsWith(`/underlyings/${underlyingId}/audit-events`)) {
      return json(route, {
        items: [
          {
            id: '33333333-3333-4333-8333-333333333333',
            aggregate_type: 'UNDERLYING',
            aggregate_id: underlyingId,
            occurred_at: now,
            actor_display_name: 'E2E User',
            change_type: 'CREATED',
            version_before: null,
            version_after: 1,
            field_changes: { name: { old: null, new: 'Siemens AG' } },
          },
        ],
        total: 1,
        offset: 0,
        limit: 50,
      });
    }
    if (path.endsWith(`/underlyings/${underlyingId}/usages`)) {
      return json(route, { items: [] });
    }
    if (
      path.endsWith(`/underlyings/${underlyingId}/verify`) &&
      request.method() === 'POST'
    ) {
      currentSummary = { ...currentSummary, quality_status: 'VERIFIED', version: 2 };
      return json(route, currentSummary);
    }
    if (
      path.endsWith(`/underlyings/${underlyingId}/deactivate`) &&
      request.method() === 'POST'
    ) {
      currentSummary = { ...currentSummary, lifecycle_status: 'INACTIVE', version: 2 };
      return json(route, currentSummary);
    }
    if (path.endsWith(`/underlyings/${underlyingId}`) && request.method() === 'GET') {
      return json(route, {
        ...currentSummary,
        listings: [
          {
            ...listing,
            lifecycle_status: currentSummary.lifecycle_status,
            version: currentSummary.version,
          },
        ],
      });
    }
    if (path.endsWith(`/underlyings/${underlyingId}`) && request.method() === 'PATCH') {
      currentSummary = { ...currentSummary, name: 'Siemens Energy AG', version: 2 };
      return json(route, currentSummary);
    }
    if (path.endsWith(`/underlyings/${underlyingId}`) && request.method() === 'DELETE') {
      deleted = true;
      return route.fulfill({ status: 204, body: '' });
    }
    if (path.endsWith('/underlyings') && request.method() === 'POST') {
      currentSummary = { ...summary };
      deleted = false;
      return json(route, currentSummary, 201);
    }
    if (path.endsWith('/underlyings') && request.method() === 'GET') {
      const lifecycleStatus = url.searchParams.get('lifecycle_status');
      const matchesLifecycle =
        lifecycleStatus === null || lifecycleStatus === currentSummary.lifecycle_status;
      const items = !deleted && matchesLifecycle ? [currentSummary] : [];
      return json(route, { items, total: items.length, offset: 0, limit: 25 });
    }

    return json(
      route,
      {
        code: 'E2E_ROUTE_MISSING',
        message: `${request.method()} ${path}`,
        details: [],
        timestamp: now,
      },
      500,
    );
  });
}

test.beforeEach(async ({ page }) => installMarketApi(page));

test('searches and filters the basiswert list server-side', async ({ page }) => {
  const searchRequest = page.waitForRequest(
    (request) =>
      request.url().includes('/api/v1/underlyings?') && request.url().includes('q=Siemens'),
  );
  await page.goto('/underlyings');
  await expect(page.getByRole('heading', { name: 'Basiswerte' })).toBeVisible();
  await expect(page.getByText('SIE · Xetra · EUR')).toBeVisible();

  await page.getByPlaceholder('Name, Ticker, ISIN oder WKN').fill('Siemens');
  await page.getByRole('button', { name: 'Suchen' }).click();
  const request = await searchRequest;
  expect(new URL(request.url()).searchParams.get('q')).toBe('Siemens');
});

test('creates an underlying with its primary listing', async ({ page }) => {
  await page.goto('/underlyings/new');
  await page.getByLabel('Name *').fill('Siemens AG');
  await page.getByLabel('ISIN').fill('DE0007236101');
  await page.getByLabel('WKN').fill('723610');
  await page.getByLabel('Ticker *').fill('SIE');

  const createRequest = page.waitForRequest(
    (request) => request.url().endsWith('/api/v1/underlyings') && request.method() === 'POST',
  );
  await page.getByRole('button', { name: 'Speichern' }).click();
  const request = await createRequest;
  expect(request.postDataJSON()).toMatchObject({
    name: 'Siemens AG',
    primary_listing: {
      trading_venue_id: venueId,
      ticker: 'SIE',
      currency_code: 'EUR',
      is_primary: true,
    },
  });
  await expect(page).toHaveURL(`/underlyings/${underlyingId}`);
});

test('shows detail history and verifies using the current version', async ({ page }) => {
  await page.goto(`/underlyings/${underlyingId}`);
  await expect(page.getByRole('heading', { name: 'Siemens AG' })).toBeVisible();
  await expect(page.getByText('E2E User')).toBeVisible();
  await expect(page.getByText('Keine fachlichen Verwendungen vorhanden.')).toBeVisible();

  const verifyRequest = page.waitForRequest((request) =>
    request.url().endsWith(`/api/v1/underlyings/${underlyingId}/verify`),
  );
  await page.getByRole('button', { name: 'Verifizieren' }).click();
  const request = await verifyRequest;
  expect(request.postDataJSON()).toEqual({ version: 1 });
});

test('keeps a deactivated underlying discoverable so it can be deleted and recreated', async ({
  page,
}) => {
  page.on('dialog', (dialog) => dialog.accept());

  await page.goto(`/underlyings/${underlyingId}`);
  const deactivateRequest = page.waitForRequest((request) =>
    request.url().endsWith(`/api/v1/underlyings/${underlyingId}/deactivate`),
  );
  await page.getByRole('button', { name: 'Deaktivieren' }).click();
  expect((await deactivateRequest).postDataJSON()).toEqual({ version: 1 });
  await expect(page.getByRole('button', { name: 'Reaktivieren' })).toBeVisible();

  await page.getByRole('link', { name: '← Basiswerte', exact: true }).click();
  await expect(page.getByRole('link', { name: 'Siemens AG' })).toBeVisible();

  await page.getByRole('link', { name: 'Siemens AG' }).click();
  const deleteRequest = page.waitForRequest(
    (request) =>
      request.url().includes(`/api/v1/underlyings/${underlyingId}?`) &&
      request.method() === 'DELETE',
  );
  await page.getByRole('button', { name: 'Löschen' }).click();
  expect(new URL((await deleteRequest).url()).searchParams.get('version')).toBe('2');
  await expect(page).toHaveURL('/underlyings');
  await expect(page.getByRole('link', { name: 'Siemens AG' })).not.toBeVisible();

  await page.getByRole('link', { name: 'Basiswert anlegen' }).click();
  await page.getByLabel('Name *').fill('Siemens AG');
  await page.getByLabel('ISIN').fill('DE0007236101');
  await page.getByLabel('WKN').fill('723610');
  await page.getByLabel('Ticker *').fill('SIE');

  const createRequest = page.waitForRequest(
    (request) => request.url().endsWith('/api/v1/underlyings') && request.method() === 'POST',
  );
  await page.getByRole('button', { name: 'Speichern' }).click();
  expect((await createRequest).postDataJSON()).toMatchObject({ name: 'Siemens AG' });
  await expect(page).toHaveURL(`/underlyings/${underlyingId}`);
});
