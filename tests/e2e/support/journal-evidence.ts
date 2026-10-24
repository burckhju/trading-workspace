import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { expect, type Page, type TestInfo } from "@playwright/test";

export async function prepareLearningQualification(
  page: Page,
  baseURL: string | undefined,
  testInfo: TestInfo,
) {
  expect(baseURL).toBe("http://localhost:8080");
  const root = resolve(process.cwd(), "..");
  const databaseState = () =>
    JSON.parse(
      execFileSync(
        process.env.JOURNAL_E2E_PYTHON ?? "python",
        [resolve(root, "tests/e2e/support/journal_database_guard.py")],
        {
          cwd: root,
          env: { ...process.env, PYTHONPATH: `${root}/backend:${root}` },
          encoding: "utf8",
        },
      ),
    );
  // The independent host connection verifies marker, DB/user/port, migration,
  // workspace and PostgreSQL before the first owner API mutation in either case.
  const initial = databaseState();
  await testInfo.attach("verified-initial-database", {
    body: JSON.stringify(initial, null, 2),
    contentType: "application/json",
  });
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await page.context().route("**/*", (route) => {
    if (new URL(route.request().url()).origin === baseURL)
      return route.continue();
    failures.push(`Blocked external browser request: ${route.request().url()}`);
    return route.abort();
  });
  return {
    assertNoUnexpectedRequests: () => expect(failures).toEqual([]),
    async readWindow<T>(name: string, read: () => Promise<T>) {
      const before = databaseState();
      const result = await read();
      const after = databaseState();
      expect(after.fingerprint).toBe(before.fingerprint);
      await testInfo.attach(name, {
        body: JSON.stringify({ before, result, after }, null, 2),
        contentType: "application/json",
      });
      return result;
    },
  };
}
