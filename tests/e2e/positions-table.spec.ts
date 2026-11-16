import { expect, test, type Page } from "@playwright/test";
import type { HebeltraderEvidenceReport } from "../../frontend/src/features/operational_workspace/hebeltraderEvidence";
import type {
  HebeltraderTargetAssessmentRequest,
  HebeltraderTargetsReport,
} from "../../frontend/src/features/operational_workspace/hebeltraderTargets";
import {
  qualificationPreview,
  targetRequest,
} from "../../frontend/src/features/operational_workspace/test/hebeltraderQualificationFixture";
import {
  targetAssessment,
  targetReport,
} from "../../frontend/src/features/operational_workspace/test/hebeltraderTargetsFixture";
import {
  sessionReport,
  unavailableSessionReport,
} from "../../frontend/src/features/operational_workspace/test/hebeltraderSessionsFixture";
import {
  missingBidSideReport,
  originalBidReport,
  originalMarketStatusReport,
} from "../../frontend/src/features/operational_workspace/test/hebeltraderOriginalBidFixture";
import type { OperationalPosition } from "../../frontend/src/features/operational_workspace/types";

async function setup(
  page: Page,
  overrides: Record<number, Partial<OperationalPosition>> = {},
  requests: string[] = [],
) {
  let writes = 0;
  const positions = Array.from({ length: 100 }, (_, i) => ({
    trade_id: `trade-${i}`,
    position_id: `position-${i}`,
    product_name: `Optionsschein ${String(i).padStart(3, "0")}`,
    product_wkn: `WK${String(i).padStart(4, "0")}`,
    product_isin: `DE000TEST${String(i).padStart(4, "0")}`,
    underlying_name: "Gemeinsamer Basiswert",
    underlying_symbol: "BASE",
    product_symbol: null,
    opened_at: "2026-09-08T09:00:00Z",
    opened_on: "2026-09-08",
    open_quantity: 100 + i,
    average_entry_price: "0.55",
    cost_basis: "55",
    realized_gross_pnl: "0",
    stop_price: "0.25",
    target_price: "0.9",
    market_value: i === 98 ? null : `${55 + i}`,
    unrealized_gross_pnl: i === 98 ? null : `${i - 50}`,
    unrealized_pnl_usable: i !== 98,
    unrealized_pnl_reason:
      i === 98 ? "WARRANT_QUOTE_MISSING" : "COST_BASIS_CURRENCY_MATCHED",
    valuation_currency: i % 2 ? "CHF" : "EUR",
    valuation_status: i === 98 ? "MISSING" : i % 3 ? "INDICATIVE" : "AVAILABLE",
    monitoring_status: "OK",
    analysis_warning: i % 3 ? "INDICATIVE" : null,
    quote_source: "FIXTURE",
    quote_observed_at: "2026-09-11T14:00:00Z",
    open_alert_count: i === 0 ? 1 : 0,
    open_alert_types: i === 0 ? ["STOP_REACHED"] : [],
    attention_state: i === 0 ? "ALERT" : "OK",
    target: `/trade-management?trade_id=trade-${i}`,
    ...overrides[i],
  }));
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    if (req.method() !== "GET") writes++;
    const url = new URL(req.url());
    const path = url.pathname;
    requests.push(`${req.method()} ${path}`);
    let body: unknown = [];
    if (path.endsWith("/operational-workspace/actions"))
      body = { generated_at: "2026-09-13T09:00:00Z", actions: [] };
    if (path.endsWith("/operational-workspace/positions"))
      body = { generated_at: "2026-09-13T09:00:00Z", positions };
    if (path.endsWith("/alert-projection")) {
      const id = path.split("/").at(-2)!;
      body = {
        trade_id: id,
        position_id: id.replace("trade-", "position-"),
        quality_status: "AVAILABLE",
        alert_level: "NORMAL",
        attention_required: false,
        reason: "NO_POSITION_ATTENTION_REQUIRED",
        candidate_stop: null,
        latest_price: null,
        phase: null,
        policy_version: "V1",
        dynamic_stop_policy_version: "V1",
        analysis_run_id: null,
      };
    }
    const coverage = path.match(
      /^\/(?:api\/)?api\/v1\/trade-position\/trades\/trade-(0|[1-9]\d?)\/hebeltrader-evidence$/,
    );
    if (coverage) {
      const id = coverage[1];
      expect(req.method()).toBe("GET");
      expect([...url.searchParams.entries()]).toEqual([
        ["position_id", `position-${id}`],
      ]);
      const report: HebeltraderEvidenceReport = {
        definition_version: "hebeltrader-evidence-v1",
        trade_id: `trade-${id}`,
        position_id: `position-${id}`,
        product_id: `product-${id}`,
        underlying_id: "underlying-1",
        basis_id: `synthetic-basis-${id}`,
        read_started_at: "2026-09-13T09:00:00Z",
        read_completed_at: "2026-09-13T09:00:01Z",
        evidence_revision_id: null,
        evidence_recorded_at: null,
        coverage_status: "INCOMPLETE",
        items: [
          {
            key: "executions",
            label: "Ausführungen",
            status: "PRESENT",
            detail: `Gespeicherte Ausführung von position-${id}.`,
            affected_rules: ["B10", "B53"],
            clarification: null,
            references: [`execution:buy-${id}`],
          },
          {
            key: "source",
            label: "Historische Quelle",
            status: "MISSING",
            detail: "Historische Quellenversion fehlt.",
            affected_rules: ["B01", "B02"],
            clarification: "Historische Ausgabe zuordnen.",
            references: [],
          },
        ],
        original_z1_quantity: null,
        assigned_z1_sold_quantity: null,
        personal_underlying_entry: null,
        underlying_currency: null,
        source: null,
        implementation_status: "F207_4_EVIDENCE_ONLY",
        operation_status: "NOT_ASSESSED",
        baseline_id: "HEBELTRADER_CONFIRMED_BASELINE",
        baseline_version: "1.0.0",
      };
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(report),
      });
    }
    const originalBid = path.match(
      /^\/(?:api\/)?api\/v1\/position-monitoring\/trades\/trade-(0|[1-9]\d?)\/hebeltrader-original-bid$/,
    );
    if (originalBid) {
      const id = originalBid[1];
      expect(req.method()).toBe("GET");
      expect([...url.searchParams.entries()]).toEqual([
        ["position_id", `position-${id}`],
      ]);
      const report = (
        id === "97"
          ? missingBidSideReport
          : id === "99"
            ? originalMarketStatusReport
            : originalBidReport
      )({
        trade_id: `trade-${id}`,
        position_id: `position-${id}`,
        product_id: `product-${id}`,
      });
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(report),
      });
    }
    const sessions = path.match(
      /^\/(?:api\/)?api\/v1\/position-monitoring\/trades\/trade-(0|[1-9]\d?)\/hebeltrader-sessions$/,
    );
    if (sessions) {
      const id = sessions[1];
      expect(req.method()).toBe("GET");
      expect([...url.searchParams.entries()]).toEqual([
        ["position_id", `position-${id}`],
      ]);
      const report = (id === "97" ? unavailableSessionReport : sessionReport)({
        trade_id: `trade-${id}`,
        position_id: `position-${id}`,
        product_id: `product-${id}`,
        basis_id: `synthetic-session-basis-${id}`,
      });
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(report),
      });
    }
    const targets = path.match(
      /^\/(?:api\/)?api\/v1\/position-monitoring\/trades\/trade-(0|[1-9]\d?)\/hebeltrader-targets$/,
    );
    if (targets) {
      const id = targets[1];
      expect(req.method()).toBe("GET");
      expect([...url.searchParams.entries()]).toEqual([
        ["position_id", `position-${id}`],
      ]);
      const report: HebeltraderTargetsReport = {
        definition_version: "hebeltrader-targets-v1",
        baseline_id: "HEBELTRADER_CONFIRMED_BASELINE",
        baseline_version: "1.0.0",
        implementation_status: "F207_2_TARGET_HISTORY_ONLY",
        operation_status: "NOT_ACTIVATED",
        trade_id: `trade-${id}`,
        position_id: `position-${id}`,
        current_basis_id: `synthetic-target-basis-${id}`,
        currentness: "NO_ASSESSMENT",
        position_state: "OPEN",
        read_started_at: "2026-09-13T09:00:00Z",
        read_completed_at: "2026-09-13T09:00:01Z",
        assessment_count: 0,
        inputs: {
          source_version_id: null,
          source_scale_reference: null,
          price_history_fingerprint: `synthetic-prices-${id}`,
          listing_binding_fingerprint: null,
          qualification_reusable: false,
          available_price_rows: 0,
          issues: ["SAVED_PRICE_QUALIFICATION_MISSING"],
        },
        latest_assessment: null,
      };
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(report),
      });
    }
    // Navigation may open a management page, but must never record a trade.
    if (path.includes("/trade-position/trades/"))
      return route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({
          message: "Fixture navigation only",
          code: "NOT_FOUND",
        }),
      });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
  return () => writes;
}

test("100 positions: global search, colored statuses, pagination, details and return context without writes", async ({
  page,
}, testInfo) => {
  const writes = await setup(page);
  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto("/workspace");
  await expect(
    page.getByRole("heading", { name: "Offene Positionen · 100" }),
  ).toBeVisible();
  await expect(page.locator("tbody > tr[data-position-id]")).toHaveCount(25);
  await expect(
    page.getByText("! Kritischer Hinweis", { exact: true }),
  ).toHaveClass(/text-rose-200/);
  await page.getByRole("button", { name: "Nächste Seite" }).click();
  await expect(page.getByRole("status")).toContainText("Seite 2 von 4");
  const search = page.getByRole("searchbox");
  await search.fill("DE000TEST0099");
  await expect(page.locator("tbody > tr[data-position-id]")).toHaveCount(1);
  await expect(
    page.getByText("Optionsschein 099", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Details", exact: true }).click();
  await expect(
    page.getByRole("region", { name: "Details Optionsschein 099" }),
  ).toContainText("Quelle: FIXTURE");
  await page
    .getByRole("link", { name: "Trade verwalten", exact: true })
    .click();
  await expect(page).toHaveURL(/trade-management\?trade_id=trade-99$/);
  await page.goBack();
  await expect(search).toHaveValue("DE000TEST0099");
  await page.getByRole("button", { name: "Ansicht zurücksetzen" }).click();
  await expect(
    page.getByRole("region", { name: "Details Optionsschein 099" }),
  ).toHaveCount(0);
  await page.getByLabel("Zeilen pro Seite").selectOption("100");
  await expect(page.locator("tbody > tr[data-position-id]")).toHaveCount(100);
  await page
    .getByRole("button", { name: "Fachliche Hinweise", exact: true })
    .click();
  await expect(page.locator("tbody > tr[data-position-id]")).toHaveCount(1);
  await page.getByRole("button", { name: "Alle offenen Positionen" }).click();
  await page.getByRole("button", { name: /^Nicht realisierter G\/V/ }).click();
  await expect(
    page.getByRole("columnheader", { name: /Nicht realisierter G\/V/ }),
  ).toHaveAttribute("aria-sort", "ascending");
  await expect(
    page.locator("tbody > tr[data-position-id]").last(),
  ).toContainText("Optionsschein 098");
  await page.getByLabel("Zeilen pro Seite").selectOption("25");
  await testInfo.attach("Positionsübersicht desktop (synthetische Testdaten)", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
  expect(writes()).toBe(0);
});

test("valuation notices preserve keyboard details, existing reads and explicit history navigation", async ({
  page,
}) => {
  const requests: string[] = [];
  const writes = await setup(
    page,
    {
      96: { valuation_status: "AVAILABLE", analysis_warning: null },
      97: { valuation_status: "LAST_AVAILABLE", analysis_warning: null },
      99: {
        valuation_status: "LAST_AVAILABLE",
        analysis_warning: "OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY",
      },
    },
    requests,
  );
  await page.goto("/workspace");
  await expect(
    page.getByRole("heading", { name: "Offene Positionen · 100" }),
  ).toBeVisible();
  await expect(page.getByText(/Positionssignale werden ergänzt/)).toHaveCount(
    0,
  );
  const quoteTime = await page.evaluate(() =>
    new Date("2026-09-11T14:00:00Z").toLocaleString("de-DE"),
  );

  for (const id of [96, 97, 99]) {
    await page.getByRole("searchbox").fill(`WK00${id}`);
    const details = page.getByRole("button", { name: "Details", exact: true });
    await details.focus();
    const before = requests.length;
    await page.keyboard.press("Enter");
    const expanded = page.getByRole("button", {
      name: "Details schließen",
      exact: true,
    });
    await expect(expanded).toHaveAttribute("aria-expanded", "true");
    await expect(expanded).toBeFocused();
    const region = page.getByRole("region", {
      name: `Details Optionsschein 0${id}`,
    });
    await expect(region).toContainText(
      `Quelle: FIXTURE · Kurszeitpunkt: ${quoteTime}`,
    );
    await expect(
      region.getByText(`${55 + id},00 ${id % 2 ? "CHF" : "EUR"}`, {
        exact: true,
      }),
    ).toBeVisible();
    await expect(region).not.toContainText("veraltet");
    await expect(region).not.toContainText("verfügbaren Referenzkurs");
    if (id === 97 || id === 99) {
      await expect(region).toContainText("Letzter verfügbarer Kursstand");
    }
    if (id === 99)
      await expect(region).toContainText(/die Analyse ist indikativ/i);

    // Detail children read on expansion; the passive valuation notice adds none.
    await expect(
      region.getByText("Kursverlauf konnte nicht geladen werden."),
    ).toBeVisible();
    await expect(
      region.getByText("Risikoauswertung konnte nicht geladen werden."),
    ).toBeVisible();
    const coverage = region.getByRole("region", {
      name: "Hebeltrader-Belegabdeckung",
    });
    await expect(coverage).toContainText("Belege noch unvollständig");
    await expect(coverage).toContainText(
      `Gespeicherte Ausführung von position-${id}.`,
    );
    await expect(coverage).toContainText("Ausführungen: Vorhanden");
    await expect(coverage).toContainText("Historische Quelle: Fehlt");
    await expect(coverage).toContainText(
      "Klärung: Historische Ausgabe zuordnen.",
    );
    await expect(coverage).toContainText(
      "F207-4: Evidenzverknüpfung. Keine Baseline-Regelauswertung.",
    );
    await expect(coverage).toContainText("Durch diesen Read nicht geprüft.");
    const targets = region.getByRole("region", {
      name: "Hebeltrader-Zielhistorie",
    });
    await expect(targets).toContainText("Noch keine gespeicherte Prüfung");
    await expect(targets).toContainText(
      "nicht als laufende Überwachung aktiviert",
    );
    await expect(targets).toContainText(
      "Die Vergleichsqualifikation für Preisbelege, Listing und Maßstab fehlt",
    );
    await expect(
      targets.getByRole("button", { name: "Gespeicherte Belege prüfen" }),
    ).toBeEnabled();
    const sessions = region.getByRole("region", {
      name: "Hebeltrader-Basiswertsitzungen",
    });
    await expect(sessions).toContainText(
      id === 97 ? "Nicht beurteilbar" : "2 abgeschlossene Basiswertsitzungen",
    );
    await expect(sessions).toContainText(
      "B04, B05, B06 und B58 sind nicht ausgewertet",
    );
    await expect(sessions).toContainText(
      "nicht als laufende Überwachung aktiviert",
    );
    await expect(sessions).toContainText(
      "serverseitiger Lesezeitpunkt, keine Original-BID-Zeit",
    );
    if (id === 97) {
      await expect(sessions).toContainText(
        "Eine ausdrücklich zugeordnete Kalenderrevision fehlt.",
      );
      await expect(sessions).not.toContainText(
        "0 abgeschlossene Basiswertsitzungen",
      );
    } else {
      await expect(
        sessions.getByRole("table", {
          name: "Dokumentierte Basiswert-Kalendertage",
        }),
      ).toContainText("Dokumentiert geschlossen");
      await sessions
        .getByText("Kalenderbindung, Quelle und Zeitstände")
        .click();
      await expect(sessions.getByText("a".repeat(64))).toBeVisible();
      await expect(sessions.getByText("b".repeat(64))).toBeVisible();
      await expect(sessions).toContainText("keine unabhängige Verifikation");
      await expect(
        sessions.locator('time[datetime="2026-08-31"]'),
      ).toBeVisible();
      await expect(
        sessions.locator('time[datetime="2026-08-31T00:00:00Z"]'),
      ).toHaveCount(0);
      await sessions
        .getByText("Kalenderbindung, Quelle und Zeitstände")
        .click();
    }
    await expect(sessions.getByRole("textbox")).toHaveCount(0);
    await expect(sessions.getByRole("button")).toHaveCount(0);
    const original = region.getByRole("region", {
      name: "Hebeltrader-Original-Geldkurs",
    });
    await expect(original).toContainText(
      "Teilbelege vorhanden; Gesamtqualifikation offen",
    );
    await expect(original).toContainText(
      "B04, B05, B06 und B58 sind nicht ausgewertet",
    );
    await expect(original).toContainText(
      id === 99
        ? "Historischer Produkt-Preismaßstab · Teilvoraussetzung belegt"
        : "Historischer Produkt-Preismaßstab · Beleg fehlt",
    );
    await expect(original).toContainText(
      id === 99
        ? "Verifizierter Produktmarktstatus · Beleg fehlt"
        : "Verifizierte offene Produktsitzung · Beleg fehlt",
    );
    await expect(original).toContainText(
      "nicht als laufende Überwachung aktiviert",
    );
    await expect(
      original
        .getByRole("list", {
          name: "Voraussetzungen für den Original-Geldkurs",
        })
        .getByRole("listitem"),
    ).toHaveCount(8);
    const sideTime = original
      .getByText("Exakte Original-BID-Zeit", { exact: true })
      .locator("..");
    if (id === 97) {
      await expect(sideTime).toContainText("Nicht belegt");
      await expect(original).toContainText(
        "Keine Zählung zur BID-Zeit verfügbar",
      );
      await expect(original).toContainText(
        "Gemeinsame Snapshotzeit, ASK-Zeit und Abrufzeit ersetzen sie nicht",
      );
    } else {
      await expect(sideTime).toContainText("2026-09-21T13:00:00Z");
      await expect(original).toContainText("1.234567890123 EUR");
      await expect(original).toContainText("20 abgeschlossene Sitzungen");
      await original
        .getByText("Geldkursquelle, Positionsbasis und Kalenderbelege")
        .click();
      await expect(original).toContainText("2026-09-21T12:59:58Z");
      await expect(original).toContainText(
        "OPEN · Kein verifizierter Live-Marktstatus",
      );
      await expect(original).toContainText(
        "Zeitpunkt der Speicherung nicht aufgezeichnet",
      );
      await expect(
        original.getByText("SHA-256 des gespeicherten JSON-Payloads", {
          exact: true,
        }),
      ).toBeVisible();
      await expect(original).toContainText("f".repeat(64));
      if (id === 99) {
        await expect(original).toContainText("Originaler Produktmarktstatus");
        await expect(original).toContainText(
          "2026-09-21T15:00:00+02:00 · Feld market_status_at",
        );
        await expect(original).toContainText("OPEN · Feld market_status");
        await expect(original).toContainText("SYNTHETIC-FRANKFURT");
        await expect(original).toContainText(
          "Bezugspunkt entspricht der Statusbeobachtung",
        );
        await expect(original).toContainText(
          "Bezugspunkt liegt nach der Statusbeobachtung",
        );
        await expect(original).toContainText(
          "Ob der Produktmarkt zum Lesestand offen oder geschlossen ist, ist damit nicht belegt",
        );
        await expect(original).toContainText(
          "Eine Originalstatuszeit belegt eine Punktbeobachtung, kein Gültigkeitsintervall",
        );
        await expect(original).toContainText(
          "Spätere Statusmeldungen, auch CLOSED oder SUSPENDED ohne geeigneten Geldkurs, können darin fehlen",
        );
        await expect(original).toContainText("synthetic-issuer-correction-2");
        await expect(original).toContainText(
          "2026-09-21T13:00:01Z ausschließlich",
        );
        await expect(original).toContainText(
          "Dokumentierte menschliche Prüfung, keine unabhängige Verifikation",
        );
        await expect(original).toContainText(
          "product-scale-revision-2 · Revision 2 · ersetzt product-scale-revision-1",
        );
        await expect(original).toContainText("c".repeat(64));
        const purchases = original.getByRole("table", {
          name: "Kaufbeiträge und dokumentierter Produktmaßstab",
        });
        await expect(purchases.getByRole("row")).toHaveCount(3);
        await expect(purchases).toContainText(
          "Ursprünglich 10 Stück · Restbeitrag 5 Stück",
        );
        await expect(purchases).toContainText("Restbeitrag 2 Stück");
        await expect(purchases).toContainText(
          "Originalpreis 1.2067901235 EUR je Stück",
        );
        await expect(purchases).toContainText("Ersetzt: original-buy-1");
        await expect(purchases).toContainText("Keine bekannte Kaufuhrzeit");
      }
      await original
        .getByText("Geldkursquelle, Positionsbasis und Kalenderbelege")
        .click();
    }
    await expect(original.getByRole("textbox")).toHaveCount(0);
    await expect(
      original.getByRole("button", {
        name: "Gespeicherten Geldkursbeleg erneut lesen",
      }),
    ).toBeEnabled();
    expect(requests.slice(before).sort()).toEqual([
      expect.stringMatching(
        new RegExp(
          `^GET (?:/api)?/api/v1/position-monitoring/trades/trade-${id}/hebeltrader-original-bid$`,
        ),
      ),
      expect.stringMatching(
        new RegExp(
          `^GET (?:/api)?/api/v1/position-monitoring/trades/trade-${id}/hebeltrader-sessions$`,
        ),
      ),
      expect.stringMatching(
        new RegExp(
          `^GET (?:/api)?/api/v1/position-monitoring/trades/trade-${id}/hebeltrader-targets$`,
        ),
      ),
      expect.stringMatching(
        new RegExp(
          `^GET (?:/api)?/api/v1/position-monitoring/trades/trade-${id}/risk$`,
        ),
      ),
      expect.stringMatching(
        new RegExp(
          `^GET (?:/api)?/api/v1/trade-position/trades/trade-${id}/hebeltrader-evidence$`,
        ),
      ),
      expect.stringMatching(
        new RegExp(
          `^GET (?:/api)?/api/v1/trade-position/trades/trade-${id}/price-history$`,
        ),
      ),
    ]);
    await expect(page).toHaveURL(/\/workspace$/);
    const history = region.getByRole("link", {
      name: "Kauf-/Verkaufsdaten und Historie öffnen",
    });
    await expect(history).toHaveAttribute(
      "href",
      `/trade-management?trade_id=trade-${id}#execution-dates`,
    );
    expect(writes()).toBe(0);
    if (id === 99) {
      await history.focus();
      await page.keyboard.press("Enter");
      await expect(page).toHaveURL(/trade_id=trade-99#execution-dates$/);
    } else {
      await expanded.focus();
      await page.keyboard.press("Enter");
      await expect(details).toHaveAttribute("aria-expanded", "false");
      await expect(details).toBeFocused();
      await expect(region).toHaveCount(0);
      expect(requests).toHaveLength(before + 6);
    }
  }
  expect(writes()).toBe(0);
});

test("narrow layout: bounded horizontal scroll and keyboard-accessible details and sale navigation", async ({
  page,
}, testInfo) => {
  const writes = await setup(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/workspace");
  const search = page.getByRole("searchbox");
  await search.fill("WK0099");
  const searchBox = await search.boundingBox();
  const sortBox = await page.getByLabel("Sortierung").boundingBox();
  expect(searchBox).not.toBeNull();
  expect(sortBox).not.toBeNull();
  expect(searchBox!.y + searchBox!.height).toBeLessThanOrEqual(sortBox!.y);
  await expect(
    page.getByText("Optionsschein 099", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);
  const scroll = page.getByRole("region", {
    name: "Positionstabelle, horizontal und vertikal scrollbar",
  });
  expect(await scroll.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(
    true,
  );
  const details = page.getByRole("button", { name: "Details", exact: true });
  await details.focus();
  await page.keyboard.press("Enter");
  // The accessible label changes to “Details schließen” after activation.
  const expanded = page.getByRole("button", {
    name: "Details schließen",
    exact: true,
  });
  await expect(expanded).toHaveAttribute("aria-expanded", "true");
  await expect(expanded).toBeFocused();
  await expect(
    page.getByRole("region", { name: "Details Optionsschein 099" }),
  ).toBeVisible();
  const detailRegion = page.getByRole("region", {
    name: "Details Optionsschein 099",
  });
  // Details remain readable when the table is scrolled to its actions on the right.
  const detailBox = await detailRegion.boundingBox();
  expect(detailBox).not.toBeNull();
  expect(detailBox!.x).toBeGreaterThanOrEqual(0);
  expect(detailBox!.x + detailBox!.width).toBeLessThanOrEqual(390);
  await expect(detailRegion).toContainText("Quelle: FIXTURE");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);
  await testInfo.attach("Positionsübersicht mobile (synthetische Testdaten)", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
  await page
    .getByRole("link", { name: "Verkauf erfassen", exact: true })
    .click();
  await expect(page).toHaveURL(/trade_id=trade-99#sale-capture$/);
  expect(writes()).toBe(0);
});

test("historical qualification preserves a scoped draft and recovers exactly one explicit request without activation", async ({
  page,
}) => {
  const requests: string[] = [];
  const otherWrites = await setup(page, {}, requests);
  const preview = qualificationPreview();
  preview.report.trade_id = "trade-99";
  preview.report.position_id = "position-99";
  preview.report.current_basis_id = "a".repeat(64);
  preview.entry.product_id = "product-99";
  preview.source!.product_id = "product-99";
  preview.source!.product.binding.instrument_id = "product-99";
  let currentReport = preview.report;
  let submitted: HebeltraderTargetAssessmentRequest | null = null;
  let assessmentPosts = 0;
  const specificRequests: string[] = [];
  const routePath =
    /^\/(?:api\/)?api\/v1\/position-monitoring\/trades\/trade-99\/hebeltrader-targets(?:\/qualification-preview|\/assessments|\/requests\/[0-9a-f-]{36})?$/;
  const concreteReference =
    "Synthetisches Listingarchiv 2026, Seite 7; Zeit, Währung und gemeinsamer Originalmaßstab geprüft.";
  await page.route(
    (url) => routePath.test(url.pathname),
    async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      const path = url.pathname;
      specificRequests.push(`${request.method()} ${path}`);
      requests.push(`${request.method()} ${path}`);
      if (path.endsWith("/assessments")) {
        expect(request.method()).toBe("POST");
        expect([...url.searchParams]).toEqual([]);
        assessmentPosts += 1;
        submitted =
          request.postDataJSON() as HebeltraderTargetAssessmentRequest;
        expect(submitted).toEqual({
          position_id: "position-99",
          request_id: expect.stringMatching(
            /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
          ),
          expected_basis_id: preview.report.current_basis_id,
          expected_assessment_id: null,
          confirmation: "ASSESS_SAVED_HEBELTRADER_EVIDENCE",
          qualification: {
            ...preview.qualification_binding,
            evidence_reference: concreteReference,
            confirmation:
              "CONFIRM_HISTORICAL_LISTING_AND_UNCHANGED_ORIGINAL_SCALE",
          },
        });
        currentReport = targetReport({
          trade_id: "trade-99",
          position_id: "position-99",
          current_basis_id: preview.report.current_basis_id,
          latest_assessment: targetAssessment({
            id: "exact-request-assessment",
            basis_id: preview.report.current_basis_id,
          }),
        });
        // Synthetic recorded command with an unconfirmed response; no database/provider is contacted.
        return route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({
            code: "RESPONSE_UNAVAILABLE",
            message: "Synthetisch unbestätigte Antwort",
            details: [],
            timestamp: "2026-11-14T10:00:01Z",
          }),
        });
      }
      expect(request.method()).toBe("GET");
      expect([...url.searchParams]).toEqual([["position_id", "position-99"]]);
      if (path.includes("/requests/")) {
        expect(submitted).not.toBeNull();
        expect(path.split("/").at(-1)).toBe(submitted!.request_id);
        const receipt = targetRequest({
          trade_id: "trade-99",
          position_id: "position-99",
          request_id: submitted!.request_id,
          assessment: currentReport.latest_assessment,
          qualification: {
            ...preview.qualification_binding!,
            evidence_reference: concreteReference,
          },
        });
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(receipt),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          path.endsWith("/qualification-preview")
            ? {
                ...preview,
                report: currentReport,
                qualification: currentReport.inputs.qualification_reusable
                  ? {
                      ...preview.qualification,
                      status: "REUSABLE",
                      value: {
                        ...preview.qualification_binding,
                        evidence_reference: concreteReference,
                      },
                      contained_in_assessment_id:
                        currentReport.latest_assessment!.id,
                      contained_in_recorded_at:
                        currentReport.latest_assessment!.recorded_at,
                    }
                  : preview.qualification,
              }
            : currentReport,
        ),
      });
    },
  );
  await page.goto("/workspace");
  await expect(
    page.getByRole("heading", { name: "Offene Positionen · 100" }),
  ).toBeVisible();
  await expect(page.getByText(/Positionssignale werden ergänzt/)).toHaveCount(
    0,
  );
  const search = page.getByRole("searchbox");
  await search.fill("WK0099");
  await page.getByRole("button", { name: "Details", exact: true }).click();
  await expect(page.getByText("Noch keine gespeicherte Prüfung")).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Hebeltrader-Basiswertsitzungen" }),
  ).toContainText("2 abgeschlossene Basiswertsitzungen");
  await expect(
    page.getByRole("region", { name: "Hebeltrader-Original-Geldkurs" }),
  ).toContainText("Teilbelege vorhanden; Gesamtqualifikation offen");
  expect(specificRequests).toEqual([
    expect.stringMatching(
      /^GET (?:\/api)?\/api\/v1\/position-monitoring\/trades\/trade-99\/hebeltrader-targets$/,
    ),
  ]);
  const beforePreview = requests.length;
  await page
    .getByRole("button", { name: "Historische Vergleichsbelege ansehen" })
    .click();
  const qualification = page.getByRole("region", {
    name: "Historische Vergleichsqualifikation",
  });
  await expect(
    qualification.getByRole("table", {
      name: "Gespeicherte Basiswert-Tageskurse",
    }),
  ).toBeVisible();
  expect(requests.slice(beforePreview)).toEqual([
    expect.stringMatching(
      /^GET (?:\/api)?\/api\/v1\/position-monitoring\/trades\/trade-99\/hebeltrader-targets\/qualification-preview$/,
    ),
  ]);
  await expect(qualification).toContainText("Basiswertmarken in USD");
  await expect(qualification).toContainText("keine unabhängige Verifikation");
  await expect(qualification).toContainText("kann aus dem Listing stammen");
  const reference = qualification.getByRole("textbox", {
    name: "Konkreter Nachweis für historische Listingzuordnung und gemeinsamen Originalmaßstab",
  });
  const confirm = qualification.getByRole("button", {
    name: "Historische Zuordnung und Originalmaßstab bestätigen und prüfen",
  });
  await reference.fill("   ");
  await expect(confirm).toBeDisabled();
  await reference.fill(concreteReference);
  await expect(confirm).toBeEnabled();
  await page
    .getByRole("button", { name: "Details schließen", exact: true })
    .click();
  await page.getByRole("button", { name: "Details", exact: true }).click();
  await expect(reference).toHaveValue(concreteReference);
  await expect(search).toHaveValue("WK0099");
  expect(assessmentPosts).toBe(0);
  const beforePost = requests.length;
  await confirm.click();
  await expect(
    page.getByRole("region", { name: "Unbestätigter Prüfauftrag" }),
  ).toBeVisible();
  expect(requests.slice(beforePost)).toEqual([
    expect.stringMatching(
      /^POST (?:\/api)?\/api\/v1\/position-monitoring\/trades\/trade-99\/hebeltrader-targets\/assessments$/,
    ),
  ]);
  await expect(confirm).toBeDisabled();
  await page
    .getByRole("button", { name: "Aktualisieren", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Offene Positionen · 100" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Details", exact: true }).click();
  const unresolved = page.getByRole("region", {
    name: "Unbestätigter Prüfauftrag",
  });
  await expect(unresolved).toBeVisible();
  await expect(unresolved).toContainText(concreteReference);
  await expect(search).toHaveValue("WK0099");
  await expect(
    page.getByRole("button", {
      name: "Gespeicherte Belege prüfen",
      exact: true,
    }),
  ).toBeDisabled();
  await expect(qualification).toContainText(
    "Die vorhandene Bestätigung passt zu diesem Stand und wird wiederverwendet.",
  );
  const beforeReceipt = specificRequests.length;
  await page
    .getByRole("button", { name: "Beleg genau dieser Anfrage lesen" })
    .click();
  await expect(
    page.getByText(
      /Der gespeicherte Vorgangsbeleg bestätigt genau diese Anfrage/,
    ),
  ).toBeVisible();
  expect(specificRequests.slice(beforeReceipt)).toEqual([
    expect.stringMatching(
      new RegExp(
        `^GET (?:/api)?/api/v1/position-monitoring/trades/trade-99/hebeltrader-targets/requests/${submitted!.request_id}$`,
      ),
    ),
  ]);
  await page
    .getByText("Gespeicherter Beleg dieser Anfrage", { exact: true })
    .click();
  await expect(
    page.getByText(/Damals enthaltener Prüfstand: exact-request-assessment/),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Hebeltrader-Zielhistorie" }),
  ).toContainText("nicht als laufende Überwachung aktiviert");
  await expect(
    page.getByRole("region", { name: "Hebeltrader-Belegabdeckung" }),
  ).toContainText("Keine Baseline-Regelauswertung");
  expect(assessmentPosts).toBe(1);
  expect(otherWrites()).toBe(0);
  await page
    .getByRole("link", { name: "Kauf-/Verkaufsdaten und Historie öffnen" })
    .click();
  await expect(page).toHaveURL(/trade_id=trade-99#execution-dates$/);
  expect(assessmentPosts).toBe(1);
  expect(otherWrites()).toBe(0);
});
