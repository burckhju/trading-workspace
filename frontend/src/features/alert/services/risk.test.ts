import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { riskApi } from './risk';
afterEach(() => vi.unstubAllGlobals());
const parameters = {
  hysteresis_fraction: '.005',
  confirmation_sessions: 2,
  volatility_high: '.4',
  volatility_reset: '.35',
  maximum_age_days: 4,
};
const configuration = {
  revision: 7,
  enabled: false,
  policy_version: 'POSITION_RISK_V1',
  parameters,
};
beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ trade_id: 'trade', configuration, metrics: { status: 'AVAILABLE' } }),
          { status: 200 },
        ),
      ),
  );
});
it('sends an object once, exact revision and explicit confirmation to the configuration endpoint', async () => {
  await riskApi.configure('trade', { configuration }, parameters, true);
  const args = vi.mocked(fetch).mock.calls[0];
  expect(args[0]).toContain('/trades/trade/risk/configuration');
  expect(args[1]?.method).toBe('PUT');
  expect(JSON.parse(typeof args[1]?.body === 'string' ? args[1].body : 'null')).toEqual({
    parameters,
    enabled: true,
    expected_revision: 7,
    confirmation: 'CONFIRM_POSITION_RISK_CONFIGURATION',
  });
});
it('preview also sends a JSON object without activating or persisting', async () => {
  await riskApi.preview('trade', parameters);
  const args = vi.mocked(fetch).mock.calls[0];
  expect(args[0]).toContain('/risk/preview');
  expect(JSON.parse(typeof args[1]?.body === 'string' ? args[1].body : 'null')).toEqual({
    parameters,
  });
});
it('rejects a response for a different trade and malformed responses', async () => {
  await expect(riskApi.read('another-trade')).rejects.toThrow('fremde');
  vi.mocked(fetch).mockResolvedValueOnce(new Response('[]', { status: 200 }));
  await expect(riskApi.read('trade')).rejects.toThrow('Unvollständige');
});
it('uses GET for reads and an explicit POST only for evaluation', async () => {
  await riskApi.read('trade');
  expect(vi.mocked(fetch).mock.calls[0][1]?.method).toBe('GET');
  vi.mocked(fetch).mockResolvedValueOnce(new Response('[]', { status: 200 }));
  await riskApi.history('trade');
  expect(vi.mocked(fetch).mock.calls[1][0]).toContain('/risk/history');
  vi.mocked(fetch).mockResolvedValueOnce(new Response('{}', { status: 200 }));
  await riskApi.evaluate('trade');
  expect(vi.mocked(fetch).mock.calls[2][1]?.method).toBe('POST');
});
