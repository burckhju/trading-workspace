import { expect, test } from "@playwright/test";

// Display-only fixtures; no market-data, notification or economic writes.
test("workspace action cards retain product identity and navigation on a narrow screen", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const writes: string[] = [];
  page.on("request", (request) => {
    if (!["GET", "HEAD"].includes(request.method())) writes.push(request.url());
  });
  await page.route("**/operational-workspace/actions", (route) =>
    route.fulfill({
      json: {
        generated_at: "2026-09-14T12:00:00Z",
        actions: ["Alpha", "Beta"].map((name, index) => ({
          id: `synthetic-${index}`,
          source_feature: "SYNTHETIC",
          action_type: "POSITION_DATA_HEALTH",
          priority: "ACTION",
          state: "ACTIONABLE",
          title: "Produktkurs fehlt",
          detail: "Keine Orderfreigabe.",
          resource_type: "trade",
          resource_id: `synthetic-trade-${index}`,
          next_action: "Prüfen",
          target: `/trade-management?trade_id=synthetic-trade-${index}`,
          occurred_at: null,
          product_id: `synthetic-warrant-${index}`,
          product_name: `SYNTHETIC ${name} Call`,
          product_wkn: `SYN00${index}`,
          product_isin: `DE000SYN00${index}0`,
        })),
      },
    }),
  );
  await page.route("**/operational-workspace/positions", (route) =>
    route.fulfill({
      json: { generated_at: "2026-09-14T12:00:00Z", positions: [] },
    }),
  );
  await page.goto("/workspace");
  const card = page
    .getByRole("listitem")
    .filter({ hasText: "SYNTHETIC Alpha Call" });
  await expect(card).toHaveCount(1);
  await expect(card).toContainText("WKN: SYN000 · ISIN: DE000SYN0000");
  await expect(card).not.toContainText("SYNTHETIC Beta Call");
  await expect(card.getByRole("link", { name: "Öffnen" })).toHaveAttribute(
    "href",
    "/trade-management?trade_id=synthetic-trade-0",
  );
  await card.getByRole("link", { name: "Öffnen" }).focus();
  await expect(card.getByRole("link", { name: "Öffnen" })).toBeFocused();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  expect(writes).toEqual([]);
});
