import type {
  ExecutionCurrencyConfirmation,
  ExecutionCurrencyDeclaration,
  ExecutionCurrencyResolution,
} from '../types/api';

export interface ExecutionCurrencyDraft {
  code: string;
  note: string;
}

export function emptyExecutionCurrency(): ExecutionCurrencyDraft {
  return { code: '', note: '' };
}

/** The explicit booking/save action confirms the entered actual price currency. */
export function executionCurrencyDeclaration(draft: ExecutionCurrencyDraft): {
  currency_confirmation?: ExecutionCurrencyDeclaration;
} {
  const code = draft.code.trim().toUpperCase();
  if (!code && !draft.note.trim()) return {};
  if (!/^[A-Z]{3}$/.test(code)) {
    throw new Error('Bitte den dreistelligen Währungscode der tatsächlichen Ausführung angeben.');
  }
  return {
    currency_confirmation: {
      currency_code: code,
      source: 'USER_CONFIRMED',
      note: draft.note.trim() || null,
    },
  };
}

/** Present the owner's resolution; never derive a currency from prices or listings. */
export function executionCurrencyText(
  resolution?: ExecutionCurrencyResolution | null,
  confirmation?: ExecutionCurrencyConfirmation | null,
): string {
  if (!resolution) {
    return confirmation ? `${confirmation.currency_code} · ausdrücklich bestätigt` : 'unbekannt';
  }
  if (resolution.source === 'MIXED') return 'widersprüchliche Kaufwährungen';
  if (!resolution.currency_code || resolution.source === 'UNKNOWN') return 'unbekannt';
  const origin = {
    USER_CONFIRMED: 'ausdrücklich bestätigt',
    PRIOR_BUYS: 'aus vorherigen Käufen übernommen',
    REPLACED_EXECUTION: 'aus der ursprünglichen Buchung übernommen',
  }[resolution.source];
  return `${resolution.currency_code} · ${origin}`;
}
