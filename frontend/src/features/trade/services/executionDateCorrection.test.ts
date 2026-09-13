// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  effectiveExecutions,
  executionDateContext,
  executionDateCorrection,
} from './executionDateCorrection';
import type { TradeTimelineEntryResponse } from '../types/api';

const entry: TradeTimelineEntryResponse = {
  id: 'buy',
  trade_id: 'trade',
  kind: 'EXECUTION',
  execution_side: 'BUY',
  quantity: 3500,
  price_per_unit: '0.5500000000',
  occurred_at: '2026-08-17T08:30:01.123456Z',
  recorded_at: '2026-09-12T17:00:00Z',
  management_event_type: null,
  numeric_value: null,
  text_value: null,
  supersedes_id: null,
};
beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-09-13T08:00:00Z'));
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
});

describe('execution date correction', () => {
  it('uses the stored execution date, never capture date or today', () => {
    expect(executionDateContext(entry).date).toBe('2026-08-17');
    expect(
      executionDateContext({
        ...entry,
        executed_on: '2026-08-18',
        execution_timezone: 'Asia/Tokyo',
      }),
    ).toEqual({ date: '2026-08-18', timezone: 'Asia/Tokyo', hasTime: false });
  });
  it('preserves amount strings and precise fractional seconds when moving a known time', () => {
    const result = executionDateCorrection(entry, '2026-08-16', true);
    expect(result).toEqual({
      side: 'BUY',
      quantity: 3500,
      price_per_unit: '0.5500000000',
      executed_at: '2026-08-16T08:30:01.123456Z',
    });
    expect(entry.recorded_at).toBe('2026-09-12T17:00:00Z');
    expect(executionDateCorrection(entry, '2026-08-17', true)).toHaveProperty(
      'executed_at',
      entry.occurred_at,
    );
  });
  it('retains the original timezone and unknown clock for date-only histories', () => {
    const result = executionDateCorrection(
      { ...entry, executed_on: '2026-08-17', execution_timezone: 'Asia/Tokyo' },
      '2026-08-16',
      false,
    );
    expect(result).toEqual({
      side: 'BUY',
      quantity: 3500,
      price_per_unit: '0.5500000000',
      executed_on: '2026-08-16',
      execution_timezone: 'Asia/Tokyo',
    });
    expect(result).not.toHaveProperty('executed_at');
    expect(result).not.toHaveProperty('recorded_at');
  });
  it('only removes a formerly precise time on an explicit unknown-time choice', () => {
    expect(
      executionDateCorrection({ ...entry, execution_side: 'SELL' }, '2026-08-22', false),
    ).toEqual({
      side: 'SELL',
      quantity: 3500,
      price_per_unit: entry.price_per_unit,
      executed_on: '2026-08-22',
      execution_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    });
  });
  it.each(['', 'wrong', '2026-02-30', '2099-01-01'])('rejects invalid/future date %s', (value) => {
    expect(() => executionDateCorrection(entry, value, false)).toThrow(/gültiges/);
  });
  it('fails closed on missing reference data instead of inventing a timezone or a price', () => {
    expect(() => executionDateContext({ ...entry, executed_on: '2026-08-17' })).toThrow(/Zeitzone/);
    expect(() =>
      executionDateCorrection({ ...entry, price_per_unit: null }, '2026-08-16', false),
    ).toThrow(/unvollständig/);
  });
  it('only offers effective economic executions, not management events or superseded versions', () => {
    const corrected = { ...entry, id: 'new', supersedes_id: 'buy' };
    const again = { ...entry, id: 'newest', supersedes_id: 'new' };
    const management = { ...entry, id: 'note', kind: 'MANAGEMENT_EVENT' as const };
    expect(effectiveExecutions([entry, corrected, management, again])).toEqual([again]);
  });
});

it('preserves local time across DST changes and rejects ambiguous or skipped target times', () => {
  vi.stubEnv('TZ', 'Europe/Berlin');
  const summer = { ...entry, occurred_at: '2025-07-12T00:30:01.123456Z' };
  expect(executionDateContext(summer).timezone).toBe('Europe/Berlin');
  expect(executionDateCorrection(summer, '2025-01-12', true)).toHaveProperty(
    'executed_at',
    '2025-01-12T01:30:01.123456Z',
  );
  expect(() => executionDateCorrection(summer, '2025-03-30', true)).toThrow(/Zeitumstellung/);
  expect(() => executionDateCorrection(summer, '2025-10-26', true)).toThrow(/Zeitumstellung/);
});
