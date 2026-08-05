import { expect, test } from '@playwright/test';

test('serves the FT-001 start page and backend health endpoint', async ({ page, request }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Basiswerte' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Basiswert anlegen' })).toBeVisible();

  const healthResponse = await request.get('/api/health');
  expect(healthResponse.ok()).toBeTruthy();
  await expect(healthResponse.json()).resolves.toMatchObject({ status: 'ok' });
});

test('keeps browser routing available through the reverse proxy', async ({ page }) => {
  await page.goto('/unknown');

  await expect(page.getByRole('heading', { name: 'Seite nicht gefunden' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Zur Startseite' })).toHaveAttribute('href', '/');
});
