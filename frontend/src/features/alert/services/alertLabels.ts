import type { AlertType } from '../types/api';

const titles: Record<AlertType, string> = {
  STOP_REACHED: 'Stop erreicht',
  TARGET_REACHED: 'Ziel erreicht',
  RISK_TREND_CHANGED: 'Trendverschlechterung',
  RISK_VOLATILITY_HIGH: 'Erhöhte realisierte Volatilität',
  HEBELTRADER_B04_LOSS: 'Hebeltrader · Verlust nach 20 Basiswertsitzungen',
  INDICATIVE_ENTRY_LOSS: 'Indikativ · Kurs unter persönlichem Bruttoeinstand',
  POSITION_REVIEW_DUE: 'Prüfhinweis · 20 Basiswertsitzungen abgeschlossen',
  PRODUCT_DEADLINE_REVIEW: 'Produkttermin · Kalendererinnerung',
  POSITION_DATA_UNAVAILABLE: 'Datenproblem · Einstandsbeobachtung nicht auswertbar',
};

export function alertTypeLabel(value: string): string {
  return Object.hasOwn(titles, value) ? titles[value as AlertType] : value;
}
