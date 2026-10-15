import { MarketApiError } from '../../market/services/http';

const messages: Record<string, string> = {
  SOURCE_VERSION_MISMATCH:
    'Die Review-Version hat sich geändert. Lade den Stand neu und bestätige die neue Version ausdrücklich.',
  SOURCE_NOT_READY: 'Der FT-011-Owner gibt diesen Reviewstand noch nicht zur Übergabe frei.',
  MATERIALIZATION_CONFLICT:
    'Eine parallele Übergabe steht im Konflikt. Lade den Status neu, bevor du erneut übergibst.',
  IDEMPOTENCY_KEY_REUSED:
    'Dieser Übergabeauftrag gehört zu einem anderen Stand. Lade die konkrete Review-Version neu.',

  POST_TRADE_NOT_ELIGIBLE:
    'Die Nachbeobachtung kann erst nach vollständigem wirtschaftlichem Exit gestartet werden.',
  POST_TRADE_OBSERVATION_ALREADY_EXISTS: 'Für diesen Trade existiert bereits eine Nachbeobachtung.',
  UNDERLYING_LISTING_NOT_RESOLVABLE:
    'Das historische Underlying-Listing konnte nicht eindeutig bestimmt werden.',
  POST_TRADE_OBSERVATION_NOT_FOUND: 'Für diesen Trade existiert noch keine Nachbeobachtung.',
  EXIT_REVIEW_NOT_FOUND: 'Für diesen Trade existiert noch kein Exit Review.',
  OBSERVATION_HORIZON_NOT_COMPLETE: 'Der Beobachtungshorizont ist noch nicht vollständig erreicht.',
  EXIT_REVIEW_INCOMPLETE: 'Alle vier Bewertungen müssen vor der Finalisierung ausgefüllt sein.',
  EXIT_REVIEW_RATIONALE_REQUIRED: 'Für die Finalisierung ist eine Begründung erforderlich.',
  EXIT_REVIEW_NOT_EDITABLE: 'Ein finalisierter Exit Review kann nicht mehr bearbeitet werden.',
};

export function postTradeErrorMessage(error: unknown): string {
  if (error instanceof MarketApiError) {
    return messages[error.response.code] ?? error.response.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Die Post-Trade-Aktion konnte nicht ausgeführt werden.';
}
