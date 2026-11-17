import { render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { alertApiClient } from '../services/client';
import type { AlertResponse } from '../types/api';
import { TradeAlertsPanel } from './TradeAlertsPanel';

vi.mock('../services/client', () => ({
  alertApiClient: {
    forTrade: vi.fn(),
    monitoringHealth: vi.fn(),
    monitoringRuntime: vi.fn(),
  },
}));

const api = vi.mocked(alertApiClient);

function entryObservation(overrides: Partial<AlertResponse> = {}): AlertResponse {
  return {
    id: 'synthetic-entry-alert',
    position_id: 'position-1',
    trade_id: 'trade-1',
    alert_type: 'INDICATIVE_ENTRY_LOSS',
    severity: 'WARNING',
    rule_key: 'synthetic-entry-episode',
    reason: 'Der beobachtete Geldkurs liegt unter dem persönlichen Bruttoeinstand.',
    observed_value: '0.48',
    threshold_value: '0.55',
    market_data_observed_at: null,
    detected_at: '2026-11-17T10:05:00Z',
    status: 'OPEN',
    resolved_at: null,
    notifications: [],
    price_context: {
      scope: 'INDICATIVE_ENTRY_V1',
      rule_version: 'indicative-entry-review-v1',
      qualified_b04: 'false',
      evaluation_mode: 'INDICATIVE_ISSUER',
      basis: 'WARRANT',
      price_type: 'BID',
      currency: 'EUR',
      provider: 'SYNTHETIC',
      provider_identity: 'SYNTHETIC-INSTRUMENT',
      observed_at: null,
      retrieved_at: '2026-11-17T10:04:00Z',
      quote_time_text: '11:03:00',
      quote_time_basis: 'DATE_AND_TIMEZONE_UNKNOWN',
      completed_sessions: '19',
      session_count_at: '2026-11-17T10:05:00Z',
      session_count_basis: 'EVALUATION_TIME',
      remaining_quantity: '2300',
    },
    ...overrides,
  };
}

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

  it.each(['SOURCE_BID', 'INDICATIVE_ISSUER'])(
    'keeps %s entry observations separate from qualified B04 and original time evidence',
    async (evaluationMode) => {
      const alert = entryObservation();
      api.forTrade.mockResolvedValue([
        { ...alert, price_context: { ...alert.price_context, evaluation_mode: evaluationMode } },
      ]);

      render(<TradeAlertsPanel tradeId="trade-1" />);

      expect(
        await screen.findByText('Indikativ · Kurs unter persönlichem Bruttoeinstand'),
      ).toBeInTheDocument();
      expect(screen.getByText(/Teilumfang: Indikative Einstandsbeobachtung/)).toHaveTextContent(
        'indicative-entry-review-v1',
      );
      expect(screen.getByText(/B58-Qualifikation nicht belegt/)).toHaveTextContent(
        'keine B04/B57-Verlustepisode',
      );
      expect(screen.getByText('Beobachteter Geldkurs · indikativ')).toBeInTheDocument();
      expect(screen.getByText('0,48')).toBeInTheDocument();
      expect(screen.getByText('Persönlicher Bruttoeinstand je Stück')).toBeInTheDocument();
      expect(screen.getByText('0,55')).toBeInTheDocument();
      expect(screen.getByText(/Abgeschlossene Basiswertsitzungen: 19/)).toHaveTextContent(
        'zum Prüfzeitpunkt',
      );
      expect(screen.getByText(/Kurszeitpunkt: nicht bekannt/)).toHaveTextContent(
        'Abgerufen: 2026-11-17T10:04:00Z',
      );
      expect(screen.getByText(/Zeitangabe der Quelle: 11:03:00/)).toHaveTextContent(
        'Kursdatum und Zeitzone unbekannt',
      );
      expect(screen.queryByText('Original-Geldkurs')).not.toBeInTheDocument();
      expect(screen.queryByText(/^Regel: B04\/B57/)).not.toBeInTheDocument();
      expect(screen.queryByText(/zur Original-Geldkurszeit/)).not.toBeInTheDocument();
    },
  );

  it('uses the declared BID session time without replacing it by the reminder session count', async () => {
    const alert = entryObservation();
    api.forTrade.mockResolvedValue([
      {
        ...alert,
        price_context: {
          ...alert.price_context,
          evaluation_mode: 'SOURCE_BID',
          observed_at: '2026-11-17T10:00:00Z',
          session_count_at: '2026-11-17T10:00:00Z',
          session_count_basis: 'ORIGINAL_BID',
          review_completed_sessions: '20',
          review_session_count_at: '2026-11-17T10:05:00Z',
        },
      },
    ]);

    render(<TradeAlertsPanel tradeId="trade-1" />);

    expect(await screen.findByText(/Abgeschlossene Basiswertsitzungen: 19/)).toHaveTextContent(
      'zur Original-Geldkurszeit · Stand: 2026-11-17T10:00:00Z',
    );
    expect(screen.queryByText(/Abgeschlossene Basiswertsitzungen: 20/)).not.toBeInTheDocument();
  });

  it('does not extend an old suspended status point from a recent capture time', async () => {
    const alert = entryObservation();
    api.forTrade.mockResolvedValue([
      {
        ...alert,
        price_context: {
          ...alert.price_context,
          source_status_point: 'SUSPENDED',
          source_status_observed_at: '2026-11-16T09:00:00Z',
          source_status_captured_at: '2026-11-17T10:04:00Z',
          status_validity: 'NOT_ESTABLISHED',
        },
      },
    ]);
    render(<TradeAlertsPanel tradeId="trade-1" />);

    expect(await screen.findByText('Letzter belegter Statuspunkt: SUSPENDED')).toBeInTheDocument();
    expect(screen.getByText(/Originalstatuszeit: 2026-11-16T09:00:00Z/)).toHaveTextContent(
      'Erfasst: 2026-11-17T10:04:00Z',
    );
    expect(screen.getByText('Fortgeltung nicht belegt.')).toBeInTheDocument();
    expect(
      screen.queryByText(/Aktueller Marktstatus|aktuell SUSPENDED|aktuell gesperrt/),
    ).not.toBeInTheDocument();
  });

  it.each(['POSITION_REVIEW_DUE', 'POSITION_DATA_UNAVAILABLE'] as const)(
    'renders %s as a price-free persisted notice and only uses existing reads',
    async (alertType) => {
      const alert = entryObservation();
      api.forTrade.mockResolvedValue([
        {
          ...alert,
          alert_type: alertType,
          observed_value: null,
          threshold_value: null,
          reason: 'Synthetischer Anlass des gespeicherten Hinweises.',
          price_context: {
            ...alert.price_context,
            price_type: null,
            review_completed_sessions: '20',
            review_session_count_at: '2026-11-17T10:05:00Z',
            data_problem_reasons:
              alertType === 'POSITION_DATA_UNAVAILABLE' ? 'QUOTE_MISSING,CURRENCY_MISSING' : null,
          },
        },
      ]);

      render(<TradeAlertsPanel tradeId="trade-1" />);

      expect(
        await screen.findByText(
          alertType === 'POSITION_REVIEW_DUE'
            ? 'Prüfhinweis · 20 Basiswertsitzungen abgeschlossen'
            : 'Datenproblem · Einstandsbeobachtung nicht auswertbar',
        ),
      ).toBeInTheDocument();
      if (alertType === 'POSITION_REVIEW_DUE') {
        expect(
          screen.getByText(/Abgeschlossene Basiswertsitzungen zum Prüfzeitpunkt: 20/),
        ).toHaveTextContent('Stand: 2026-11-17T10:05:00Z');
        expect(screen.getByText(/Kalenderbasierter Prüfhinweis/)).toHaveTextContent(
          'keinen Verlust',
        );
      } else {
        expect(screen.getByText(/Ein bestehender Verlusthinweis bleibt/)).toBeInTheDocument();
        expect(screen.getByText('QUOTE_MISSING,CURRENCY_MISSING')).toBeInTheDocument();
      }
      expect(screen.queryByText('Beobachtet')).not.toBeInTheDocument();
      expect(screen.queryByText('Schwelle')).not.toBeInTheDocument();
      expect(screen.queryByText('Original-Geldkurs')).not.toBeInTheDocument();
      expect(screen.queryByText('Persönlicher Bruttoeinstand je Stück')).not.toBeInTheDocument();
      expect(screen.queryByText('Marktdaten')).not.toBeInTheDocument();
      expect(screen.queryByText('0')).not.toBeInTheDocument();
      expect(screen.queryByText('NaN')).not.toBeInTheDocument();
      expect(screen.queryByText(/Kursbezug ungeklärt/)).not.toBeInTheDocument();
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
      expect(api.forTrade).toHaveBeenCalledExactlyOnceWith('trade-1', expect.any(AbortSignal));
      expect(api.monitoringHealth).toHaveBeenCalledExactlyOnceWith(
        'trade-1',
        expect.any(AbortSignal),
      );
      expect(api.monitoringRuntime).toHaveBeenCalledExactlyOnceWith(expect.any(AbortSignal));
    },
  );

  it('keeps an existing entry observation visible next to a separate data problem', async () => {
    api.forTrade.mockResolvedValue([
      entryObservation(),
      entryObservation({
        id: 'synthetic-data-alert',
        alert_type: 'POSITION_DATA_UNAVAILABLE',
        observed_value: null,
        threshold_value: null,
        reason: 'Eine spätere Kurslieferung fehlt.',
        detected_at: '2026-11-17T10:10:00Z',
      }),
    ]);

    render(<TradeAlertsPanel tradeId="trade-1" />);

    const loss = await screen.findByText('Indikativ · Kurs unter persönlichem Bruttoeinstand');
    const data = screen.getByText('Datenproblem · Einstandsbeobachtung nicht auswertbar');
    expect(screen.getByText('2 offen')).toBeInTheDocument();
    expect(within(loss.closest('li')!).getByText('0,48')).toBeInTheDocument();
    expect(within(loss.closest('li')!).getByText('OPEN')).toBeInTheDocument();
    expect(within(data.closest('li')!).queryByText('0,48')).not.toBeInTheDocument();
    expect(
      within(data.closest('li')!).getByText('Eine spätere Kurslieferung fehlt.'),
    ).toBeInTheDocument();
  });

  it('does not convert a missing numeric value into a zero price', async () => {
    api.forTrade.mockResolvedValue([
      entryObservation({ observed_value: null, threshold_value: null }),
    ]);
    render(<TradeAlertsPanel tradeId="trade-1" />);

    const loss = await screen.findByText('Indikativ · Kurs unter persönlichem Bruttoeinstand');
    const row = within(loss.closest('li')!);
    expect(row.queryByText('0')).not.toBeInTheDocument();
    expect(row.getAllByText('—')).toHaveLength(3);
  });

  it.each([
    ['REVIEW_POSITION_CLOSED', true],
    ['REVIEW_ALERT_RESOLVED', true],
    ['REVIEW_ALERT_INVALIDATED', true],
    ['REVIEW_TRADE_CANCELLED', true],
    ['REVIEW_TRADE_MISSING', true],
    ['REVIEW_TRANSPORT_ERROR', false],
  ] as const)(
    'renders delivery outcome %s without inventing recovery',
    async (errorCode, suppressed) => {
      api.forTrade.mockResolvedValue([
        entryObservation({
          notifications: [
            {
              id: 'synthetic-notification',
              channel: 'TELEGRAM',
              destination_key: 'synthetic',
              status: 'FAILED',
              created_at: '2026-11-17T10:05:00Z',
              last_delivery: {
                status: 'FAILED',
                attempted_at: '2026-11-17T10:06:00Z',
                completed_at: '2026-11-17T10:06:00Z',
                retryable: !suppressed,
                error_code: errorCode,
                error_message: 'Synthetischer Zustellgrund.',
              },
            },
          ],
        }),
      ]);
      render(<TradeAlertsPanel tradeId="trade-1" />);

      expect(
        await screen.findByText(
          suppressed
            ? 'TELEGRAM: Versand unterdrückt · Synthetischer Zustellgrund.'
            : 'TELEGRAM: fehlgeschlagen',
        ),
      ).toBeInTheDocument();
      expect(screen.getByText('OPEN')).toBeInTheDocument();
      expect(screen.queryByText('TELEGRAM: zugestellt')).not.toBeInTheDocument();
    },
  );

  it('does not describe every invalidated observation as an unqualified price binding', async () => {
    api.forTrade.mockResolvedValue([
      entryObservation({
        status: 'INVALIDATED',
        invalidation_reason: 'OWNER_BASIS_CHANGED',
      }),
    ]);
    render(<TradeAlertsPanel tradeId="trade-1" />);

    expect(
      await screen.findByText(/Hinweis durch eine neue Bewertung ungültig/),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Meldung wegen ungeklärtem Kursbezug ungültig/),
    ).not.toBeInTheDocument();
  });
});
