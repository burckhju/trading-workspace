import type { ExecutionCurrencyDeclaration } from '../types/api';

export interface ExecutionCurrencyDraft {
  code: string;
  note: string;
  confirmed: boolean;
}

export function emptyExecutionCurrency(): ExecutionCurrencyDraft {
  return { code: '', note: '', confirmed: false };
}

/** An offered or typed code is never an execution fact without the explicit affirmation. */
export function executionCurrencyDeclaration(draft: ExecutionCurrencyDraft): {
  currency_confirmation?: ExecutionCurrencyDeclaration;
} {
  if (!draft.confirmed) return {};
  const code = draft.code.trim().toUpperCase();
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
