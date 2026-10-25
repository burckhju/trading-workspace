import assert from "node:assert/strict";
import test from "node:test";
import { localGovernanceRequest } from "../tests/e2e/support/candidate-governance-request-guard.mjs";

const METHODS = ["get", "post", "put", "patch"];

for (const method of METHODS) {
  test(`${method} preserves payload and forces no redirect or transport retry`, async () => {
    const calls = [];
    const client = localGovernanceRequest({
      [method]: (...args) => {
        calls.push(args);
        return "actual response";
      },
    });
    const url =
      "http://localhost:8080/api/api/v1/model-governance/proposals?limit=20";
    const options = {
      data: { confirmed: true },
      headers: { "X-Actor-ID": "synthetic" },
      maxRedirects: 20,
      maxRetries: 5,
    };
    assert.equal(await client[method](url, options), "actual response");
    assert.deepEqual(calls, [
      [url, { ...options, maxRedirects: 0, maxRetries: 0 }],
    ]);
    assert.equal(options.maxRedirects, 20);
    assert.equal(options.maxRetries, 5);
  });
}

test("only the four named owner API methods are exposed", () => {
  assert.deepEqual(Object.keys(localGovernanceRequest({})), METHODS);
});

for (const url of [
  "https://provider.example/api/api/v1/models",
  "http://127.0.0.1:8080/api/api/v1/models",
  "http://localhost:38080/api/api/v1/models",
  "http://localhost:8080/api/api/v1/../../outside",
  "http://localhost:8080/api/api/v1/models/../proposals",
  "http://localhost:8080/api/api/v1/%2e%2e/outside",
  "http://localhost:8080/api/api/v1/models%2foutside",
  "http://localhost:8080/api/api/v1/%252e%252e%252foutside",
  "http://localhost:8080/api/api/v1/\\outside",
  "http://localhost:8080/api/api/v1/models%5coutside",
  "http://localhost:8080/health",
  "http://localhost:8080/api/api/v10/models",
  "http://user:secret@localhost:8080/api/api/v1/models",
  "http://localhost:8080/api/api/v1/models#fragment",
  "http://localhost:8080/api/api/v1/models#",
  "//provider.example/api/api/v1/models",
]) {
  test(`refuse every method before transport: ${url}`, () => {
    let calls = 0;
    const client = localGovernanceRequest(
      Object.fromEntries(METHODS.map((method) => [method, () => calls++])),
    );
    for (const method of METHODS) assert.throws(() => client[method](url));
    assert.equal(calls, 0);
  });
}
