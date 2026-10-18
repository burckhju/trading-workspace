import { afterEach, expect, it, vi } from 'vitest';
import type { IvModelForm } from '../types/iv';
import { ivApi } from './iv';

afterEach(() => vi.unstubAllGlobals());

it('sends percentages/pp without mixing them and chooses exactly one IV origin', async () => {
  const fetch = vi
    .fn<typeof globalThis.fetch>()
    .mockResolvedValue(new Response('{}', { status: 200 }));
  vi.stubGlobal('fetch', fetch);
  const form = {
    scope: 'EUROPEAN',
    direction: 'CALL',
    currency: 'USD',
    mode: 'iv',
    spot: '100',
    strike: '100',
    ratio: '.1',
    remaining_days: '30',
    iv_percent: '35',
    calibration_price: '1',
    rate_percent: '2',
    dividend_yield_percent: '0',
    quantity: '500',
    underlying_change_percent: '-10',
    iv_change_pp: '-5',
    elapsed_days: '7',
  } as IvModelForm;
  await ivApi.preview(form);
  const raw = fetch.mock.calls[0][1]?.body;
  if (typeof raw !== 'string') throw new Error('Expected JSON request body');
  const body = JSON.parse(raw) as Record<string, unknown>;
  expect(body.iv_percent).toBe('35');
  expect(body.calibration_price).toBeNull();
  expect(body.scenario).toEqual({
    quantity: '500',
    underlying_change_percent: '-10',
    iv_change_pp: '-5',
    elapsed_days: '7',
  });
  expect(body.underlying_currency).toBe('USD');
  expect(body.basis).toBe('HYPOTHETICAL_ASSUMPTIONS');
  fetch.mockResolvedValue(new Response('{}', { status: 200 }));
  await ivApi.preview({ ...form, mode: 'price' });
  const priceRaw = fetch.mock.calls[1][1]?.body;
  if (typeof priceRaw !== 'string') throw new Error('Expected JSON request body');
  const priceBody = JSON.parse(priceRaw) as Record<string, unknown>;
  expect(priceBody.iv_percent).toBeNull();
  expect(priceBody.calibration_price).toBe('1');
});
