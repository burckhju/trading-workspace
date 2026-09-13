// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { executionTime } from './capture';

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-09-13T12:00:00Z'));
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
});

describe('new capture local execution times', () => {
  it.each([
    ['Europe/Berlin', '2025-10-26', '02:00'],
    ['Europe/Berlin', '2025-10-26', '02:30'],
    ['Europe/Berlin', '2025-10-26', '02:59'],
    ['America/New_York', '2025-11-02', '01:30'],
    ['Australia/Lord_Howe', '2025-04-06', '01:45'],
  ])(
    'rejects a repeated clock time instead of choosing an offset: %s %s %s',
    (zone, date, time) => {
      vi.stubEnv('TZ', zone);
      expect(() => executionTime(date, time)).toThrow(/Zeitumstellung.*nicht eindeutig/);
    },
  );

  it.each([
    ['Europe/Berlin', '2025-10-26', '01:59', '2025-10-25T23:59:00.000Z'],
    ['Europe/Berlin', '2025-10-26', '03:00', '2025-10-26T02:00:00.000Z'],
    ['America/New_York', '2025-11-02', '00:59', '2025-11-02T04:59:00.000Z'],
    ['America/New_York', '2025-11-02', '02:00', '2025-11-02T07:00:00.000Z'],
    ['Australia/Lord_Howe', '2025-04-06', '01:29', '2025-04-05T14:29:00.000Z'],
    ['Australia/Lord_Howe', '2025-04-06', '02:00', '2025-04-05T15:30:00.000Z'],
    ['UTC', '2025-10-26', '02:30', '2025-10-26T02:30:00.000Z'],
    ['Asia/Kolkata', '2025-10-26', '02:30', '2025-10-25T21:00:00.000Z'],
  ])(
    'preserves unique local times, including on transition days: %s %s %s',
    (zone, date, time, at) => {
      vi.stubEnv('TZ', zone);
      expect(executionTime(date, time)).toEqual({ executed_at: at });
    },
  );

  it.each([
    ['Europe/Berlin', '2025-03-30', '02:30'],
    ['America/New_York', '2025-03-09', '02:30'],
    ['Australia/Lord_Howe', '2025-10-05', '02:15'],
  ])('still rejects skipped local times: %s %s %s', (zone, date, time) => {
    vi.stubEnv('TZ', zone);
    expect(() => executionTime(date, time)).toThrow(/nicht gültig/);
  });

  it.each([
    ['Europe/Berlin', '2025-10-26'],
    ['America/New_York', '2025-11-02'],
    ['Australia/Lord_Howe', '2025-04-06'],
  ])('retains explicitly date-only capture without guessing an instant: %s %s', (zone, date) => {
    vi.stubEnv('TZ', zone);
    expect(executionTime(date)).toEqual({ executed_on: date, execution_timezone: zone });
  });

  it('still rejects a future precise execution on the current calendar day', () => {
    vi.stubEnv('TZ', 'Europe/Berlin');
    expect(() => executionTime('2026-09-13', '14:01')).toThrow(/Zukunft/);
    expect(executionTime('2026-09-13', '14:00')).toEqual({
      executed_at: '2026-09-13T12:00:00.000Z',
    });
  });
});
