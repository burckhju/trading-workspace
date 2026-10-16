import { expect, test, type Page } from '@playwright/test';

// UI navigation contract only: every API call is intercepted with synthetic data.
// These PATCHes do not reach the backend or mutate user/reference data.
const venueId = '00000000-0000-4000-8001-000000000001';
const itemName = (index: number) => `Testbasiswert ${String(index).padStart(2, '0')}`;
async function installApi(page: Page) {
  const writes: { path: string; body: unknown }[] = [];
  const items = Array.from({ length: 60 }, (_, index) => ({
    id: `00000000-0000-4000-8000-${String(index + 1).padStart(12, '0')}`,
    type: 'STOCK',
    name: itemName(index + 1),
    isin: null,
    wkn: null,
    lifecycle_status: 'ACTIVE',
    quality_status: 'COMPLETE',
    version: 1,
    created_at: '2026-09-01T12:00:00Z',
    updated_at: '2026-09-01T12:00:00Z',
    primary_listing: null,
    listings: [],
  }));
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const json = (body: unknown, status = 200) =>
      route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify(body),
      });
    if (path.endsWith('/market-reference-data/trading-venues'))
      return json({
        items: [
          {
            id: venueId,
            mic: 'XETR',
            name: 'Xetra',
            country_code: 'DE',
            timezone: 'Europe/Berlin',
            reference_version: 'test',
          },
        ],
      });
    if (path.endsWith('/market-reference-data/currencies'))
      return json({
        items: [
          {
            code: 'EUR',
            name: 'Euro',
            minor_unit: 2,
            reference_version: 'test',
          },
        ],
      });
    if (path.endsWith('/audit-events')) return json({ items: [], total: 0, limit: 50, offset: 0 });
    if (path.endsWith('/usages')) return json({ items: [] });
    if (path.endsWith('/underlyings') && request.method() === 'GET') {
      const offset = Number(url.searchParams.get('offset') ?? 0);
      return json({
        items: items.slice(offset, offset + 25),
        total: items.length,
        offset,
        limit: 25,
      });
    }
    const item = items.find((item) => path === `/api/v1/underlyings/${item.id}`);
    if (item && request.method() === 'GET') return json(item);
    if (item && request.method() === 'PATCH') {
      const body = request.postDataJSON();
      writes.push({ path, body });
      item.name = body.name;
      item.version += 1;
      return json(item);
    }
    return json({ message: `Unmapped test API: ${request.method()} ${path}` }, 500);
  });
  return { writes, items };
}

for (const pageNumber of [2, 3]) {
  test(`returns to underlying page ${pageNumber} after saving, including reload and filters`, async ({
    page,
  }) => {
    const { writes, items } = await installApi(page);
    await page.goto('/underlyings');
    await expect(page.getByRole('link', { name: itemName(1), exact: true })).toBeVisible();
    await page.getByRole('textbox', { name: 'Suche', exact: true }).fill('Test');
    await page.getByRole('button', { name: 'Suchen', exact: true }).click();
    await page.getByRole('combobox', { name: 'Status', exact: true }).selectOption('ACTIVE');
    await page.getByRole('combobox', { name: 'Markt', exact: true }).selectOption(venueId);
    await page.getByRole('combobox', { name: 'Währung', exact: true }).selectOption('EUR');
    for (let current = 1; current < pageNumber; current++) {
      await page.getByRole('button', { name: 'Weiter', exact: true }).click();
      await expect(
        page.getByRole('link', {
          name: itemName(current * 25 + 1),
          exact: true,
        }),
      ).toBeVisible();
    }
    const listUrl = page.url();
    await page.reload();
    const firstIndex = (pageNumber - 1) * 25;
    await page.getByRole('link', { name: itemName(firstIndex + 1), exact: true }).click();
    await page.getByRole('link', { name: 'Bearbeiten', exact: true }).click();
    await page.reload();
    await page.getByRole('textbox', { name: 'Name *', exact: true }).fill('Testbasiswert gepflegt');
    expect(writes).toHaveLength(0);
    await page.getByRole('button', { name: 'Speichern', exact: true }).click();
    await expect(page).toHaveURL(listUrl);
    await expect(
      page.getByRole('link', { name: 'Testbasiswert gepflegt', exact: true }),
    ).toBeVisible();
    await expect(page.getByRole('status')).toHaveText(`60 Treffer · Seite ${pageNumber} von 3`);
    await expect(page.getByRole('textbox', { name: 'Suche', exact: true })).toHaveValue('Test');
    await expect(page.getByRole('combobox', { name: 'Status', exact: true })).toHaveValue('ACTIVE');
    await expect(page.getByRole('combobox', { name: 'Markt', exact: true })).toHaveValue(venueId);
    await expect(page.getByRole('combobox', { name: 'Währung', exact: true })).toHaveValue('EUR');
    expect(writes).toEqual([
      {
        path: `/api/v1/underlyings/${items[firstIndex].id}`,
        body: {
          version: 1,
          name: 'Testbasiswert gepflegt',
          isin: null,
          wkn: null,
        },
      },
    ]);
  });
}

test('keeps return pages independent in two tabs and cancels without mutation', async ({
  page,
  context,
}) => {
  const other = await context.newPage();
  const first = await installApi(page);
  const second = await installApi(other);
  await page.goto('/underlyings?offset=25');
  await other.goto('/underlyings?offset=50');
  await page.getByRole('link', { name: itemName(26), exact: true }).click();
  await other.getByRole('link', { name: itemName(51), exact: true }).click();
  await page.getByRole('link', { name: 'Bearbeiten', exact: true }).click();
  await page.getByRole('textbox', { name: 'Name *', exact: true }).fill('Nicht speichern');
  await page.getByRole('link', { name: 'Abbrechen', exact: true }).click();
  await expect(page.getByRole('link', { name: itemName(26), exact: true })).toBeVisible();
  await expect(page).toHaveURL('/underlyings?offset=25');
  await other.getByRole('link', { name: '← Basiswerte', exact: true }).click();
  await expect(other.getByRole('link', { name: itemName(51), exact: true })).toBeVisible();
  await expect(other).toHaveURL('/underlyings?offset=50');
  expect(first.writes).toHaveLength(0);
  expect(second.writes).toHaveLength(0);
  await other.close();
});
