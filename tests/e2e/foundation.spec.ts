import { expect, test } from "@playwright/test";

test("serves the attention-first start page, preserved underlying entry and backend health endpoint", async ({
  page,
  request,
}) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Aktuelles" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Depot öffnen" })).toBeVisible();
  await page.goto("/underlyings");
  await expect(page.getByRole("heading", { name: "Basiswerte" })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Basiswert anlegen" }),
  ).toBeVisible();

  const healthResponse = await request.get("/api/health");
  expect(healthResponse.ok()).toBeTruthy();
  await expect(healthResponse.json()).resolves.toMatchObject({ status: "ok" });
});

test("keeps browser routing available through the reverse proxy", async ({
  page,
}) => {
  await page.goto("/unknown");

  await expect(
    page.getByRole("heading", { name: "Seite nicht gefunden" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Zur Startseite" }),
  ).toHaveAttribute("href", "/");
});
