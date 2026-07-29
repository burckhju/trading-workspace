import { expect, test } from '@playwright/test';

test('serves the technical workspace foundation and backend health endpoint', async ({ page, request }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Technisches Frontend-Grundgerüst' })).toBeVisible();
  await expect(page.getByText('Trading Workspace')).toBeVisible();

  const healthResponse = await request.get('/api/health');
  expect(healthResponse.ok()).toBeTruthy();
  await expect(healthResponse.json()).resolves.toMatchObject({ status: 'healthy' });
});

test('keeps browser routing available through the reverse proxy', async ({ page }) => {
  await page.goto('/unknown');

  await expect(page.getByRole('heading', { name: 'Seite nicht gefunden' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Zur Startseite' })).toHaveAttribute('href', '/');
});
