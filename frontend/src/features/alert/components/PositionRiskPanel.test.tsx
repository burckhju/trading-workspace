import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { riskApi } from '../services/risk';
import type { RiskView } from '../types/risk';
import { PositionRiskPanel } from './PositionRiskPanel';

vi.mock('../services/risk', () => ({
  riskApi: {
    read: vi.fn(),
    history: vi.fn(),
    evaluate: vi.fn(),
    preview: vi.fn(),
    configure: vi.fn(),
  },
}));
function view(): RiskView {
  return {
    trade_id: 'trade-1',
    evaluated_at: '2026-09-24T00:00:00Z',
    snapshot_id: null,
    input_fingerprint: 'audit-input',
    configuration: {
      revision: 0,
      enabled: false,
      policy_version: 'POSITION_RISK_V1',
      parameters: {
        hysteresis_fraction: '.005',
        confirmation_sessions: 2,
        volatility_high: '.4',
        volatility_reset: '.35',
        maximum_age_days: 4,
      },
    },
    product: { direction: 'CALL', isin: 'SYNTHETIC', ratio: '.1' },
    listing: { symbol: 'TEST', currency: 'EUR', listing_id: 'listing' },
    metrics: {
      status: 'AVAILABLE',
      reason: 'QUALIFIED_COMPLETED_OBSERVATIONS',
      session: '2026-09-23',
      window_start: '2026-08-26',
      observations: 21,
      adjusted_close: '100',
      sma20: '102',
      distance_sma20: '-.02',
      sma20_slope: '-.003',
      realized_volatility20: '.42',
      previous_volatility20: '.3',
      atr14_relative: '.02',
      atr_reason: 'RAW',
      policy_version: 'POSITION_RISK_ANALYTICS_V1',
    },
    assessment: {
      transition: 'CROSSED_BELOW',
      interpretation: 'UNFAVORABLE',
      reason: 'CONFIRMED_SESSION_STATE',
      policy_version: 'POSITION_RISK_V1',
      state: { trend: 'BELOW', pending_sessions: 0, trend_warning: true, volatility_warning: true },
    },
    quote_quality: {
      status: 'LIMITED',
      reasons: ['SOURCE_TIME_OR_TIMEZONE_UNKNOWN', 'ASK_MISSING'],
      bid: '2',
      ask: null,
      spread_mid_percent: null,
      observed_at: null,
      received_at: '2026-09-24T10:00:00Z',
      provider: 'SYNTHETIC',
      bid_volume: 0,
      ask_volume: null,
    },
    comparison: {
      status: 'NOT_EVALUABLE',
      reasons: ['PRODUCT_HISTORY_NOT_AVAILABLE', 'EOD_SESSION_CLOSE_INSTANT_UNVERIFIED'],
      price_type: 'BID_TO_BID',
      underlying_return: null,
      warrant_return: null,
      descriptive_divergence: null,
      times: [],
      normalized_underlying: [],
      normalized_warrant: [],
    },
    input_prices: [
      {
        provider: 'SYNTHETIC',
        provider_symbol: 'TEST',
        trading_date: '2026-09-23',
        adjusted_close: '100',
        retrieved_at: '2026-09-23T22:00:00Z',
        currency: 'EUR',
      },
    ],
  };
}
beforeEach(() => {
  vi.mocked(riskApi.read).mockResolvedValue(view());
});
describe('qualified risk panel', () => {
  it('separates risk metrics, original time and receipt; read-only performs no writes', async () => {
    render(<PositionRiskPanel tradeId="trade-1" readOnly />);
    await screen.findByText(/Wechsel unter SMA20 bestätigt/);
    expect(screen.getByText('42 %')).toBeInTheDocument();
    expect(screen.getByText(/Echte Optionsschein-Kurshistorie fehlt/)).toBeInTheDocument();
    expect(screen.getByText(/Originalkurszeit: unbekannt/)).toBeInTheDocument();
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(riskApi.configure).not.toHaveBeenCalled();
    expect(riskApi.evaluate).not.toHaveBeenCalled();
  });
  it('requires explicit confirmation and sends the exact current revision and parameters', async () => {
    vi.mocked(riskApi.configure).mockResolvedValue({});
    render(<PositionRiskPanel tradeId="trade-1" />);
    const activate = await screen.findByRole('button', {
      name: 'Warnregeln für diese Position aktivieren',
    });
    expect(activate).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(activate);
    await waitFor(() =>
      expect(riskApi.configure).toHaveBeenCalledWith(
        'trade-1',
        view(),
        view().configuration.parameters,
        true,
      ),
    );
    await waitFor(() => expect(screen.getByRole('checkbox')).not.toBeChecked());
  });
  it('previews changed parameters without activation; stores only the configured set', async () => {
    vi.mocked(riskApi.preview).mockResolvedValue(view());
    vi.mocked(riskApi.evaluate).mockResolvedValue({ ...view(), snapshot_id: 'saved' });
    render(<PositionRiskPanel tradeId="trade-1" />);
    fireEvent.change(await screen.findByLabelText('Bestätigungstage'), { target: { value: '3' } });
    fireEvent.click(screen.getByText('Parameter unverbindlich prüfen'));
    await screen.findByText(/Parametervorschau/);
    expect(riskApi.preview).toHaveBeenCalledWith(
      'trade-1',
      expect.objectContaining({ confirmation_sessions: 3 }),
    );
    expect(screen.getByText('Aktuelle Konfiguration auswerten und speichern')).toBeDisabled();
    fireEvent.click(screen.getByText('Zur aktuellen Konfiguration'));
    await waitFor(() =>
      expect(screen.getByText('Aktuelle Konfiguration auswerten und speichern')).toBeEnabled(),
    );
    fireEvent.click(screen.getByText('Aktuelle Konfiguration auswerten und speichern'));
    await waitFor(() => expect(riskApi.evaluate).toHaveBeenCalledWith('trade-1'));
    expect(riskApi.configure).not.toHaveBeenCalled();
  });
  it('shows normalized qualified comparison, gap and immutable history', async () => {
    const data = view();
    data.metrics.status = 'NOT_EVALUABLE';
    data.metrics.reason = 'EOD_STALE';
    data.metrics.atr14_relative = null;
    data.comparison = {
      status: 'AVAILABLE',
      reasons: [],
      price_type: 'BID_TO_BID',
      underlying_return: '.01',
      warrant_return: '-.1',
      descriptive_divergence: true,
      times: ['2026-09-22T12:00:00Z', '2026-09-23T12:00:00Z'],
      normalized_underlying: ['100', '101'],
      normalized_warrant: ['100', '90'],
    };
    vi.mocked(riskApi.read).mockResolvedValue(data);
    vi.mocked(riskApi.history).mockResolvedValue([{ ...data, snapshot_id: 'past' }]);
    render(<PositionRiskPanel tradeId="trade-1" />);
    await screen.findByText(/Basiswertdaten veraltet/);
    expect(screen.getByRole('table')).toHaveTextContent('101');
    expect(screen.getByText(/keine nachgewiesene Fehlbewertung/)).toBeInTheDocument();
    fireEvent.click(screen.getByText('Letzte 20 Auswertungen anzeigen'));
    await waitFor(() => expect(riskApi.history).toHaveBeenCalledWith('trade-1'));
  });
  it('reports command failures and supports explicit deactivation', async () => {
    const active = view();
    active.configuration.enabled = true;
    vi.mocked(riskApi.read).mockResolvedValue(active);
    vi.mocked(riskApi.configure).mockRejectedValue(new Error('409'));
    render(<PositionRiskPanel tradeId="trade-1" />);
    await screen.findByText(/Warnregeln aktiv/);
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByText('Warnregeln deaktivieren'));
    await screen.findByRole('alert');
    expect(riskApi.configure).toHaveBeenCalledWith(
      'trade-1',
      active,
      active.configuration.parameters,
      false,
    );
  });
  it('clears the previous trade on identity changes and reports unavailable reads', async () => {
    const component = render(<PositionRiskPanel tradeId="trade-1" />);
    await screen.findByText(/Wechsel unter SMA20 bestätigt/);
    vi.mocked(riskApi.read).mockRejectedValue(new Error('404'));
    component.rerender(<PositionRiskPanel tradeId="trade-2" />);
    await screen.findByRole('alert');
    expect(screen.queryByText(/Wechsel unter SMA20 bestätigt/)).not.toBeInTheDocument();
  });
});
