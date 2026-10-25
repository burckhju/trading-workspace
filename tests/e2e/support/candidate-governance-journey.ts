import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import {
  expect,
  type APIRequestContext,
  type BrowserContext,
  type Page,
  type TestInfo,
} from "@playwright/test";
import { localGovernanceRequest } from "./candidate-governance-request-guard.mjs";

const origin = "http://localhost:8080";
const apiPrefix = "/api/api/v1";
type Method = "POST" | "PUT" | "PATCH";
type DatabaseState = {
  fingerprint: string;
  tables: Record<string, { count: number; hash: string }>;
  [key: string]: unknown;
};
type Observed = {
  transport: "browser" | "setup-api";
  phase: string;
  method: string;
  path: string;
  payload?: unknown;
  status?: number;
  body?: unknown;
};

// This helper forwards real local HTTP responses. It provides no mocked business
// data. APIRequestContext and the browser have independent origin/redirect guards.
export async function prepareGovernanceJourney(
  context: BrowserContext,
  rawRequest: APIRequestContext,
  testInfo: TestInfo,
) {
  const root = resolve(process.cwd(), "..");
  const python = process.env.CANDIDATE_GOVERNANCE_E2E_PYTHON!;
  const runId = process.env.CANDIDATE_GOVERNANCE_E2E_RUN_ID!;
  expect(process.env.CI).toBe("true");
  expect(process.env.GITHUB_ACTIONS).toBe("true");
  expect(process.env.CANDIDATE_GOVERNANCE_E2E_WRITES_ALLOWED).toBe("1");
  expect(runId).toMatch(/^[0-9a-f-]{36}$/);
  const pythonJson = (file: string, args: string[] = []) =>
    JSON.parse(
      execFileSync(python, [resolve(root, file), ...args], {
        cwd: root,
        env: { ...process.env, PYTHONPATH: `${root}/backend:${root}` },
        encoding: "utf8",
      }),
    );
  const databaseState = (): DatabaseState =>
    pythonJson("tests/e2e/support/candidate_governance_database_guard.py");
  const record = async (name: string, body: unknown) => {
    await testInfo.attach(name, {
      body: JSON.stringify(body, null, 2),
      contentType: "application/json",
    });
  };
  await record("B-CG-001-initial-target", databaseState());

  let phase = "S0-setup";
  let readWindow = false;
  let armed: { method: Method; path: string; requests: number } | null = null;
  const reads = new Set<string>();
  const documents = new Set<string>(["/candidates"]);
  const observed: Observed[] = [];
  const failures: string[] = [];
  const pending = new Set<Promise<void>>();
  // The production build needs no socket. Do not let an unreviewed WebSocket
  // bypass the HTTP origin/command guard; interception never connects upstream.
  await context.routeWebSocket("**/*", async (socket) => {
    failures.push(`Unexpected browser WebSocket: ${socket.url()}`);
    await socket.close({
      code: 1008,
      reason: "No WebSockets in this qualification",
    });
  });
  context.on("page", (page) =>
    page.on("pageerror", (error) => failures.push(error.message)),
  );
  for (const page of context.pages())
    page.on("pageerror", (error) => failures.push(error.message));
  const allowRead = (path: string) => reads.add(apiPrefix + path);
  const allowLesson = (
    lessonId: string,
    versionIds: string[],
    evidenceId: string,
  ) => {
    documents.add(`/lessons/${lessonId}`);
    allowRead(`/learning/lessons/${lessonId}`);
    allowRead(`/learning/lessons/${lessonId}/review-context`);
    allowRead("/learning/learning-evidence");
    allowRead(`/learning/learning-evidence/${evidenceId}`);
    allowRead(`/learning/learning-evidence/${evidenceId}/currentness`);
    for (const id of versionIds)
      allowRead(`/model-governance/lesson-versions/${id}/hypotheses`);
  };
  const allowModel = (modelId: string) => {
    allowRead("/model-governance/models");
    allowRead(`/model-governance/models/${modelId}/versions`);
    allowRead(`/model-governance/models/${modelId}/runtime-activation`);
  };
  const allowCandidate = (id: string) => {
    allowRead("/candidates");
    allowRead(`/candidates/${id}/evaluations`);
    allowRead(`/candidates/${id}/live-workflow`);
  };
  const remember = (path: string, body: { id?: string }) => {
    if (!body?.id) return;
    if (/\/model-governance\/lesson-versions\/[^/]+\/hypotheses$/.test(path))
      allowRead(`/model-governance/hypotheses/${body.id}/proposals`);
    if (path === apiPrefix + "/model-governance/proposals") {
      allowRead(`/model-governance/proposals/${body.id}/validations`);
      allowRead(`/model-governance/proposals/${body.id}/approval`);
    }
  };
  await context.route("**/*", async (route) => {
    const operation = (async () => {
      const request = route.request();
      const target = new URL(request.url());
      const method = request.method();
      if (
        target.origin !== origin ||
        target.username ||
        target.password ||
        target.hash ||
        request.redirectedFrom()
      ) {
        failures.push(
          `Refused browser origin or redirect: ${method} ${request.url()}`,
        );
        await route.abort();
        return;
      }
      const isApi = target.pathname.startsWith(apiPrefix + "/");
      if (!isApi) {
        if (
          method !== "GET" ||
          !(
            documents.has(target.pathname) ||
            target.pathname.startsWith("/assets/") ||
            ["/favicon.ico", "/vite.svg"].includes(target.pathname)
          )
        ) {
          failures.push(
            `Unexpected browser resource: ${method} ${target.pathname}`,
          );
          await route.abort();
          return;
        }
      } else if (method === "GET") {
        if (!reads.has(target.pathname)) {
          failures.push(`Unreviewed browser read: ${target.pathname}`);
          await route.abort();
          return;
        }
      } else if (
        readWindow ||
        !armed ||
        armed.method !== method ||
        armed.path !== target.pathname ||
        armed.requests !== 0
      ) {
        failures.push(
          `Unplanned or duplicate browser command: ${method} ${target.pathname}`,
        );
        await route.abort();
        return;
      } else {
        armed.requests += 1;
      }
      const entry: Observed = {
        transport: "browser",
        phase,
        method,
        path: target.pathname + target.search,
        ...(request.postData() ? { payload: request.postDataJSON() } : {}),
      };
      if (isApi) observed.push(entry);
      // maxRedirects=0 also prevents a same-origin response escaping the route
      // guard through a browser redirect. The native response body is unchanged.
      const response = await route.fetch({ maxRedirects: 0, maxRetries: 0 });
      entry.status = response.status();
      if (response.status() >= 300 && response.status() < 400) {
        failures.push(
          `Refused native redirect: ${target.pathname} ${response.status()}`,
        );
        await route.abort();
        return;
      }
      if (isApi) {
        entry.body = await response.json();
        if (method === "GET" && response.status() !== 200)
          failures.push(
            `Failed browser read: ${target.pathname} ${response.status()}`,
          );
        if (response.ok() && method !== "GET")
          remember(target.pathname, entry.body as { id?: string });
      }
      await route.fulfill({ response });
    })();
    pending.add(operation);
    try {
      await operation;
    } catch (error) {
      failures.push(String(error));
      await route.abort().catch(() => undefined);
    } finally {
      pending.delete(operation);
    }
  });
  const settle = async () => {
    while (pending.size) await Promise.all([...pending]);
    expect(failures).toEqual([]);
  };
  const request = localGovernanceRequest(rawRequest);
  const getJson = async (path: string) => {
    if (phase !== "S0-setup")
      expect(reads.has(apiPrefix + path), `Unreviewed API read: ${path}`).toBe(
        true,
      );
    const response = await request.get(origin + apiPrefix + path);
    expect(response.status(), await response.text()).toBe(200);
    const body = await response.json();
    observed.push({
      transport: "setup-api",
      phase,
      method: "GET",
      path,
      status: 200,
      body,
    });
    return body;
  };
  const command = async (
    path: string,
    data?: object,
    method: Method = "POST",
    headers?: Record<string, string>,
  ) => {
    expect(phase).toBe("S0-setup");
    expect(readWindow).toBe(false);
    const execute =
      method === "POST"
        ? request.post
        : method === "PUT"
          ? request.put
          : request.patch;
    const response = await execute(origin + apiPrefix + path, {
      data,
      headers,
    });
    const body = await response.json();
    observed.push({
      transport: "setup-api",
      phase,
      method,
      path,
      payload: data,
      status: response.status(),
      body,
    });
    expect(response.ok(), JSON.stringify(body)).toBe(true);
    return body;
  };
  return {
    runId,
    record,
    databaseState,
    getJson,
    command,
    allowRead,
    allowLesson,
    allowModel,
    allowCandidate,
    setPhase(value: string) {
      phase = value;
    },
    async seedPrices(
      mode: "learning" | "analyses" | "warning",
      ...ids: string[]
    ) {
      expect(phase).toBe("S0-setup");
      const seeded = pythonJson(
        "tests/e2e/support/seed_candidate_governance_prices.py",
        [mode, ...ids],
      );
      await record(`S0-synthetic-${mode}-prices`, seeded);
      return seeded;
    },
    settle,
    async uiCommand(
      page: Page,
      label: string,
      path: string,
      action: () => Promise<unknown>,
      expectedStatus = 200,
    ) {
      expect(readWindow).toBe(false);
      expect(armed).toBeNull();
      await settle();
      phase = label;
      const before = databaseState();
      const current = {
        method: "POST" as const,
        path: apiPrefix + path,
        requests: 0,
      };
      armed = current;
      try {
        const [response] = await Promise.all([
          page.waitForResponse(
            (value) =>
              value.url() === origin + apiPrefix + path &&
              value.request().method() === "POST",
          ),
          action(),
        ]);
        expect(await response.finished()).toBeNull();
        expect(response.status(), await response.text()).toBe(expectedStatus);
        const body = await response.json();
        const payload = response.request().postData()
          ? response.request().postDataJSON()
          : null;
        await settle();
        expect(current.requests).toBe(1);
        const after = databaseState();
        if (expectedStatus >= 400)
          expect(after.fingerprint).toBe(before.fingerprint);
        await record(label, {
          before,
          payload,
          body,
          after,
          browserCommands: current.requests,
        });
        return { body, payload, before, after };
      } finally {
        armed = null;
      }
    },
    async readWindow<T>(label: string, read: () => Promise<T>) {
      await settle();
      expect(armed).toBeNull();
      const before = databaseState();
      const index = observed.length;
      phase = label;
      readWindow = true;
      try {
        const result = await read();
        await settle();
        const requests = observed.slice(index);
        expect(requests.length).toBeGreaterThan(0);
        expect(requests.every((entry) => entry.method === "GET")).toBe(true);
        const after = databaseState();
        expect(after.fingerprint).toBe(before.fingerprint);
        await record(label, { before, result, requests, after });
        return result;
      } finally {
        readWindow = false;
      }
    },
    async finish() {
      try {
        await settle();
      } finally {
        await record("B-CG-001-all-observed-requests", {
          requests: observed,
          failures,
        });
      }
      expect(failures).toEqual([]);
    },
  };
}
