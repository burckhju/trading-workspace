# S6-13e Implementation Report – E2E Proxy Path Alignment

## Scope

S6-13e corrects the FT-007 Playwright route contract after request diagnostics proved the browser-facing reverse-proxy path.

## Finding

The current deployment contract intentionally composes two API path layers:

- `VITE_API_BASE_URL=http://localhost:8080/api` identifies the Nginx gateway prefix.
- Feature clients append the FastAPI resource prefix `/api/v1/...`.
- Nginx `location /api/` with `proxy_pass http://backend:8000/;` strips the gateway `/api/` prefix before forwarding.
- Therefore the browser-visible FT-007 URL is `/api/api/v1/trade-plans/...`, while FastAPI receives `/api/v1/trade-plans/...`.

Changing the production client or environment normalization would alter an existing cross-feature proxy contract and was therefore rejected in this unit.

## Changes

- FT-007 E2E route matchers now target the measured external path `/api/api/v1/trade-plans...`.
- The direct amendment request in the E2E scenario uses the same external proxy path.
- Backend, frontend production client, domain and API code are unchanged.

## Expected gate

Run:

```bash
./scripts/run-e2e.sh
```

Expected result: all 8 Playwright E2E tests pass.
