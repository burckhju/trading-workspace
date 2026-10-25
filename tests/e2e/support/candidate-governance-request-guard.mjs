const ORIGIN = "http://localhost:8080";

// APIRequestContext has no BrowserContext routes. Validate before transport and
// never follow a redirect or repeat a command with an uncertain outcome.
export function localGovernanceRequest(request) {
  const send = (method, url, options = {}) => {
    const target = new URL(url);
    if (
      target.origin !== ORIGIN ||
      target.username ||
      target.password ||
      url.includes("#") ||
      target.href !== url ||
      !target.pathname.startsWith("/api/api/v1/") ||
      /[%\\]/.test(target.pathname)
    )
      throw new Error(
        "Governance qualification API request escaped its canonical local API boundary",
      );
    return request[method](url, {
      ...options,
      maxRedirects: 0,
      maxRetries: 0,
    });
  };
  return Object.fromEntries(
    ["get", "post", "put", "patch"].map((method) => [
      method,
      (url, options) => send(method, url, options),
    ]),
  );
}
