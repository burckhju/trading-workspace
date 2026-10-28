// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { TradeTimelineEntryResponse } from '../types/api';
import {
  executionAmountChanges,
  executionAmountCorrection,
  executionPrice,
  executionQuantity,
} from './executionAmountCorrection';

const entry: TradeTimelineEntryResponse = {
  id: 'buy',
  trade_id: 'trade',
  kind: 'EXECUTION',
  execution_side: 'BUY',
  quantity: 10,
  price_per_unit: '0.5500000000',
  occurred_at: '2026-08-17T08:30:01.123456789+02:00',
  recorded_at: '2026-09-12T17:00:00Z',
  management_event_type: null,
  numeric_value: null,
  text_value: null,
  supersedes_id: null,
};

beforeEach(() => {
  vi.stubEnv('TZ', 'UTC');
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-09-13T08:00:00Z'));
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
});

describe('execution quantity input', () => {
  it('accepts positive whole quantities through the persisted integer boundary', () => {
    expect(executionQuantity('1')).toBe(1);
    expect(executionQuantity(' 00012 ')).toBe(12);
    expect(executionQuantity('2147483647')).toBe(2147483647);
  });

  it.each(['', ' ', '1.5', '1,5', '10.0', '10shares', '1e3', '+2', '-1', '1 000', '1_000'])(
    'rejects incomplete, fractional, grouped or partially numeric quantity %j',
    (value) => {
      expect(() => executionQuantity(value)).toThrow(/positive ganze Menge/);
    },
  );

  it.each(['0', '0000'])('rejects %s rather than treating it as cancellation', (value) => {
    expect(() => executionQuantity(value)).toThrow(/größer als 0.*storniert/);
  });

  it.each(['2147483648', '999999999999999999999999999999999999999'])(
    'rejects overflow %s',
    (value) => {
      expect(() => executionQuantity(value)).toThrow(/2147483647/);
    },
  );
});

describe('execution price input', () => {
  it.each([
    ['2,50000000000', '2.5'],
    ['000000000000000000000002.50', '2.5'],
    [' 99999999999999,9999999999 ', '99999999999999.9999999999'],
    ['0.00000000010000', '0.0000000001'],
    ['10.000000000000000000', '10'],
  ])('normalizes %s by string operations to %s without losing value', (value, expected) => {
    expect(executionPrice(value, entry.price_per_unit!)).toBe(expected);
  });

  it.each([
    '',
    '.',
    ',',
    '1.',
    '1,',
    '.5',
    ',5',
    '1,234.56',
    '1.234,56',
    '1.000.000',
    '1,000,000',
    '1 000',
    "1'000",
    '2e1',
    '-0.5',
    '+0.5',
    'NaN',
    'Infinity',
    '3eur',
  ])('rejects malformed, incomplete or grouped new price %j', (value) => {
    expect(() => executionPrice(value, entry.price_per_unit!)).toThrow(/vollständigen Preis/);
  });

  it.each(['0', '000.000', '0,0000000000'])('rejects zero %s', (value) => {
    expect(() => executionPrice(value, entry.price_per_unit!)).toThrow(/größer als 0/);
  });

  it.each(['100000000000000', '99999999999999.99999999999', '0.00000000001', '2.50000000001'])(
    'rejects %s when lossless Numeric(24,10) persistence is impossible',
    (value) => {
      expect(() => executionPrice(value, entry.price_per_unit!)).toThrow(
        /14 Vorkomma- und 10 Nachkommastellen.*nicht gerundet/,
      );
    },
  );

  it.each(['0,55', '0.5500000000', '000.550000000000000000', ' 0.55 '])(
    'keeps the entire stored string for equivalent input %s',
    (value) => {
      expect(executionPrice(value, entry.price_per_unit!)).toBe('0.5500000000');
      expect(executionAmountChanges(entry, '00010', value)).toEqual({
        quantity: false,
        price: false,
      });
    },
  );

  it('preserves long existing price strings without claiming they are valid new database values', () => {
    const original = '12345678901234567890.12345678901234567890';
    expect(executionPrice(original, original)).toBe(original);
    expect(executionPrice('00012345678901234567890,1234567890123456789000', original)).toBe(
      original,
    );
    expect(() => executionPrice(original, '0.55')).toThrow(/14 Vorkomma- und 10 Nachkommastellen/);
    expect(() => executionPrice('12345678901234567890.12345678901234567891', original)).toThrow(
      /14 Vorkomma- und 10 Nachkommastellen/,
    );
  });

  it('compares tiny stored Decimal exponent strings exactly without accepting new exponent inputs', () => {
    expect(executionPrice('1E-10', '1E-10')).toBe('1E-10');
    expect(executionPrice('0,000000000100', '1E-10')).toBe('1E-10');
    expect(executionPrice('0.0000000002', '1E-10')).toBe('0.0000000002');
    expect(() => executionPrice('2E-10', '1E-10')).toThrow(
      /ohne Tausendertrennzeichen oder Exponent/,
    );
    expect(executionPrice('1000', '1E+3')).toBe('1E+3');
  });
});

describe('amount correction payload and dirty detection', () => {
  it('detects quantity-only and price-only edits, and protects invalid input', () => {
    expect(executionAmountChanges(entry, '12', '0,55')).toEqual({ quantity: true, price: false });
    expect(executionAmountChanges(entry, '10', '2,5')).toEqual({ quantity: false, price: true });
    expect(executionAmountChanges(entry, '10.5', '0.55')).toEqual({ quantity: true, price: false });
    expect(executionAmountChanges(entry, '10', '1,')).toEqual({ quantity: false, price: true });
    expect(executionAmountChanges({ ...entry, price_per_unit: null }, '10', '')).toEqual({
      quantity: false,
      price: true,
    });
  });

  it.each(['BUY', 'SELL'] as const)(
    'preserves the exact timestamp and original full price on a %s quantity correction',
    (side) => {
      const source = { ...entry, execution_side: side };
      const result = executionAmountCorrection(source, '2026-08-17', true, '12', '0,55');
      expect(result).toEqual({
        side,
        quantity: 12,
        price_per_unit: '0.5500000000',
        executed_at: '2026-08-17T08:30:01.123456789+02:00',
      });
      expect(result).not.toHaveProperty('request_id');
      expect(result).not.toHaveProperty('expected_version');
      expect(result).not.toHaveProperty('recorded_at');
      expect(source).toEqual({ ...entry, execution_side: side });
    },
  );

  it('sends a normalized changed price without changing quantity or time', () => {
    expect(executionAmountCorrection(entry, '2026-08-17', true, '10', '2,50')).toEqual({
      side: 'BUY',
      quantity: 10,
      price_per_unit: '2.5',
      executed_at: entry.occurred_at,
    });
  });

  it('preserves calendar precision and the original timezone for amount-only changes', () => {
    const dateOnly = { ...entry, executed_on: '2026-08-17', execution_timezone: 'Asia/Tokyo' };
    expect(executionAmountCorrection(dateOnly, '2026-08-17', false, '12', '2,5')).toEqual({
      side: 'BUY',
      quantity: 12,
      price_per_unit: '2.5',
      executed_on: '2026-08-17',
      execution_timezone: 'Asia/Tokyo',
    });
  });

  it('reuses explicit date and time-precision choices without rounding legacy price transport', () => {
    const source = { ...entry, price_per_unit: '0.12345678901234567890' };
    expect(
      executionAmountCorrection(source, '2026-08-16', false, '10', source.price_per_unit),
    ).toEqual({
      side: 'BUY',
      quantity: 10,
      price_per_unit: source.price_per_unit,
      executed_on: '2026-08-16',
      execution_timezone: 'UTC',
    });
  });

  it('continues to reject invalid dates and missing facts', () => {
    expect(() => executionAmountCorrection(entry, '2026-02-30', true, '12', '2.5')).toThrow(
      /gültiges/,
    );
    expect(() => executionAmountCorrection(entry, '2099-01-01', true, '12', '2.5')).toThrow(
      /gültiges/,
    );
    expect(() =>
      executionAmountCorrection(
        { ...entry, price_per_unit: null },
        '2026-08-17',
        true,
        '12',
        '2.5',
      ),
    ).toThrow(/unvollständig/);
  });

  it('continues to reject ambiguous or missing target clock times during a combined correction', () => {
    vi.stubEnv('TZ', 'Europe/Berlin');
    const summer = { ...entry, occurred_at: '2025-07-12T00:30:01.123456Z' };
    expect(executionAmountCorrection(summer, '2025-01-12', true, '12', '2,5')).toHaveProperty(
      'executed_at',
      '2025-01-12T01:30:01.123456Z',
    );
    expect(() => executionAmountCorrection(summer, '2025-03-30', true, '12', '2,5')).toThrow(
      /Zeitumstellung/,
    );
    expect(() => executionAmountCorrection(summer, '2025-10-26', true, '12', '2,5')).toThrow(
      /Zeitumstellung/,
    );
  });
});
