import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { alertApiClient } from '../services/client';
import { TradeAlertsPanel } from './TradeAlertsPanel';

vi.mock('../services/client', () => ({
  alertApiClient: {
    forTrade: vi.fn(),
  },
}));

const api = vi.mocked(alertApiClient);

describe('TradeAlertsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows persisted alert and delivery state separately', async () => {
    api.forTrade.mockResolvedValue([
      {
        id: 'alert-1',
        position_id: 'position-1',
        trade_id: 'trade-1',
        alert_type: 'TARGET_REACHED',
        severity: 'INFO',
        rule_key: 'target-1',
        reason: 'Target 1 wurde erreicht.',
        observed_value: '125',
        threshold_value: '120',
        market_data_observed_at: '2026-09-03T10:00:00Z',
        detected_at: '2026-09-03T10:01:00Z',
        status: 'OPEN',
        resolved_at: null,
        notifications: [
          {
            id: 'notification-1',
            channel: 'TELEGRAM',
            destination_key: 'telegram_default',
            status: 'DELIVERED',
            created_at: '2026-09-03T10:01:01Z',
            last_delivery: {
              status: 'DELIVERED',
              attempted_at: '2026-09-03T10:01:02Z',
              completed_at: '2026-09-03T10:01:03Z',
              retryable: false,
              error_code: null,
              error_message: null,
            },
          },
        ],
      },
    ]);

    render(<TradeAlertsPanel tradeId="trade-1" />);

    expect(await screen.findByText('Target erreicht')).toBeInTheDocument();
    expect(screen.getByText('Target 1 wurde erreicht.')).toBeInTheDocument();
    expect(screen.getByText('TELEGRAM: zugestellt')).toBeInTheDocument();
    expect(screen.getByText('1 offen')).toBeInTheDocument();
  });

  it('renders delivery failure without changing the alert state', async () => {
    api.forTrade.mockResolvedValue([
      {
        id: 'alert-1',
        position_id: 'position-1',
        trade_id: 'trade-1',
        alert_type: 'STOP_REACHED',
        severity: 'WARNING',
        rule_key: 'stop',
        reason: 'Stop wurde erreicht.',
        observed_value: '95',
        threshold_value: '100',
        market_data_observed_at: '2026-09-03T10:00:00Z',
        detected_at: '2026-09-03T10:01:00Z',
        status: 'OPEN',
        resolved_at: null,
        notifications: [
          {
            id: 'notification-1',
            channel: 'TELEGRAM',
            destination_key: 'telegram_default',
            status: 'FAILED',
            created_at: '2026-09-03T10:01:01Z',
            last_delivery: {
              status: 'FAILED',
              attempted_at: '2026-09-03T10:01:02Z',
              completed_at: '2026-09-03T10:01:03Z',
              retryable: true,
              error_code: 'TELEGRAM_TIMEOUT',
              error_message: 'timeout',
            },
          },
        ],
      },
    ]);

    render(<TradeAlertsPanel tradeId="trade-1" />);

    expect(await screen.findByText('Stop erreicht')).toBeInTheDocument();
    expect(screen.getByText('OPEN')).toBeInTheDocument();
    expect(screen.getByText('TELEGRAM: fehlgeschlagen')).toBeInTheDocument();
    expect(screen.getByText('(TELEGRAM_TIMEOUT)')).toBeInTheDocument();
  });
});
