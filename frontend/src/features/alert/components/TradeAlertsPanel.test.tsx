import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { alertApiClient } from '../services/client';
import { TradeAlertsPanel } from './TradeAlertsPanel';

vi.mock('../services/client', () => ({
  alertApiClient: {
    forTrade: vi.fn(),
    monitoringHealth: vi.fn(),
    monitoringRuntime: vi.fn(),
  },
}));

const api = vi.mocked(alertApiClient);

describe('TradeAlertsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.monitoringRuntime.mockResolvedValue({
      enabled: false,
      running: false,
      cycle_running: false,
      interval_seconds: 900,
      scope: 'PROCESS_LOCAL_ALL_WORKSPACES',
      price_basis: 'COMPLETED_UNDERLYING_DAILY_LOW_HIGH',
      last_cycle_started_at: null,
      last_cycle_completed_at: null,
      next_run_at: null,
      last_error: null,
      last_error_at: null,
      last_result: null,
    });
    api.monitoringHealth.mockResolvedValue({
      trade_id: 'trade-1',
      position_id: 'position-1',
      status: 'OK',
      reason: 'COMPLETED_DAILY_PRICE_FRESH',
      symbol: 'DAX.INDX',
      trading_date: '2026-09-03',
      market_data_observed_at: '2026-09-03T10:00:00Z',
      age_days: 0,
    });
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
    expect(
      screen.getByText('Kursbezug ungeklärt · historische Meldung nicht belastbar'),
    ).toBeInTheDocument();
    expect(screen.getByText('Automatische Prüfung deaktiviert')).toBeInTheDocument();
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
    expect(
      screen.getByText('Kursbezug ungeklärt · historische Meldung nicht belastbar'),
    ).toBeInTheDocument();
  });

  it('shows Frankfurt basis prices separately from disabled automatic evaluation', async () => {
    api.forTrade.mockResolvedValue([]);
    api.monitoringHealth.mockResolvedValue({
      trade_id: 'trade-1',
      position_id: 'position-1',
      status: 'OK',
      reason: 'COMPLETED_DAILY_PRICE_CURRENT',
      symbol: 'APC',
      trading_date: '2026-09-11',
      market_data_observed_at: '2026-09-14T13:00:00Z',
      age_days: 3,
      basis: {
        underlying_id: 'basis-1',
        name: 'Example basis',
        isin: 'US0378331005',
        listing_id: 'frankfurt-listing',
        venue_mic: 'XFRA',
        currency: 'EUR',
      },
      daily_price: {
        listing_id: 'frankfurt-listing',
        trading_date: '2026-09-11',
        close: '120.12',
        low: '119.01',
        high: '122.34',
        currency: 'EUR',
        provider: 'EODHD',
        provider_symbol: 'APC',
        source_updated_at: null,
        retrieved_at: '2026-09-14T13:00:00Z',
      },
    });
    render(<TradeAlertsPanel tradeId="trade-1" />);
    expect(await screen.findByText('120,12 EUR')).toBeInTheDocument();
    expect(screen.getByText('119,01 EUR')).toBeInTheDocument();
    expect(screen.getByText('122,34 EUR')).toBeInTheDocument();
    expect(screen.getByText(/Example basis · US0378331005 · XFRA · EUR/)).toBeInTheDocument();
    expect(screen.getByText('Daten aktuell')).toBeInTheDocument();
    expect(screen.getByText('Automatische Prüfung deaktiviert')).toBeInTheDocument();
    expect(screen.getByText(/Quellenzeitpunkt: — · Abgerufen:/)).toBeInTheDocument();
  });

  it('keeps data and alerts visible if runtime diagnostics fail', async () => {
    api.forTrade.mockResolvedValue([]);
    api.monitoringRuntime.mockRejectedValue(new Error('unavailable'));
    render(<TradeAlertsPanel tradeId="trade-1" />);
    expect(await screen.findByText('Laufstatus nicht verfügbar')).toBeInTheDocument();
    expect(screen.getByText('Daten aktuell')).toBeInTheDocument();
  });
});
