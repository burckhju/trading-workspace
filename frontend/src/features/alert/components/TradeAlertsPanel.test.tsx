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
    expect(screen.queryByRole('heading', { name: 'Trade Timeline' })).not.toBeInTheDocument();
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
  it('keeps an issuer source clock separate from receipt and detection time', async () => {
    api.forTrade.mockResolvedValue([
      {
        id: 'issuer-alert',
        position_id: 'position-1',
        trade_id: 'trade-1',
        alert_type: 'STOP_REACHED',
        severity: 'WARNING',
        rule_key: 'CURRENT_STOP',
        reason: 'Indikativer Geldkurs unter Stop',
        observed_value: '0.94',
        threshold_value: '1.00',
        market_data_observed_at: null,
        detected_at: '2026-09-22T18:20:08Z',
        status: 'OPEN',
        resolved_at: null,
        notifications: [],
        price_context: {
          basis: 'WARRANT',
          currency: 'EUR',
          price_type: 'BID',
          provider: 'JPMORGAN',
          provider_identity: 'DE000JE7KTY8',
          observed_at: null,
          retrieved_at: '2026-09-22T18:20:04Z',
          quote_time_text: '20:18:16',
          quote_time_basis: 'DATE_AND_TIMEZONE_UNKNOWN',
          evaluation_mode: 'INDICATIVE_ISSUER',
          warning: 'QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY',
        },
      },
    ]);
    render(<TradeAlertsPanel tradeId="trade-1" />);
    expect(await screen.findByText('Stop erreicht (indikative Prüfung)')).toBeInTheDocument();
    expect(screen.getByText(/Zeitangabe der Quelle: 20:18:16/)).toHaveTextContent(
      'Kursdatum und Zeitzone unbekannt',
    );
    expect(screen.getByText(/Kurszeitpunkt: nicht bekannt/)).toHaveTextContent(
      'Abgerufen: 2026-09-22T18:20:04Z',
    );
    expect(screen.getByText(/Indikative Prüfung · QUOTE_TIMESTAMP/)).toHaveTextContent(
      'Keine Orderfreigabe',
    );
  });

  it('renders B04 scope and quantity while keeping data problems and suppression separate', async () => {
    api.monitoringHealth.mockResolvedValue({
      trade_id: 'trade-1',
      position_id: 'position-1',
      status: 'MISSING',
      reason: 'SYNTHETIC_DATA_GAP',
      symbol: null,
      trading_date: null,
      market_data_observed_at: null,
      age_days: null,
    });
    api.forTrade.mockResolvedValue([
      {
        id: 'b04-alert',
        position_id: 'position-1',
        trade_id: 'trade-1',
        alert_type: 'HEBELTRADER_B04_LOSS',
        severity: 'WARNING',
        rule_key: 'synthetic-b04-episode',
        reason: 'Original-Geldkurs liegt unter dem persönlichen Bruttoeinstand.',
        observed_value: '0.48',
        threshold_value: '0.55',
        market_data_observed_at: '2026-11-17T10:00:00Z',
        detected_at: '2026-11-17T10:00:05Z',
        status: 'RESOLVED',
        resolved_at: '2026-11-17T10:01:00Z',
        price_context: {
          basis: 'WARRANT',
          currency: 'EUR',
          price_type: 'BID',
          provider: 'SYNTHETIC',
          observed_at: '2026-11-17T10:00:00Z',
          rule_version: 'hebeltrader-b04-b57-v1',
          remaining_quantity: '2300',
          completed_sessions_at_bid: '20',
        },
        notifications: [
          {
            id: 'b04-notification',
            channel: 'TELEGRAM',
            destination_key: 'synthetic',
            status: 'FAILED',
            created_at: '2026-11-17T10:00:05Z',
            last_delivery: {
              status: 'FAILED',
              attempted_at: '2026-11-17T10:01:00Z',
              completed_at: '2026-11-17T10:01:00Z',
              retryable: false,
              error_code: 'B04_POSITION_CLOSED',
              error_message:
                'Effektive Ausführungen belegen Vollverkauf; B04-Zustellung unterdrückt.',
            },
          },
        ],
      },
    ]);
    render(<TradeAlertsPanel tradeId="trade-1" />);
    expect(
      await screen.findByText('Hebeltrader · Verlust nach 20 Basiswertsitzungen'),
    ).toBeInTheDocument();
    expect(screen.getByText('Regel: B04/B57 · hebeltrader-b04-b57-v1')).toBeInTheDocument();
    expect(screen.getByText(/Restmenge bei Auslösung: 2300/)).toHaveTextContent(
      'Abgeschlossene Basiswertsitzungen zur Geldkurszeit: 20',
    );
    expect(screen.getByText('Original-Geldkurs')).toBeInTheDocument();
    expect(screen.getByText('Persönlicher Bruttoeinstand je Stück')).toBeInTheDocument();
    expect(screen.getByText('Daten fehlen')).toBeInTheDocument();
    expect(screen.getByText(/TELEGRAM: Versand unterdrückt/)).toHaveTextContent('Vollverkauf');
    expect(screen.queryByText('TELEGRAM: zugestellt')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /kaufen|verkaufen|ausführen/i }),
    ).not.toBeInTheDocument();
    expect(api.forTrade).toHaveBeenCalledTimes(1);
  });
});
