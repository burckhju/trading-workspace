import { describe, expect, it } from 'vitest';

import { MarketApiError } from '../../market/services/http';
import { postTradeErrorMessage } from './errors';

describe('postTradeErrorMessage', () => {
  it('translates stable FT-011 backend error codes', () => {
    const error = new MarketApiError(422, {
      code: 'OBSERVATION_HORIZON_NOT_COMPLETE',
      message: 'technical backend message',
      details: [],
      timestamp: '2026-08-18T12:00:00Z',
    });

    expect(postTradeErrorMessage(error)).toBe(
      'Der Beobachtungshorizont ist noch nicht vollständig erreicht.',
    );
  });

  it('falls back to backend message for unknown codes', () => {
    const error = new MarketApiError(409, {
      code: 'UNKNOWN_POST_TRADE_ERROR',
      message: 'Fallback message',
      details: [],
      timestamp: '2026-08-18T12:00:00Z',
    });

    expect(postTradeErrorMessage(error)).toBe('Fallback message');
  });
});
