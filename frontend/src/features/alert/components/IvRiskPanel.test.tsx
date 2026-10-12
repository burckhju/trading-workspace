import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MarketApiError } from '../../market/services/http';
import { ivApi } from '../services/iv';
import type { IvModelResult } from '../types/iv';
import type { RiskView } from '../types/risk';
import { IvRiskPanel } from './IvRiskPanel';

vi.mock('../services/iv', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../services/iv')>()),
  ivApi: { preview: vi.fn() },
}));

const view = {
  trade_id: 'iv-test',
  evaluated_at: '2026-10-12T12:00:00Z',
  product: { ratio: '.1', strike_currency: 'USD' },
  listing: { symbol: 'SYN', currency: 'USD' },
  quote_quality: { provider: 'SYNTHETIC', observed_at: null, received_at: '2026-10-12T12:00:00Z' },
  iv: {
    status: 'NOT_EVALUABLE',
    reasons: [
      'SOURCE_TIME_OR_TIMEZONE_UNKNOWN',
      'EXERCISE_STYLE_UNKNOWN',
      'SYNCHRONIZED_UNDERLYING_QUOTE_MISSING',
    ],
    quote_side: null,
    quote_age_seconds: null,
    policy_version: 'IV_READINESS_V1',
    history_status: 'NO_QUALIFIED_IV_HISTORY',
    event_status: 'NO_VERIFIED_EVENT_SOURCE',
  },
} as RiskView;
const result: IvModelResult = {
  status: 'HYPOTHETICAL',
  model_version: 'BSM_CONTINUOUS_YIELD_ACT365_V1',
  iv_origin: 'USER_ASSUMPTION',
  inputs: { currency: 'EUR', iv_decimal: '.35' },
  scenario: {
    quantity: '100',
    underlying_change_percent: '-5',
    iv_change_pp: '-5',
    elapsed_days: '7',
  },
  baseline_price: '1.5',
  scenario_price: '1.0',
  change_per_warrant: '-.5',
  position_change: '-50',
  vega_per_warrant_per_pp: '.02',
  position_vega_per_pp: '2',
  local_iv_change: '-.1',
  isolated_iv_change: '-.098',
  isolated_spot_change: '-.3',
  isolated_time_change: '-.1',
  warnings: [],
};

function fillExample() {
  fireEvent.click(screen.getByText('Modelllabor: IV-Szenario mit eigenen Annahmen'));
  fireEvent.click(screen.getByRole('button', { name: 'Beispielannahmen laden' }));
  fireEvent.change(screen.getByLabelText('Modellgeltung ausdrücklich wählen'), {
    target: { value: 'EUROPEAN' },
  });
}

describe('IV availability and isolated assumption calculator', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it('shows missing values as unavailable, keeps receipt distinct and explains historical/event gaps', () => {
    render(<IvRiskPanel view={view} />);
    expect(screen.getAllByText('Nicht verfügbar')).toHaveLength(6);
    expect(screen.getByText(/IV-Risikoniveau ist unbekannt/)).toBeInTheDocument();
    fireEvent.click(screen.getByText('Warum IV-Kennzahlen fehlen · Daten und Grenzen'));
    expect(screen.getByText(/Originalkurszeit Optionsschein:/)).toHaveTextContent('unbekannt');
    expect(screen.getByText(/Originalkurszeit Optionsschein:/)).toHaveTextContent(
      '2026-10-12T12:00:00Z',
    );
    expect(screen.getByText(/Keine qualifizierte IV-Historie/)).toBeVisible();
    expect(screen.getByText(/Keine verifizierte Ereignisquelle/)).toBeVisible();
    expect(screen.getByText(/Tageskurse ersetzen ihn nicht/)).toBeVisible();
    expect(screen.queryByText('0 %')).not.toBeInTheDocument();
    expect(ivApi.preview).not.toHaveBeenCalled();
  });

  it('handles old snapshots without fabricated IV and displays provenance when known', () => {
    const { rerender } = render(<IvRiskPanel view={{ ...view, iv: null }} />);
    expect(screen.getByText(/ältere Auswertung/)).toBeInTheDocument();
    rerender(
      <IvRiskPanel
        view={{
          ...view,
          iv: { ...view.iv!, quote_age_seconds: 120, quote_side: 'BID_ONLY' },
          quote_evidence: {
            provider: 'GETTEX',
            identity_key: 'route-b',
            quote: { currency: 'EUR', feed_delay_seconds: 900, max_quote_age_seconds: 1200 },
          },
        }}
      />,
    );
    expect(screen.getByText(/Kursroute:/)).toHaveTextContent('route-b');
    expect(screen.getByText(/Originalkurszeit Optionsschein:/)).toHaveTextContent('120 Sekunden');
    expect(screen.getByText(/Feed-Verzögerung:/)).toHaveTextContent('900 Sekunden');
  });

  it('computes only explicit assumptions, clears obsolete results and restores inputs per position', async () => {
    vi.mocked(ivApi.preview).mockResolvedValue(result);
    const first = render(<IvRiskPanel view={view} />);
    fillExample();
    fireEvent.click(screen.getByRole('button', { name: 'Annahmen berechnen' }));
    const output = await screen.findByRole('region', { name: 'Hypothetisches IV-Ergebnis' });
    expect(output).toHaveTextContent('−50 EUR'.replace('−', '-'));
    expect(output).toHaveTextContent('kein Verkaufserlös');
    expect(output).toHaveTextContent('keine Änderung von Stops');
    expect(within(output).getAllByText('-0,1 EUR')).toHaveLength(2);
    expect(ivApi.preview).toHaveBeenCalledWith(
      expect.objectContaining({
        scope: 'EUROPEAN',
        ratio: '0.1',
        iv_change_pp: '-5',
        iv_percent: '35',
      }),
      expect.any(AbortSignal),
    );
    fireEvent.change(screen.getByLabelText('IV-Änderung (Prozentpunkte)'), {
      target: { value: '-10' },
    });
    expect(
      screen.queryByRole('region', { name: 'Hypothetisches IV-Ergebnis' }),
    ).not.toBeInTheDocument();
    first.unmount();
    const second = render(<IvRiskPanel view={view} />);
    expect(screen.getByLabelText('IV-Änderung (Prozentpunkte)')).toHaveValue(-10);
    second.unmount();
    render(<IvRiskPanel view={{ ...view, trade_id: 'other' }} />);
    expect(screen.getByLabelText('IV-Änderung (Prozentpunkte)')).toHaveValue(null);
  });

  it('uses a hypothetical price alternative and explains missing local approximation', async () => {
    vi.mocked(ivApi.preview).mockResolvedValue({
      ...result,
      iv_origin: 'HYPOTHETICAL_PRICE_INVERSION',
      local_iv_change: null,
      vega_per_warrant_per_pp: null,
      position_vega_per_pp: null,
      warnings: ['VEGA_TOO_SMALL'],
    });
    render(<IvRiskPanel view={view} />);
    fillExample();
    fireEvent.change(screen.getByLabelText('IV-Grundlage (Annahme)'), {
      target: { value: 'price' },
    });
    fireEvent.change(screen.getByLabelText('Hypothetischer Preis je Schein'), {
      target: { value: '1.5' },
    });
    fireEvent.change(screen.getByLabelText('Richtung'), { target: { value: 'PUT' } });
    fireEvent.change(screen.getByLabelText('Gemeinsame Währung (keine Umrechnung)'), {
      target: { value: 'usd' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Annahmen berechnen' }));
    const output = await screen.findByRole('region', { name: 'Hypothetisches IV-Ergebnis' });
    expect(output).toHaveTextContent('aus hypothetischem Preis berechnet');
    expect(within(output).getAllByText('Nicht berechenbar')).toHaveLength(3);
    expect(output).toHaveTextContent('Vega fehlt oder ist zu klein');
  });

  it('ignores stale responses after an input edit and reports concrete failures', async () => {
    let resolve: (value: IvModelResult) => void = () => {};
    vi.mocked(ivApi.preview).mockImplementation(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    render(<IvRiskPanel view={view} />);
    fillExample();
    fireEvent.click(screen.getByRole('button', { name: 'Annahmen berechnen' }));
    fireEvent.change(screen.getByLabelText('IV-Änderung (Prozentpunkte)'), {
      target: { value: '-10' },
    });
    resolve(result);
    await waitFor(() =>
      expect(
        screen.queryByRole('region', { name: 'Hypothetisches IV-Ergebnis' }),
      ).not.toBeInTheDocument(),
    );
    vi.mocked(ivApi.preview).mockRejectedValue(
      new MarketApiError(422, {
        code: 'HTTP_422',
        message: 'SCENARIO_HORIZON_INVALID',
        details: [],
        timestamp: '',
      }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Annahmen berechnen' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('zwischen heute und der Fälligkeit');
    vi.mocked(ivApi.preview).mockRejectedValue(new Error('offline'));
    fireEvent.click(screen.getByRole('button', { name: 'Annahmen berechnen' }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('kein neues Ergebnis'));
  });

  it('ignores corrupted or unavailable optional session storage', () => {
    sessionStorage.setItem('iv-assumptions-v1:iv-test', '{invalid');
    const first = render(<IvRiskPanel view={view} />);
    expect(screen.getByLabelText('Basiswertkurs (Währungseinheiten)')).toHaveValue(null);
    first.unmount();
    const get = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    const set = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    render(<IvRiskPanel view={view} />);
    fillExample();
    expect(screen.getByLabelText('Basiswertkurs (Währungseinheiten)')).toHaveValue(100);
    get.mockRestore();
    set.mockRestore();
  });
});
