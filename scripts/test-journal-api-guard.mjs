import assert from "node:assert/strict";
import test from "node:test";
import { localLearningRequest } from "../tests/e2e/support/journal-request-guard.mjs";

test("both local API methods preserve payloads and force zero redirects", async () => {
  const calls = [];
  const client = localLearningRequest({
    get: (...args) => calls.push(["GET", ...args]),
    post: (...args) => calls.push(["POST", ...args]),
  });
  const url =
    "http://localhost:8080/api/api/v1/learning/trades/example/journal";
  await client.get(url, { maxRedirects: 20 });
  await client.post(url, { data: { confirmed: true }, maxRedirects: 5 });
  assert.deepEqual(calls, [
    ["GET", url, { maxRedirects: 0 }],
    ["POST", url, { data: { confirmed: true }, maxRedirects: 0 }],
  ]);
});

for (const url of [
  "https://provider.example/api/api/v1/trades",
  "http://127.0.0.1:8080/api/api/v1/trades",
  "http://localhost:38080/api/api/v1/trades",
  "http://localhost:8080/api/api/v1/../../outside",
  "http://localhost:8080/health",
  "http://user:secret@localhost:8080/api/api/v1/trades",
  "http://localhost:8080/api/api/v1/trades#fragment",
  "//provider.example/api/api/v1/trades",
]) {
  test(`refuse API target before transport: ${url}`, () => {
    let calls = 0;
    const client = localLearningRequest({
      get: () => calls++,
      post: () => calls++,
    });
    assert.throws(() => client.get(url));
    assert.throws(() => client.post(url));
    assert.equal(calls, 0);
  });
}
