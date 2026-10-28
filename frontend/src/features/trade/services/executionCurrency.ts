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
  if (resolution.source === 'CONFLICT') return 'widersprüchliche Währungsbelege';
  if (!resolution.currency_code || resolution.source === 'UNKNOWN') return 'unbekannt';
  const origin = {
    USER_CONFIRMED: 'ausdrücklich bestätigt',
    PRIOR_BUYS: 'aus vorherigen Käufen übernommen',
    REPLACED_EXECUTION: 'aus der ursprünglichen Buchung übernommen',
    EXECUTION_DOCUMENT: 'automatisch aus Ausführungsbeleg abgeleitet',
    HISTORICAL_LISTING: 'automatisch aus historischer Notierung abgeleitet',
    HISTORICAL_LISTINGS: 'automatisch aus historischen Notierungen abgeleitet',
  }[resolution.source];
  return `${resolution.currency_code} · ${origin}`;
}

const reasons: Record<string, string> = {
  NO_HISTORICAL_EVIDENCE:
    'Für den Ausführungszeitraum fehlt ein belastbarer Währungsbeleg. Heutige Produktnotierungen allein belegen keine historische Ausführungswährung. Eine einmal zugeordnete historische Quelle wird für passende Buchungen wiederverwendet.',
  DOCUMENT_CONFLICT:
    'Die zugeordneten Ausführungsbelege nennen unterschiedliche Währungen. Bitte die widersprüchlichen Belege prüfen oder die tatsächliche Ausführungswährung gezielt berichtigen.',
  LISTING_CONFLICT:
    'Die historischen Quellen widersprechen sich für denselben Handelsplatz. Bitte die betroffenen Quellen prüfen und fehlerhafte Angaben korrigieren oder widerrufen.',
  MULTIPLE_LISTING_CURRENCIES:
    'Die historischen Handelsplätze verwenden unterschiedliche Währungen. Ein eindeutiger Ausführungsplatz oder eine Währung aus dem Ausführungsbeleg fehlt.',
  LISTING_HISTORY_INCOMPLETE:
    'Die historischen Notierungen decken den Ausführungszeitraum oder die relevanten Handelsplätze nicht vollständig ab. Der Betrag bleibt nicht berechenbar.',
  EXECUTION_TIME_UNKNOWN:
    'Das Ausführungsdatum oder seine Zeitzone ist nicht ausreichend belegt, um eine historische Notierung zuzuordnen.',
  CORRECTION_SOURCE_REVIEW_REQUIRED:
    'Die bisherige Quelle gehört zu einer ersetzten Buchung. Für diese Korrektur fehlt ein passender Nachweis. Bitte die Quelle prüfen oder die tatsächliche Währung dieser Buchung gezielt bestätigen.',
  EVIDENCE_HISTORY_INVALID:
    'Die Quellenhistorie ist widersprüchlich. Bitte die betroffenen Quellenversionen prüfen; bis zur Klärung bleibt der Betrag nicht berechenbar.',
};

export function executionCurrencyReason(reason?: string | null): string | null {
  return reason ? (reasons[reason] ?? `Währungsherkunft ungeklärt (${reason}).`) : null;
}
