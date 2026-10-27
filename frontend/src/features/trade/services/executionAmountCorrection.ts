import type { ExecutionCorrectionRequest, TradeTimelineEntryResponse } from '../types/api';
import { executionDateCorrection } from './executionDateCorrection';

// ExecutionRecordModel.quantity uses PostgreSQL Integer, not an application limit.
const maximumQuantity = '2147483647';

export function executionQuantity(value: string): number {
  const input = value.trim();
  if (!/^\d+$/.test(input)) {
    throw new Error(
      'Bitte eine positive ganze Menge ohne Dezimalstellen oder Trennzeichen eingeben.',
    );
  }
  const normalized = input.replace(/^0+(?=\d)/, '');
  if (normalized === '0') {
    throw new Error('Die Menge muss größer als 0 sein. Eine Korrektur storniert keine Buchung.');
  }
  if (
    normalized.length > maximumQuantity.length ||
    (normalized.length === maximumQuantity.length && normalized > maximumQuantity)
  ) {
    throw new Error(
      'Die Menge darf höchstens 2147483647 betragen (speicherbarer Ganzzahlbereich).',
    );
  }
  // The validated 32-bit integer is exactly representable as the API's number.
  return Number(normalized);
}

function decimalValue(value: string, stored = false) {
  const match = /^(\d+)(?:[.,](\d+))?(?:[eE]([+-]?\d+))?$/.exec(value.trim());
  if (!match || (!stored && match[3])) return null;
  const whole = match[1].replace(/^0+(?=\d)/, '');
  const fraction = (match[2] ?? '').replace(/0+$/, '');
  const significant = `${whole}${fraction}`.replace(/^0+/, '');
  const digits = significant.replace(/0+$/, '');
  // Decimal API strings can use exponent notation for a small stored price.
  // Compare their exact decimal value without converting money to a Number.
  const exponent =
    BigInt(match[3] ?? '0') - BigInt(fraction.length) + BigInt(significant.length - digits.length);
  return { whole, fraction, digits, exponent };
}

function samePrice(value: string, original: string): boolean {
  if (value.trim() === original.trim()) return true;
  const current = decimalValue(value);
  const previous = decimalValue(original, true);
  return Boolean(
    current &&
      previous &&
      current.digits === previous.digits &&
      (!current.digits || current.exponent === previous.exponent),
  );
}

/** Only changed prices must meet Numeric(24,10); unchanged source strings remain intact. */
export function executionPrice(value: string, original: string): string {
  if (samePrice(value, original)) return original;
  const decimal = decimalValue(value);
  if (!decimal) {
    throw new Error(
      'Bitte einen vollständigen Preis mit höchstens einem Dezimalpunkt oder Dezimalkomma ' +
        'eingeben, ohne Tausendertrennzeichen oder Exponent.',
    );
  }
  if (!decimal.digits) throw new Error('Der Preis je Einheit muss größer als 0 sein.');
  if (decimal.whole.length > 14 || decimal.fraction.length > 10) {
    throw new Error(
      'Der Preis darf höchstens 14 Vorkomma- und 10 Nachkommastellen haben. ' +
        'Zusätzliche wertgleiche Nullen sind erlaubt; der Preis wird nicht gerundet.',
    );
  }
  return decimal.fraction ? `${decimal.whole}.${decimal.fraction}` : decimal.whole;
}

/** Invalid edits are dirty too, while alternative spellings of the same value are not. */
export function executionAmountChanges(
  entry: TradeTimelineEntryResponse,
  quantity: string,
  price: string,
): { quantity: boolean; price: boolean } {
  let quantityChanged = true;
  try {
    quantityChanged = executionQuantity(quantity) !== entry.quantity;
  } catch {
    // Keep an invalid, unsaved quantity protected by the existing draft guard.
  }
  return {
    quantity: quantityChanged,
    price: entry.price_per_unit === null || !samePrice(price, entry.price_per_unit),
  };
}

/** Reuse the existing date/DST logic and preserve its exact timestamp or date-only payload. */
export function executionAmountCorrection(
  entry: TradeTimelineEntryResponse,
  date: string,
  keepTime: boolean,
  quantity: string,
  price: string,
): ExecutionCorrectionRequest {
  const request = executionDateCorrection(entry, date, keepTime);
  return {
    ...request,
    quantity: executionQuantity(quantity),
    price_per_unit: executionPrice(price, request.price_per_unit),
  };
}
