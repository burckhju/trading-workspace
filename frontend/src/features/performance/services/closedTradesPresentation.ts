import type { ClosedTradeGroup, ClosedTradeItem } from '../types/api';
import { reasonText } from './presentation';

export const closedTradeGroupText: Record<ClosedTradeGroup, string> = {
  CANCELLED: 'Stornierter Fehleintrag · ausgeschlossen',
  HISTORY_UNRESOLVED: 'Historie oder Vollabschluss ungeklärt',
  OPEN: 'Offener Trade · ausgeschlossen',
  OUTSIDE_PERIOD: 'Vollabschluss außerhalb des Zeitraums · ausgeschlossen',
  OTHER_CURRENCY: 'Vollständig belegte andere Währung · ausgeschlossen',
  PERIOD_UNRESOLVED: 'Abschlusszeitraum ungeklärt',
  MONETARY_UNRESOLVED: 'Vollabschluss im Zeitraum · Gesamtergebnis ungeklärt',
  QUALIFIED: 'Vollständig qualifiziert',
};

export const classificationText: Record<NonNullable<ClosedTradeItem['classification']>, string> = {
  POSITIVE: 'Positiv',
  NEGATIVE: 'Negativ',
  NEUTRAL: 'Neutral · exakt null',
};

export function closedTradeReasonText(reason: string): string {
  if (reason === 'TRADE_OPEN') return 'Die wirksame Historie enthält noch keinen Vollabschluss.';
  if (reason === 'CURRENCY_UNKNOWN') {
    return 'Die Währung aller benötigten Käufe und sämtlicher Verkäufe ist nicht vollständig belegt.';
  }
  if (reason === 'CURRENCY_MIXED') {
    return 'Käufe oder Verkäufe haben unterschiedliche Währungen; ein vollständiges Tradeergebnis ist nicht berechenbar.';
  }
  return reasonText(reason);
}
