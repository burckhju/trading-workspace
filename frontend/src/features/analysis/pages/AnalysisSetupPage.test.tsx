import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { candidateApiClient } from '../../candidate/services/client';
import type { CandidateLiveWorkflow } from '../../candidate/types/api';
import { marketApiClient } from '../../market/services/client';
import { MarketApiError, MarketTransportError } from '../../market/services/http';
import type { UnderlyingDetailResponse } from '../../market/types/api';
import { analysisApiClient } from '../services/client';
import {
  defaultAnalysisParameters,
  type AnalysisDetail,
  type AnalysisRun,
  type AnalysisRunDetail,
  type RunAnalysisRequest,
} from '../types/api';
import { AnalysisSetupPage } from './AnalysisSetupPage';

vi.mock('../../market/services/client', () => ({
  marketApiClient: { getUnderlying: vi.fn(), searchUnderlyings: vi.fn() },
}));
vi.mock('../../candidate/services/client', () => ({
  candidateApiClient: { liveWorkflow: vi.fn(), evaluateAuto: vi.fn() },
}));
vi.mock('../services/client', () => ({
  analysisApiClient: {
    get: vi.fn(),
    getRun: vi.fn(),
    create: vi.fn(),
    run: vi.fn(),
    runReference: vi.fn(),
    list: vi.fn(),
  },
}));

const timestamp = '2026-10-27T09:00:00Z';
const market = vi.mocked(marketApiClient);
const api = vi.mocked(analysisApiClient);
const candidates = vi.mocked(candidateApiClient);
let details: Record<string, AnalysisDetail>;
let runDetails: Record<string, AnalysisRunDetail>;
let workflow: CandidateLiveWorkflow;

function underlying(id = 'u1'): UnderlyingDetailResponse {
  const listings = ['primary', 'secondary'].map((suffix) => ({
    id: `${id}-${suffix}`,
    underlying_id: id,
    trading_venue_id: 'venue',
    trading_venue_mic: 'XETR',
    trading_venue_name: 'Xetra',
    ticker: id.toUpperCase(),
    currency_code: 'EUR',
    lifecycle_status: 'ACTIVE' as const,
    is_primary: suffix === 'primary',
    version: 1,
    created_at: timestamp,
    updated_at: timestamp,
  }));
  return {
    id,
    type: id === 'etf' ? 'ETF' : 'STOCK',
    name: `Name ${id}`,
    isin: `ISIN-${id}`,
    wkn: null,
    lifecycle_status: 'ACTIVE',
    quality_status: 'VERIFIED',
    version: 1,
    created_at: timestamp,
    updated_at: timestamp,
    primary_listing: listings[0],
    listings,
  };
}
function run(version = 1): AnalysisRun {
  return {
    version,
    status: 'COMPLETED',
    quality_status: 'GOOD',
    model_id: 'EOD_TREND_MOMENTUM',
    model_version: '1.0.1',
    observation_count: 250,
    analysis_time: timestamp,
    input_hash: `hash-${version}`,
  };
}
function analysis(id = 'a1', owner = 'u1'): AnalysisDetail {
  return {
    analysis: {
      id,
      underlying_id: owner,
      listing_id: `${owner}-secondary`,
      market_data_instrument_id: null,
      created_at: timestamp,
      created_by: 'Tester',
    },
    runs: [run()],
  };
}
function source(
  detail: AnalysisDetail,
  version = 1,
  parameters = defaultAnalysisParameters,
): AnalysisRunDetail {
  return {
    analysis: detail.analysis,
    run: detail.runs.find((item) => item.version === version) ?? run(version),
    parameters: { ...parameters },
    metrics: {},
    notes: [],
    data_sources: [],
    criteria: [],
    snapshot: [],
  };
}
function apiError(status = 409, code = 'ANALYSIS_CONFLICT') {
  return new MarketApiError(status, {
    code,
    message: 'Konkreter Konflikt',
    details: [],
    timestamp,
  });
}
function Probe() {
  const location = useLocation();
  return (
    <output data-testid="location">
      {location.pathname}
      {location.search}
    </output>
  );
}
function mount(entries = ['/market-analyses/setup?analysis_id=a1'], index = entries.length - 1) {
  const router = createMemoryRouter(
    [
      {
        path: '/market-analyses/setup',
        element: (
          <>
            <AnalysisSetupPage />
            <Probe />
          </>
        ),
      },
      {
        path: '/market-analyses/:analysisId',
        element: (
          <>
            <h1>Analyse lesen</h1>
            <Probe />
          </>
        ),
      },
      {
        path: '/market-analyses',
        element: (
          <>
            <h1>Übersicht</h1>
            <Probe />
          </>
        ),
      },
      {
        path: '/candidates',
        element: (
          <>
            <h1>Kandidaten</h1>
            <Probe />
          </>
        ),
      },
    ],
    { initialEntries: entries, initialIndex: index },
  );
  render(<RouterProvider router={router} />);
  return router;
}
async function ready() {
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Lesestand aktualisieren' })).toBeEnabled(),
  );
}
function confirmAndSubmit() {
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(
    screen.getByRole('button', {
      name: /Bestätigte Analyse anlegen|Bestätigten Analyselauf ausführen/,
    }),
  );
}
function candidateUrl(owner = 'etf') {
  return `/market-analyses/setup?${new URLSearchParams({ action: 'RUN_MARKET_ANALYSIS', candidate_id: 'candidate', resource_id: `${owner}-secondary`, underlying_id: owner, listing_id: `${owner}-secondary`, action_params: JSON.stringify({ underlying_id: owner, listing_id: `${owner}-secondary` }), step_code: 'SECTOR_ANALYSIS' })}`;
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  vi.resetAllMocks();
  details = { a1: analysis(), a2: analysis('a2', 'u2') };
  runDetails = { 'a1:1': source(details.a1), 'a2:1': source(details.a2) };
  workflow = {
    candidate_id: 'candidate',
    underlying_id: 'candidate-owner',
    as_of: '2026-10-27',
    ready: false,
    can_evaluate: false,
    next_action: 'ASSIGN_SECTOR',
    steps: [
      {
        code: 'SECTOR_ANALYSIS',
        label: 'Sektoranalyse',
        status: 'BLOCKED',
        detail: 'Analyse fehlt',
        action: 'RUN_MARKET_ANALYSIS',
        resource_id: 'etf-secondary',
        action_params: { underlying_id: 'etf', listing_id: 'etf-secondary' },
      },
    ],
  };
  market.getUnderlying.mockImplementation((id) => Promise.resolve(underlying(id)));
  market.searchUnderlyings.mockResolvedValue({
    items: [underlying(), underlying('u2')],
    total: 2,
    offset: 0,
    limit: 20,
  });
  candidates.liveWorkflow.mockImplementation(() => Promise.resolve(structuredClone(workflow)));
  api.get.mockImplementation((id) =>
    details[id]
      ? Promise.resolve(structuredClone(details[id]))
      : Promise.reject(new Error('Analyse fehlt')),
  );
  api.getRun.mockImplementation((id, version) =>
    runDetails[`${id}:${version}`]
      ? Promise.resolve(structuredClone(runDetails[`${id}:${version}`]))
      : Promise.reject(new Error('Lauf fehlt')),
  );
  api.list.mockImplementation(() =>
    Promise.resolve(Object.values(details).map((value) => value.analysis)),
  );
  api.create.mockImplementation((owner, listing) => {
    const created = {
      id: 'created',
      underlying_id: owner,
      listing_id: listing,
      market_data_instrument_id: null,
      created_at: timestamp,
      created_by: 'Tester',
    };
    details.created = { analysis: created, runs: [] };
    return Promise.resolve(created);
  });
  const execute = (id: string, request: RunAnalysisRequest) => {
    const next = run(Math.max(0, ...details[id].runs.map((item) => item.version)) + 1);
    details[id].runs.push(next);
    runDetails[`${id}:${next.version}`] = source(details[id], next.version, request.parameters);
    return Promise.resolve(next);
  };
  api.run.mockImplementation(execute);
  api.runReference.mockImplementation(execute);
});

describe('canonical analysis preparation', () => {
  it('opens without writes, binds explicit nonprimary identity and separates creation from the confirmed run', async () => {
    const router = mount(['/market-analyses/setup?underlying_id=u1&listing_id=u1-secondary']);
    await ready();
    expect(screen.getByText(/nichtprimäre Notierung/)).toBeVisible();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(api.create).not.toHaveBeenCalled();
    expect(api.run).not.toHaveBeenCalled();
    confirmAndSubmit();
    await screen.findByText(/Analyse angelegt: created/);
    await ready();
    expect(router.state.location.search).toContain('analysis_id=created');
    expect(api.create).toHaveBeenCalledExactlyOnceWith('u1', 'u1-secondary');
    expect(api.run).not.toHaveBeenCalled();
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    expect(screen.getByLabelText('Von')).toHaveValue(
      new Date(Date.now() - 365 * 86400000).toISOString().slice(0, 10),
    );
    confirmAndSubmit();
    await screen.findByRole('heading', { name: 'Schreibauftrag für Version 1 abgeschlossen' });
    expect(api.run).toHaveBeenCalledExactlyOnceWith(
      'created',
      expect.objectContaining({ model_version: '1.0.1', parameters: defaultAnalysisParameters }),
    );
    expect(screen.getByRole('link', { name: 'Genau diese Analyseversion öffnen' })).toHaveAttribute(
      'href',
      '/market-analyses/created?version=1',
    );
    expect(api.create).toHaveBeenCalledTimes(1);
  });

  it('offers only missing targets from stored search and preserves the selected secondary listing', async () => {
    const user = userEvent.setup();
    mount(['/market-analyses/setup']);
    await ready();
    await user.selectOptions(screen.getByRole('combobox', { name: 'Basiswert / ETF' }), 'u2');
    await ready();
    await user.selectOptions(
      screen.getByRole('combobox', { name: 'Bestehende Notierung' }),
      'u2-secondary',
    );
    await ready();
    confirmAndSubmit();
    await screen.findByText(/Analyse angelegt/);
    expect(api.create).toHaveBeenCalledExactlyOnceWith('u2', 'u2-secondary');
    expect(market.searchUnderlyings).toHaveBeenCalledWith(
      { query: undefined, lifecycleStatus: 'ACTIVE', offset: 0, limit: 20 },
      expect.any(AbortSignal),
    );
  });

  it('retains the acknowledged analysis ID after explicit run failure and never creates a second analysis', async () => {
    mount(['/market-analyses/setup?underlying_id=u1&listing_id=u1-secondary']);
    await ready();
    confirmAndSubmit();
    await screen.findByText(/Analyse angelegt/);
    await ready();
    api.run.mockRejectedValueOnce(apiError(422, 'ANALYSIS_DATA_UNAVAILABLE'));
    fireEvent.change(screen.getByLabelText('Von'), { target: { value: '2026-01-01' } });
    confirmAndSubmit();
    await screen.findByText(/ANALYSIS_DATA_UNAVAILABLE: Konkreter Konflikt/);
    expect(screen.getByLabelText('Von')).toHaveValue('2026-01-01');
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    expect(
      screen.queryByRole('button', { name: 'Bestätigte Analyse anlegen' }),
    ).not.toBeInTheDocument();
    confirmAndSubmit();
    await screen.findByRole('heading', { name: 'Schreibauftrag für Version 1 abgeschlossen' });
    expect(api.create).toHaveBeenCalledTimes(1);
    expect(api.run).toHaveBeenCalledTimes(2);
    expect(api.run.mock.calls.every(([id]) => id === 'created')).toBe(true);
  });

  it('keeps creation success and exact URL if its readback fails; retry only reads', async () => {
    mount(['/market-analyses/setup?underlying_id=u1&listing_id=u1-secondary']);
    await ready();
    api.get.mockImplementation((id) =>
      id === 'created' ? Promise.reject(new Error('read failed')) : Promise.resolve(details[id]),
    );
    confirmAndSubmit();
    await screen.findByText(/Der Schreibauftrag ist abgeschlossen; das Nachlesen ist gestört/);
    expect(screen.getByTestId('location')).toHaveTextContent('analysis_id=created');
    expect(
      screen.queryByRole('button', { name: 'Bestätigte Analyse anlegen' }),
    ).not.toBeInTheDocument();
    api.get.mockImplementation((id) => Promise.resolve(details[id]));
    fireEvent.click(screen.getByRole('button', { name: 'Nur Lesestand erneut laden' }));
    await ready();
    expect(screen.getByRole('checkbox')).toBeEnabled();
    expect(api.create).toHaveBeenCalledTimes(1);
    expect(api.run).not.toHaveBeenCalled();
  });

  it('binds a non-next candidate step to the actual ETF owner with explicit 400-day dates', async () => {
    mount([candidateUrl()]);
    await ready();
    expect(screen.getByText('Name etf')).toBeVisible();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    confirmAndSubmit();
    await screen.findByText(/Analyse angelegt/);
    await ready();
    expect(screen.getByText(/Zeitraumsvorschlag: letzte 400 Tage/)).toBeVisible();
    expect(screen.getByLabelText('Von')).toHaveValue(
      new Date(Date.now() - 400 * 86400000).toISOString().slice(0, 10),
    );
    expect(api.create).toHaveBeenCalledExactlyOnceWith('etf', 'etf-secondary');
    confirmAndSubmit();
    await screen.findByRole('heading', { name: 'Schreibauftrag für Version 1 abgeschlossen' });
    expect(candidates.liveWorkflow.mock.calls.length).toBeGreaterThanOrEqual(4);
    expect(candidates.evaluateAuto).not.toHaveBeenCalled();
    expect(screen.getByRole('link', { name: '← Zurück zum konkreten Kandidaten' })).toHaveAttribute(
      'href',
      '/candidates?candidate=candidate',
    );
  });

  it('rechecks the concrete candidate step immediately before a write and preserves the dates when it is stale', async () => {
    details.a1 = analysis('a1', 'etf');
    mount([`${candidateUrl()}&analysis_id=a1`]);
    await ready();
    fireEvent.change(screen.getByLabelText('Von'), { target: { value: '2026-02-01' } });
    workflow.steps[0].status = 'COMPLETE';
    confirmAndSubmit();
    await screen.findByText(/Dieser konkrete Analyse-Schritt ist nicht mehr blockiert/);
    expect(screen.getByLabelText('Von')).toHaveValue('2026-02-01');
    expect(api.run).not.toHaveBeenCalled();
  });

  it('runs a stored listing-free reference through its owner API without manufacturing a listing', async () => {
    details.ref = {
      ...analysis('ref'),
      analysis: {
        id: 'ref',
        underlying_id: null,
        listing_id: null,
        market_data_instrument_id: 'instrument',
        created_at: timestamp,
        created_by: 'Tester',
      },
    };
    mount(['/market-analyses/setup?analysis_id=ref']);
    await ready();
    expect(
      screen.getByText(/Direkte Marktreferenzanalyse ohne Basiswert oder Listing/),
    ).toBeVisible();
    expect(market.getUnderlying).not.toHaveBeenCalled();
    confirmAndSubmit();
    await screen.findByRole('heading', { name: 'Schreibauftrag für Version 2 abgeschlossen' });
    expect(api.runReference).toHaveBeenCalledExactlyOnceWith(
      'ref',
      expect.objectContaining({ model_version: '1.0.1', parameters: defaultAnalysisParameters }),
    );
    expect(api.run).not.toHaveBeenCalled();
    expect(api.create).not.toHaveBeenCalled();
  });

  it('prepares all historical parameters only on request, preserving new dates and exact candidate evaluation return', async () => {
    const historic = {
      ...defaultAnalysisParameters,
      price_field: 'CLOSE' as const,
      short_window: 10,
      medium_window: 30,
      long_window: 100,
      momentum_windows: [15, 35],
      volatility_window: 15,
      range_window: 26,
      minimum_required_observations: 100,
      maximum_data_age_days: 3,
      annualization_factor: '250.50',
      rounding_scale: 4,
    };
    runDetails['a1:1'] = source(details.a1, 1, historic);
    mount([
      '/market-analyses/setup?analysis_id=a1&source_version=1&candidate_id=candidate&evaluation_id=evaluation',
    ]);
    await ready();
    expect(screen.getByLabelText('Kurzfristiges Fenster')).toHaveValue(20);
    expect(screen.getByLabelText('Von')).toHaveValue('');
    expect(screen.getByLabelText('Bis')).toHaveValue('');
    expect(candidates.liveWorkflow).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Parameter aus Version 1 vorbereiten' }));
    expect(screen.getByLabelText('Kurzfristiges Fenster')).toHaveValue(10);
    expect(screen.getByLabelText('Mittelfristiges Fenster')).toHaveValue(30);
    expect(screen.getByLabelText('Momentumfenster (aufsteigend, mit Kommas)')).toHaveValue(
      '15, 35',
    );
    fireEvent.change(screen.getByLabelText('Von'), { target: { value: '2026-01-01' } });
    fireEvent.change(screen.getByLabelText('Bis'), { target: { value: '2026-10-01' } });
    confirmAndSubmit();
    await screen.findByRole('heading', { name: 'Schreibauftrag für Version 2 abgeschlossen' });
    expect(api.run).toHaveBeenCalledExactlyOnceWith('a1', {
      start_date: '2026-01-01',
      end_date: '2026-10-01',
      model_version: '1.0.1',
      parameters: historic,
    });
    expect(screen.getByRole('link', { name: '← Zurück zum konkreten Kandidaten' })).toHaveAttribute(
      'href',
      '/candidates?candidate=candidate&evaluation=evaluation',
    );
  });

  it('requires explicit discard before a historical proposal replaces a dirty parameter draft', async () => {
    mount(['/market-analyses/setup?analysis_id=a1&source_version=1']);
    await ready();
    fireEvent.change(screen.getByLabelText('Kurzfristiges Fenster'), { target: { value: '15' } });
    fireEvent.click(screen.getByRole('button', { name: 'Parameter aus Version 1 vorbereiten' }));
    expect(screen.getByRole('alertdialog')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    expect(screen.getByLabelText('Kurzfristiges Fenster')).toHaveValue(15);
    fireEvent.click(screen.getByRole('button', { name: 'Parameter aus Version 1 vorbereiten' }));
    fireEvent.click(screen.getByRole('button', { name: 'Entwurf verwerfen und fortfahren' }));
    expect(screen.getByLabelText('Kurzfristiges Fenster')).toHaveValue(20);
    expect(api.run).not.toHaveBeenCalled();
  });

  it('blocks inconsistent object IDs before enabling a write', async () => {
    mount(['/market-analyses/setup?analysis_id=a1&listing_id=u2-secondary']);
    await screen.findByText(/Widersprüchliche Analyse-Listingkennung/);
    expect(
      screen.getByRole('button', { name: 'Bestätigten Analyselauf ausführen' }),
    ).toBeDisabled();
    expect(api.run).not.toHaveBeenCalled();
  });

  it('retains invalid raw parameters and provides a useful validation message', async () => {
    mount();
    await ready();
    fireEvent.change(screen.getByLabelText('Momentumfenster (aufsteigend, mit Kommas)'), {
      target: { value: '60, 20' },
    });
    expect(
      screen.getByText(/Momentumfenster müssen positive, eindeutig aufsteigende/),
    ).toBeVisible();
    expect(screen.getByLabelText('Momentumfenster (aufsteigend, mit Kommas)')).toHaveValue(
      '60, 20',
    );
    expect(screen.getByRole('checkbox')).toBeDisabled();
    expect(api.run).not.toHaveBeenCalled();
  });
});

describe('analysis write certainty and draft navigation', () => {
  it('keeps completed write separate from failed exact-run readback and retries only GET', async () => {
    mount();
    await ready();
    api.getRun.mockRejectedValueOnce(new Error('run readback unavailable'));
    confirmAndSubmit();
    await screen.findByText(/Der Schreibauftrag ist abgeschlossen; das Nachlesen ist gestört/);
    expect(
      screen.getByRole('heading', { name: 'Schreibauftrag für Version 2 abgeschlossen' }),
    ).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Nur Lesestand erneut laden' }));
    await screen.findByText(/Version 2 mit Modell .* wurde genau nachgelesen/);
    expect(api.run).toHaveBeenCalledTimes(1);
  });

  it('treats an unknown run transport as uncertain even when the matching version appears in GET', async () => {
    mount();
    await ready();
    api.run.mockImplementationOnce((id) => {
      details[id].runs.push(run(2));
      return Promise.reject(new MarketTransportError('request outcome unknown'));
    });
    confirmAndSubmit();
    await screen.findByText(/ein passender Wert beweist nicht den Abschluss dieses Requests/);
    await ready();
    fireEvent.click(screen.getByRole('button', { name: 'Nur Lesestand erneut laden' }));
    await ready();
    expect(
      screen.getByRole('button', { name: 'Bestätigten Analyselauf ausführen' }),
    ).toBeDisabled();
    expect(
      screen.queryByRole('heading', { name: /Schreibauftrag für Version/ }),
    ).not.toBeInTheDocument();
    expect(api.run).toHaveBeenCalledTimes(1);
  });

  it('blocks unknown creation and only reads possible same-context analyses without adopting one', async () => {
    mount(['/market-analyses/setup?underlying_id=u1&listing_id=u1-secondary']);
    await ready();
    api.create.mockRejectedValueOnce(new MarketTransportError('unknown creation'));
    confirmAndSubmit();
    await screen.findByRole('link', { name: 'Analyse a1 lesend öffnen' });
    expect(screen.getByRole('button', { name: 'Bestätigte Analyse anlegen' })).toBeDisabled();
    expect(screen.getByTestId('location')).not.toHaveTextContent('analysis_id=a1');
    expect(api.create).toHaveBeenCalledTimes(1);
    expect(api.run).not.toHaveBeenCalled();
  });

  it('treats a malformed successful run response as unknown instead of claiming a different model', async () => {
    mount();
    await ready();
    api.run.mockResolvedValueOnce({ ...run(2), model_version: '1.0.0' });
    confirmAndSubmit();
    await screen.findByText(/Die Serverantwort belegt diesen Analyseauftrag nicht eindeutig/);
    expect(
      screen.getByRole('button', { name: 'Bestätigten Analyselauf ausführen' }),
    ).toBeDisabled();
    expect(api.run).toHaveBeenCalledTimes(1);
  });

  it('detects newer runs before writing, preserves the draft and requires review then a fresh confirmation', async () => {
    mount();
    await ready();
    fireEvent.change(screen.getByLabelText('Kurzfristiges Fenster'), { target: { value: '15' } });
    details.a1.runs.push(run(2));
    confirmAndSubmit();
    const review = await screen.findByRole('button', {
      name: 'Aktuellen Stand prüfen und Entwurf beibehalten',
    });
    expect(screen.getByLabelText('Kurzfristiges Fenster')).toHaveValue(15);
    expect(api.run).not.toHaveBeenCalled();
    fireEvent.click(review);
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    confirmAndSubmit();
    await screen.findByRole('heading', { name: 'Schreibauftrag für Version 3 abgeschlossen' });
    expect(api.run).toHaveBeenCalledTimes(1);
  });

  it('preserves a same-context draft across refresh and clears an earlier confirmation', async () => {
    mount();
    await ready();
    const field = screen.getByLabelText('Kurzfristiges Fenster');
    fireEvent.change(field, { target: { value: '15' } });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Lesestand aktualisieren' }));
    await ready();
    expect(screen.getByLabelText('Kurzfristiges Fenster')).toBe(field);
    expect(field).toHaveValue(15);
    expect(screen.getByRole('checkbox')).not.toBeChecked();
  });

  it('protects query and browser POP changes, preserves the draft on stay and discards only explicitly', async () => {
    const router = mount([
      '/market-analyses/setup?analysis_id=a2',
      '/market-analyses/setup?analysis_id=a1',
    ]);
    await ready();
    fireEvent.change(screen.getByLabelText('Kurzfristiges Fenster'), { target: { value: '15' } });
    await act(async () => {
      await router.navigate(-1);
    });
    expect(screen.getByRole('alertdialog')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Hier bleiben' })).toHaveFocus();
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    expect(screen.getByLabelText('Kurzfristiges Fenster')).toHaveValue(15);
    await act(async () => {
      await router.navigate('/market-analyses/setup?analysis_id=a2');
    });
    fireEvent.click(screen.getByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
    await screen.findByText('Name u2');
    await ready();
    expect(screen.getByLabelText('Kurzfristiges Fenster')).toHaveValue(20);
    expect(api.run).not.toHaveBeenCalled();
  });

  it('ignores delayed old A reads after A→B→A even when the original identity matches again', async () => {
    const oldA = deferred<AnalysisDetail>();
    api.get.mockImplementationOnce(() => oldA.promise);
    const router = mount();
    await act(async () => {
      await router.navigate('/market-analyses/setup?analysis_id=a2');
    });
    await screen.findByText('Name u2');
    await act(async () => {
      await router.navigate('/market-analyses/setup?analysis_id=a1');
    });
    await ready();
    fireEvent.change(screen.getByLabelText('Kurzfristiges Fenster'), { target: { value: '17' } });
    await act(async () => {
      oldA.resolve({ ...analysis(), runs: [run(99)] });
      await oldA.promise;
    });
    expect(screen.getByLabelText('Kurzfristiges Fenster')).toHaveValue(17);
    expect(screen.getByText(/Vorhandene Versionen: 1/)).toBeVisible();
    expect(api.run).not.toHaveBeenCalled();
  });

  it('locks synchronous double submit and prevents route discard while the write is pending', async () => {
    const pending = deferred<AnalysisRun>();
    api.run.mockReturnValueOnce(pending.promise);
    const router = mount();
    await ready();
    fireEvent.click(screen.getByRole('checkbox'));
    const form = screen.getByRole('form');
    fireEvent.submit(form);
    fireEvent.submit(form);
    await waitFor(() => expect(api.run).toHaveBeenCalledTimes(1));
    await act(async () => {
      await router.navigate('/market-analyses');
    });
    expect(screen.getByRole('heading', { name: 'Speicherung läuft' })).toBeVisible();
    expect(
      screen.queryByRole('button', { name: 'Eingaben verwerfen und wechseln' }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText('Kurzfristiges Fenster')).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    details.a1.runs.push(run(2));
    runDetails['a1:2'] = source(details.a1, 2);
    await act(async () => {
      pending.resolve(run(2));
      await pending.promise;
    });
    await screen.findByRole('heading', { name: 'Schreibauftrag für Version 2 abgeschlossen' });
    expect(api.run).toHaveBeenCalledTimes(1);
  });
});
