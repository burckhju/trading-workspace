import { expect, test, type Page, type Route } from '@playwright/test';

const venueId = '00000000-0000-4000-8001-000000000001';
const secondVenueId = '00000000-0000-4000-8001-000000000002';

const venue = {
  id: venueId,
  mic: 'XETR',
  name: 'Xetra',
  country_code: 'DE',
  timezone: 'Europe/Berlin',
  reference_version: 'FT-001-V1',
};

const secondVenue = {
  id: secondVenueId,
  mic: 'XFRA',
  name: 'Frankfurt',
  country_code: 'DE',
  timezone: 'Europe/Berlin',
  reference_version: 'FT-001-V1',
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function installReferenceData(page: Page, venues: typeof venue[]) {
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;

    if (path.endsWith('/market-reference-data/trading-venues')) {
      return json(route, { items: venues });
    }
    if (path.endsWith('/market-reference-data/currencies')) {
      return json(route, {
        items: [{ code: 'EUR', name: 'Euro', minor_unit: 2, reference_version: 'FT-001-V1' }],
      });
    }

    return json(
      route,
      {
        code: 'E2E_ROUTE_MISSING',
        message: `${request.method()} ${path}`,
        details: [],
        timestamp: '2026-08-13T12:00:00Z',
      },
      500,
    );
  });
}

test('uses the only active trading venue without asking the user', async ({ page }) => {
  await installReferenceData(page, [venue]);

  await page.goto('/underlyings/new');

  await expect(page.getByLabel('Automatisch gewählter Markt')).toContainText('Xetra · XETR');
  await expect(page.getByLabel('Markt *')).toHaveCount(0);
  await expect(
    page.getByText('Automatisch übernommen, weil genau ein aktiver Handelsplatz verfügbar ist.'),
  ).toBeVisible();
});

test('asks for a trading venue only when multiple active venues are available', async ({ page }) => {
  await installReferenceData(page, [venue, secondVenue]);

  await page.goto('/underlyings/new');

  const market = page.getByLabel('Markt *');
  await expect(market).toBeVisible();
  await expect(market.locator('option')).toHaveCount(2);
  await market.selectOption(secondVenueId);
  await expect(market).toHaveValue(secondVenueId);
  await expect(
    page.getByText('Auswahl nur erforderlich, weil mehrere aktive Handelsplätze verfügbar sind.'),
  ).toBeVisible();
});
