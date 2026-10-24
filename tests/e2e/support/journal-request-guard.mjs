const ORIGIN = "http://localhost:8080";

// APIRequestContext does not share BrowserContext routes. Pin it independently
// and disable redirects so a local response cannot forward a test write outside.
export function localLearningRequest(request) {
  function validate(url) {
    const target = new URL(url);
    if (
      target.origin !== ORIGIN ||
      target.username ||
      target.password ||
      target.hash ||
      !target.pathname.startsWith("/api/api/v1/")
    )
      throw new Error(
        "Learning qualification API request escaped its local API boundary",
      );
  }
  return {
    get(url, options = {}) {
      validate(url);
      return request.get(url, { ...options, maxRedirects: 0 });
    },
    post(url, options = {}) {
      validate(url);
      return request.post(url, { ...options, maxRedirects: 0 });
    },
  };
}
