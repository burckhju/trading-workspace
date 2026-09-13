import { afterEach, describe, expect, it, vi } from 'vitest';

import { captureRequest, executionTime, finishCapture, localToday } from './capture';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('execution dates and retry identity', () => {
  it('preserves calendar dates without inventing a clock time', () => {
    expect(localToday(new Date(2026, 7, 17, 23, 55))).toBe('2026-08-17');
    expect(executionTime('2026-08-17')).toEqual({
      executed_on: '2026-08-17',
      execution_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    });
    expect(executionTime('2026-08-17', '10:30')).toEqual({
      executed_at: new Date('2026-08-17T10:30').toISOString(),
    });
    expect(() => executionTime('2099-01-01')).toThrow();
    expect(() => executionTime('')).toThrow();
    expect(() => executionTime('2026-08-17', '99:30')).toThrow();
  });
  it('reuses an unchanged request but not a deliberately new purchase', () => {
    const scope = 'test:retry';
    const payload = { quantity: 10, price_per_unit: '0.55', executed_on: '2026-08-17' };
    const key = captureRequest(scope, payload);
    expect(captureRequest(scope, { ...payload })).toBe(key);
    expect(captureRequest(scope, { ...payload, quantity: 11 })).not.toBe(key);
    finishCapture(scope);
    expect(captureRequest(scope, payload)).not.toBe(key);
    finishCapture(scope);
  });
  it('keeps retry identity even when browser storage is unavailable', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('denied');
    });
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('denied');
    });
    const key = captureRequest('test:storage', { quantity: 1 });
    expect(captureRequest('test:storage', { quantity: 1 })).toBe(key);
    finishCapture('test:storage');
    expect(captureRequest('test:storage', { quantity: 1 })).not.toBe(key);
    finishCapture('test:storage');
  });
  it('does not trust corrupt browser storage', () => {
    sessionStorage.setItem('trade-capture:test:corrupt', '{');
    expect(captureRequest('test:corrupt', {})).toMatch(/^[a-f0-9-]{36}$/);
    finishCapture('test:corrupt');
  });
});
