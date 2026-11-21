import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { useCallback, useRef } from 'react';
import { createMemoryRouter, Link, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { riskApi } from '../services/risk';
import type { RiskView } from '../types/risk';
import { PositionRiskPanel } from './PositionRiskPanel';
import type { PositionRiskPending } from '../types/pending';
import {
  TradePendingChangesProvider,
  useTradePendingChanges,
} from '../../trade/components/TradePendingChanges';

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
  sessionStorage.clear();
  vi.mocked(riskApi.read).mockResolvedValue(view());
});

function HostedRisk() {
  const ref = useRef<PositionRiskPending | null>(null);
  const { notify, isBusyExceptSelf } = useTradePendingChanges('risk-test-host', {
    isBusy: () => ref.current?.isBusy() ?? false,
    isDirty: () => ref.current?.isDirty() ?? false,
    onDiscard: () => ref.current?.discard(),
  });
  const onPendingChange = useCallback(
    (value: PositionRiskPending | null) => {
      ref.current = value;
      notify();
    },
    [notify],
  );
  return (
    <>
      <Link to="/elsewhere">Positionsübersicht öffnen</Link>
      <PositionRiskPanel
        tradeId="trade-1"
        onPendingChange={onPendingChange}
        isContextPending={isBusyExceptSelf}
      />
    </>
  );
}
function showHostedRisk() {
  const router = createMemoryRouter(
    [
      {
        path: '/risk',
        element: (
          <TradePendingChangesProvider>
            <HostedRisk />
          </TradePendingChangesProvider>
        ),
      },
      { path: '/elsewhere', element: <h1>Positionsübersicht</h1> },
    ],
    { initialEntries: ['/risk'] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

describe('shared host protection for risk and IV drafts', () => {
  it('guards changed risk parameters after a preview and discards only through the single host dialog', async () => {
    const preview = view();
    preview.configuration.parameters.confirmation_sessions = 3;
    vi.mocked(riskApi.preview).mockResolvedValueOnce(preview);
    showHostedRisk();
    fireEvent.change(await screen.findByLabelText('Bestätigungstage'), { target: { value: '3' } });
    fireEvent.click(screen.getByRole('button', { name: 'Parameter unverbindlich prüfen' }));
    await screen.findByText(/Parametervorschau · gespeicherte Aktivierung unverändert/);
    fireEvent.click(screen.getByRole('link', { name: 'Positionsübersicht öffnen' }));
    expect(screen.getAllByRole('alertdialog')).toHaveLength(1);
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    expect(screen.getByLabelText('Bestätigungstage')).toHaveValue(3);
    const unload = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(unload);
    expect(unload.defaultPrevented).toBe(true);
    fireEvent.click(screen.getByRole('link', { name: 'Positionsübersicht öffnen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
    expect(await screen.findByRole('heading', { name: 'Positionsübersicht' })).toBeVisible();
    expect(riskApi.configure).not.toHaveBeenCalled();
  });

  it('retains the risk write lock until readback, blocks duplicate activation and prevents discard departure', async () => {
    let finish!: (value: unknown) => void;
    vi.mocked(riskApi.configure).mockReturnValueOnce(
      new Promise((resolve) => {
        finish = resolve;
      }),
    );
    showHostedRisk();
    const activate = await screen.findByRole('button', {
      name: 'Warnregeln für diese Position aktivieren',
    });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(activate);
    fireEvent.click(activate);
    expect(riskApi.configure).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByRole('link', { name: 'Positionsübersicht öffnen' }));
    expect(screen.getAllByRole('alertdialog')).toHaveLength(1);
    expect(screen.getByRole('heading', { name: 'Speicherung läuft' })).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Eingaben verwerfen und wechseln' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    await act(async () => {
      finish({});
      await Promise.resolve();
    });
    await waitFor(() => expect(screen.getByRole('checkbox')).not.toBeChecked());
    fireEvent.click(screen.getByRole('link', { name: 'Positionsübersicht öffnen' }));
    expect(await screen.findByRole('heading', { name: 'Positionsübersicht' })).toBeVisible();
  });

  it('honors another host participant lock before preview or activation', async () => {
    const { rerender } = render(
      <PositionRiskPanel tradeId="trade-1" isContextPending={() => false} />,
    );
    await screen.findByLabelText('Bestätigungstage');
    fireEvent.click(screen.getByRole('checkbox'));
    rerender(<PositionRiskPanel tradeId="trade-1" isContextPending={() => true} />);
    const activate = screen.getByRole('button', {
      name: 'Warnregeln für diese Position aktivieren',
    });
    expect(activate).toBeDisabled();
    fireEvent.click(activate);
    fireEvent.click(screen.getByRole('button', { name: 'Parameter unverbindlich prüfen' }));
    expect(riskApi.configure).not.toHaveBeenCalled();
    expect(riskApi.preview).not.toHaveBeenCalled();
  });

  it('lets already preserved IV assumptions survive route departure without a redundant discard prompt', async () => {
    const router = showHostedRisk();
    await screen.findByLabelText('Bestätigungstage');
    fireEvent.click(screen.getByText('Modelllabor: IV-Szenario mit eigenen Annahmen'));
    fireEvent.change(screen.getByLabelText('IV-Änderung (Prozentpunkte)'), {
      target: { value: '-7' },
    });
    fireEvent.click(screen.getByRole('link', { name: 'Positionsübersicht öffnen' }));
    expect(await screen.findByRole('heading', { name: 'Positionsübersicht' })).toBeVisible();
    expect(screen.queryByRole('alertdialog')).toBeNull();
    await act(() => router.navigate('/risk'));
    expect(await screen.findByLabelText('IV-Änderung (Prozentpunkte)')).toHaveValue(-7);
  });

  it('guards IV assumptions if session storage cannot preserve them', async () => {
    const storage = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage unavailable');
    });
    try {
      showHostedRisk();
      await screen.findByLabelText('Bestätigungstage');
      fireEvent.click(screen.getByText('Modelllabor: IV-Szenario mit eigenen Annahmen'));
      fireEvent.change(screen.getByLabelText('IV-Änderung (Prozentpunkte)'), {
        target: { value: '-7' },
      });
      expect(screen.getByText(/nicht zwischengespeichert/)).toBeVisible();
      fireEvent.click(screen.getByRole('link', { name: 'Positionsübersicht öffnen' }));
      expect(screen.getAllByRole('alertdialog')).toHaveLength(1);
      fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
      expect(screen.getByLabelText('IV-Änderung (Prozentpunkte)')).toHaveValue(-7);
      fireEvent.click(screen.getByRole('link', { name: 'Positionsübersicht öffnen' }));
      fireEvent.click(screen.getByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
      expect(await screen.findByRole('heading', { name: 'Positionsübersicht' })).toBeVisible();
    } finally {
      storage.mockRestore();
    }
  });
});
describe('qualified risk panel', () => {
  it('separates risk metrics, original time and receipt; read-only performs no writes', async () => {
    render(<PositionRiskPanel tradeId="trade-1" readOnly />);
    await screen.findByText(/Wechsel unter SMA20 bestätigt/);
    const summary = within(screen.getByRole('region', { name: 'Risikoübersicht' }));
    expect(summary.getByText('42 %')).toBeVisible();
    expect(summary.getByText('Deaktiviert')).toBeVisible();
    expect(summary.getByText('Optionsscheinquote: Eingeschränkt')).toBeVisible();
    expect(screen.getByText(/Originalkurszeit: unbekannt/)).not.toBeVisible();
    fireEvent.click(screen.getByText('Kennzahlen, Kursqualität und Quellen im Detail'));
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
    const summary = within(await screen.findByRole('region', { name: 'Risikoübersicht' }));
    expect(summary.getByText('Basiswertdaten veraltet')).toBeVisible();
    expect(summary.getAllByText('Nicht auswertbar')).toHaveLength(2);
    expect(summary.queryByText('42 %')).not.toBeInTheDocument();
    expect(summary.getByText(/Bisheriger Warnzustand bleibt/)).toBeVisible();
    fireEvent.click(screen.getByText('Kennzahlen, Kursqualität und Quellen im Detail'));
    expect(screen.getByRole('table')).toHaveTextContent('101');
    expect(screen.getByText(/keine nachgewiesene Fehlbewertung/)).toBeInTheDocument();
    fireEvent.click(screen.getByText('Letzte 20 Auswertungen anzeigen'));
    await waitFor(() => expect(riskApi.history).toHaveBeenCalledWith('trade-1'));
  });
  it('shows a pending change and preview independently from active warnings', async () => {
    const pending = view();
    pending.configuration.enabled = true;
    pending.assessment.transition = 'CONFIRMING';
    pending.assessment.interpretation = 'FAVORABLE';
    pending.assessment.state.pending_sessions = 1;
    pending.assessment.state.trend_warning = false;
    pending.assessment.state.volatility_warning = false;
    vi.mocked(riskApi.read).mockResolvedValue(pending);
    vi.mocked(riskApi.preview).mockResolvedValue({
      ...pending,
      configuration: { ...pending.configuration, enabled: false },
    });
    render(<PositionRiskPanel tradeId="trade-1" />);
    const summary = within(await screen.findByRole('region', { name: 'Risikoübersicht' }));
    expect(summary.getByText(/1 von 2 Bestätigungstagen/)).toBeVisible();
    expect(summary.getByText('Aktiv')).toBeVisible();
    expect(summary.getByText('Kein erhöhter Warnzustand in der Auswertung')).toBeVisible();
    fireEvent.click(screen.getByText('Parameter unverbindlich prüfen'));
    expect(await summary.findByText(/Unverbindliche Vorschau/)).toBeVisible();
    expect(summary.getByText('Vorschau', { exact: true })).toBeVisible();
    expect(summary.queryByText('Deaktiviert')).not.toBeInTheDocument();
    expect(riskApi.configure).not.toHaveBeenCalled();
  });
  it('identifies an initial state without claiming a trend break', async () => {
    const initial = view();
    initial.assessment.transition = 'INITIALIZED';
    initial.assessment.state.trend_warning = false;
    vi.mocked(riskApi.read).mockResolvedValue(initial);
    render(<PositionRiskPanel tradeId="trade-1" readOnly />);
    const summary = within(await screen.findByRole('region', { name: 'Risikoübersicht' }));
    expect(summary.getByText('Ausgangszustand, noch kein Trendbruch.')).toBeVisible();
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
