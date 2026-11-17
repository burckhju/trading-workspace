import type { AlertType } from '../types/api';

const titles: Record<AlertType, string> = {
  STOP_REACHED: 'Stop erreicht',
  TARGET_REACHED: 'Ziel erreicht',
  RISK_TREND_CHANGED: 'Trendverschlechterung',
  RISK_VOLATILITY_HIGH: 'Erhöhte realisierte Volatilität',
  HEBELTRADER_B04_LOSS: 'Hebeltrader · Verlust nach 20 Basiswertsitzungen',
};

export function alertTypeLabel(value: string): string {
  return Object.hasOwn(titles, value) ? titles[value as AlertType] : value;
}
