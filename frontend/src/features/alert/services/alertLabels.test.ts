import { describe, expect, it } from 'vitest';

import { alertTypeLabel } from './alertLabels';

describe('persisted alert labels', () => {
  it('distinguishes indicative entry observations, review reminders and data problems from B04', () => {
    expect(alertTypeLabel('INDICATIVE_ENTRY_LOSS')).toBe(
      'Indikativ · Kurs unter persönlichem Bruttoeinstand',
    );
    expect(alertTypeLabel('POSITION_REVIEW_DUE')).toBe(
      'Prüfhinweis · 20 Basiswertsitzungen abgeschlossen',
    );
    expect(alertTypeLabel('POSITION_DATA_UNAVAILABLE')).toBe(
      'Datenproblem · Einstandsbeobachtung nicht auswertbar',
    );
    expect(alertTypeLabel('HEBELTRADER_B04_LOSS')).toBe(
      'Hebeltrader · Verlust nach 20 Basiswertsitzungen',
    );
    expect(alertTypeLabel('PRODUCT_DEADLINE_REVIEW')).toBe('Produkttermin · Kalendererinnerung');
  });

  it('keeps unknown types explicit without inferring a known rule', () => {
    expect(alertTypeLabel('FUTURE_RULE')).toBe('FUTURE_RULE');
    expect(alertTypeLabel('toString')).toBe('toString');
  });
});
