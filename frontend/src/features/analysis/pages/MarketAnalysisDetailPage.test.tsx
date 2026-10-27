import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MarketApiError, MarketTransportError } from '../../market/services/http';
import { analysisApiClient } from '../services/client';
import type { AnalysisDetail, AnalysisEvent, AnalysisRun, AnalysisRunDetail } from '../types/api';
import { MarketAnalysisDetailPage } from './MarketAnalysisDetailPage';

vi.mock('../services/client', () => ({
  analysisApiClient: {
    get: vi.fn(),
    run: vi.fn(),
    runReference: vi.fn(),
    getRun: vi.fn(),
    getSnapshot: vi.fn(),
    events: vi.fn(),
    verify: vi.fn(),
    retry: vi.fn(),
    supersede: vi.fn(),
  },
}));

const analysisId = '33333333-3333-4333-8333-333333333333';
const otherId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const analysis = {
  id: analysisId,
  underlying_id: '11111111-1111-4111-8111-111111111111',
  listing_id: '22222222-2222-4222-8222-222222222222',
  created_at: '2026-08-06T10:00:00Z',
  created_by: 'Tester',
};
const run1: AnalysisRun = {
  version: 1,
  status: 'NOT_EVALUABLE',
  quality_status: 'INSUFFICIENT',
  model_id: 'EOD_TREND_MOMENTUM',
  model_version: '1.0.0',
  observation_count: 20,
  analysis_time: '2026-08-06T11:00:00Z',
  input_hash: 'abc123',
};
const run2: AnalysisRun = {
  ...run1,
  version: 2,
  status: 'COMPLETED',
  quality_status: 'GOOD',
  observation_count: 250,
  analysis_time: '2026-08-06T12:00:00Z',
  input_hash: 'def456',
};
const retryRun: AnalysisRun = { ...run1, version: 3, analysis_time: '2026-08-06T13:00:00Z' };
const superseded: AnalysisEvent = {
  id: '44444444-4444-4444-8444-444444444444',
  version: 1,
  event_type: 'SUPERSEDED',
  from_status: 'NOT_EVALUABLE',
  to_status: 'SUPERSEDED',
  source_version: 1,
  replacement_version: 2,
  reason: 'Retry erfolgreich',
  correlation_id: null,
  occurred_at: '2026-08-06T12:01:00Z',
};
const verification = {
  verified: true,
  model_available: true,
  input_hash_matches: true,
  metrics_match: true,
  criteria_match: true,
  quality_status_match: true,
  notes_match: true,
};
let detail: AnalysisDetail;
let events: AnalysisEvent[];

function runDetail(version: number, id = analysisId): AnalysisRunDetail {
  return {
    analysis: { ...detail.analysis, id },
    run: detail.runs.find((run) => run.version === version)!,
    parameters: { short_window: 20, long_window: 200 },
    metrics: { sma_short: version === 1 ? '101.25' : '202.50', unavailable: null },
    notes: version === 1 ? ['Zu wenig Beobachtungen'] : [],
    data_sources: ['EODHD'],
    criteria: [
      {
        code: `TREND_V${version}`,
        classification: 'POSITIVE',
        value: '1',
        explanation: 'Stored source result.',
      },
    ],
    snapshot: [],
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  detail = { analysis: { ...analysis }, runs: [{ ...run1 }, { ...run2 }] };
  events = [superseded];
  vi.mocked(analysisApiClient.get).mockImplementation((id) =>
    Promise.resolve({
      ...detail,
      analysis: { ...detail.analysis, id },
    }),
  );
  vi.mocked(analysisApiClient.events).mockImplementation(() => Promise.resolve([...events]));
  vi.mocked(analysisApiClient.getRun).mockImplementation((id, version) =>
    Promise.resolve(runDetail(version, id)),
  );
  vi.mocked(analysisApiClient.getSnapshot).mockImplementation((_id, _version, offset, limit) =>
    Promise.resolve({
      items: [
        {
          trading_date: '2026-08-05',
          open: '100',
          high: '103',
          low: '99',
          close: '102',
          adjusted_close: '102',
          volume: '1000',
          currency: 'EUR',
          provider: 'EODHD',
          provider_symbol: 'SIE.XETRA',
          quality_status: 'GOOD',
          warnings: [],
        },
      ],
      total: 1,
      offset,
      limit,
    }),
  );
  vi.mocked(analysisApiClient.verify).mockResolvedValue(verification);
  vi.mocked(analysisApiClient.retry).mockImplementation((_id, version, reason) => {
    detail = { ...detail, runs: [...detail.runs, retryRun] };
    events = [
      ...events,
      {
        ...superseded,
        source_version: version,
        replacement_version: 3,
        reason: reason || 'Replaced by retry version 3',
      },
    ];
    return Promise.resolve(retryRun);
  });
  vi.mocked(analysisApiClient.supersede).mockImplementation((_id, version, replacement, reason) => {
    const event = {
      ...superseded,
      version,
      source_version: version,
      replacement_version: replacement,
      reason: reason || null,
    };
    events = [...events, event];
    return Promise.resolve(event);
  });
});

function show(search = '?version=2', entries?: string[], initialIndex?: number) {
  const router = createMemoryRouter(
    [
      { path: '/market-analyses/setup', element: <p>Gemeinsamer Analyseeditor</p> },
      { path: '/market-analyses/:analysisId', element: <MarketAnalysisDetailPage /> },
      { path: '/market-analyses', element: <p>Analyseübersicht</p> },
      { path: '/candidates', element: <p>Kandidatenrückkehr</p> },
    ],
    { initialEntries: entries ?? [`/market-analyses/${analysisId}${search}`], initialIndex },
  );
  render(<RouterProvider router={router} />);
  return router;
}
async function loaded(version = 2) {
  await screen.findByRole('heading', { name: `Ergebnis · Version ${version}` });
  await waitFor(() =>
    expect(screen.queryByText('Lesestand wird aktualisiert …')).not.toBeInTheDocument(),
  );
}
async function openRetry() {
  await loaded(1);
  await userEvent.click(screen.getByRole('button', { name: 'Retry aus Snapshot' }));
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
function noWrites() {
  for (const method of ['run', 'runReference', 'retry', 'supersede', 'verify'] as const)
    expect(analysisApiClient[method]).not.toHaveBeenCalled();
}

describe('exact analysis detail version and one canonical editor', () => {
  it('pins only an unqualified first visit to the numeric latest version using replace', async () => {
    detail.runs.reverse();
    const router = show('');
    await loaded();
    expect(router.state.location.search).toBe('?version=2');
    expect(router.state.historyAction).toBe('REPLACE');
    expect(screen.getByText('TREND_V2')).toBeInTheDocument();
    expect(screen.queryByText('TREND_V1')).not.toBeInTheDocument();
    expect(screen.getByText('Grund: Retry erfolgreich')).toBeInTheDocument();
    expect(screen.queryByRole('form')).not.toBeInTheDocument();
    noWrites();
  });

  it('opens the pinned historical body and carries only internal context into the shared editor', async () => {
    const user = userEvent.setup();
    const router = show(
      '?version=1&candidate_id=c1&evaluation_id=e7&overview_context=status%3DCOMPLETED&return_to=https://evil.test',
    );
    await loaded(1);
    expect(screen.getByText('101.25')).toBeInTheDocument();
    expect(screen.queryByText('202.50')).not.toBeInTheDocument();
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Von')).not.toBeInTheDocument();
    const setup = screen.getByRole('link', {
      name: 'Neue Analyseversion aus Version 1 vorbereiten',
    });
    const url = new URL(setup.getAttribute('href')!, 'http://localhost');
    expect(url.pathname).toBe('/market-analyses/setup');
    expect(url.searchParams.get('analysis_id')).toBe(analysisId);
    expect(url.searchParams.get('source_version')).toBe('1');
    expect(url.searchParams.get('listing_id')).toBe(analysis.listing_id);
    expect(url.searchParams.get('candidate_id')).toBe('c1');
    expect(url.searchParams.get('evaluation_id')).toBe('e7');
    expect(url.searchParams.has('return_to')).toBe(false);
    expect(screen.getByRole('link', { name: 'Zurück zum Kandidaten' })).toHaveAttribute(
      'href',
      '/candidates?candidate=c1&evaluation=e7',
    );
    await user.click(setup);
    expect(router.state.location.pathname).toBe('/market-analyses/setup');
    noWrites();
  });

  it('returns to the filtered overview and never to its own detail URL', async () => {
    show(
      '?version=2&overview_context=status%3DCOMPLETED%26offset%3D50%26external%3Dhttps%253A%252F%252Fevil.test',
    );
    await loaded();
    expect(screen.getByRole('link', { name: 'Zurück zu Marktanalysen' })).toHaveAttribute(
      'href',
      '/market-analyses?offset=50&status=COMPLETED',
    );
  });

  it.each(['', '0', '-1', '1.5', '01', '2x', '9007199254740992', '1&version=2'])(
    'blocks the explicit invalid version %j without falling back',
    async (value) => {
      const router = show(`?version=${value}`);
      expect(await screen.findByRole('alert')).toHaveTextContent('ungültig');
      expect(router.state.location.search).toBe(`?version=${value}`);
      expect(analysisApiClient.get).not.toHaveBeenCalled();
      noWrites();
    },
  );

  it.each(['analysis_id=foreign', 'source_version=2'])(
    'blocks contradictory detail identities %s',
    async (query) => {
      show(`?version=1&${query}`);
      expect(await screen.findByRole('alert')).toBeInTheDocument();
      expect(analysisApiClient.get).not.toHaveBeenCalled();
      noWrites();
    },
  );

  it('preserves a safe candidate return even when the selected version is invalid', async () => {
    show('?version=&candidate_id=c1&evaluation_id=e2&return_to=https://evil.test');
    expect(await screen.findByRole('alert')).toHaveTextContent('ungültig');
    expect(screen.getByRole('link', { name: 'Zurück zum Kandidaten' })).toHaveAttribute(
      'href',
      '/candidates?candidate=c1&evaluation=e2',
    );
    noWrites();
  });

  it('does not substitute latest when the explicit historical version is absent', async () => {
    show('?version=99');
    expect(await screen.findByRole('alert')).toHaveTextContent('Version 99 ist nicht vorhanden');
    expect(screen.queryByText('202.50')).not.toBeInTheDocument();
    expect(analysisApiClient.getRun).not.toHaveBeenCalled();
    noWrites();
  });

  it.each(['analysis', 'version', 'listing'])(
    'rejects a foreign %s in the scoped run response',
    async (mismatch) => {
      vi.mocked(analysisApiClient.getRun).mockImplementation((_id, version) => {
        const result = runDetail(version);
        if (mismatch === 'analysis') result.analysis.id = otherId;
        if (mismatch === 'version') result.run = run1;
        if (mismatch === 'listing') result.analysis.listing_id = 'foreign';
        return Promise.resolve(result);
      });
      show();
      expect(await screen.findByRole('alert')).toHaveTextContent('Ergebnisversion passt nicht');
      expect(screen.queryByText('202.50')).not.toBeInTheDocument();
      noWrites();
    },
  );

  it('keeps a listing-free direct reference and its historical version without fabricating a listing', async () => {
    detail.analysis = {
      ...analysis,
      underlying_id: null,
      listing_id: null,
      market_data_instrument_id: 'native-index',
    };
    show('?version=1');
    await loaded(1);
    expect(screen.getByText('Marktreferenz · Dateninstrument native-index')).toBeInTheDocument();
    const url = new URL(
      screen
        .getByRole('link', { name: 'Neue Analyseversion aus Version 1 vorbereiten' })
        .getAttribute('href')!,
      'http://localhost',
    );
    expect(url.searchParams.get('market_data_instrument_id')).toBe('native-index');
    expect(url.searchParams.get('source_version')).toBe('1');
    expect(url.searchParams.has('listing_id')).toBe(false);
    expect(url.searchParams.has('underlying_id')).toBe(false);
    noWrites();
  });

  it('offers preparation for an empty analysis without inferring a historical version', async () => {
    detail.runs = [];
    const router = show('');
    expect(
      await screen.findByText('Für diese Analyse wurde noch keine Version ausgeführt.'),
    ).toBeInTheDocument();
    expect(router.state.location.search).toBe('');
    expect(
      screen.getByRole('link', { name: 'Erste Analyseversion vorbereiten' }),
    ).toBeInTheDocument();
    noWrites();
  });

  it('hides the previous body immediately and stays blocked when the new version read fails', async () => {
    const user = userEvent.setup();
    show();
    await loaded();
    vi.mocked(analysisApiClient.getRun).mockRejectedValue(new Error('Historical read unavailable'));
    await user.selectOptions(screen.getByLabelText('Analyseversion'), '1');
    expect(await screen.findByRole('alert')).toHaveTextContent('Historical read unavailable');
    expect(screen.queryByText('202.50')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Reproduzierbarkeit prüfen' }),
    ).not.toBeInTheDocument();
    noWrites();
  });

  it('discards delayed A responses after A→B→A using abort and a new generation', async () => {
    const firstA = deferred<AnalysisRunDetail>();
    vi.mocked(analysisApiClient.getRun).mockImplementationOnce(() => firstA.promise);
    const router = show('?version=1');
    await waitFor(() => expect(analysisApiClient.getRun).toHaveBeenCalledTimes(1));
    const oldSignal = vi.mocked(analysisApiClient.getRun).mock.calls[0][2];
    await act(() => router.navigate(`/market-analyses/${otherId}?version=2`));
    await loaded(2);
    await act(() => router.navigate(`/market-analyses/${analysisId}?version=1`));
    await loaded(1);
    await act(async () => {
      firstA.resolve({ ...runDetail(1), metrics: { poisoned: 'STALE_A' } });
      await firstA.promise;
    });
    expect(oldSignal?.aborted).toBe(true);
    expect(screen.queryByText('STALE_A')).not.toBeInTheDocument();
    expect(screen.getByText('101.25')).toBeInTheDocument();
    noWrites();
  });
});

describe('explicit guarded lifecycle operations', () => {
  it('verifies exactly the selected historical model without a new run', async () => {
    const user = userEvent.setup();
    show('?version=1');
    await loaded(1);
    await user.click(screen.getByRole('button', { name: 'Reproduzierbarkeit prüfen' }));
    expect(await screen.findByText('Reproduktion bestätigt')).toBeInTheDocument();
    expect(analysisApiClient.verify).toHaveBeenCalledExactlyOnceWith(analysisId, 1);
    expect(analysisApiClient.run).not.toHaveBeenCalled();
    expect(analysisApiClient.runReference).not.toHaveBeenCalled();
    expect(screen.getByText('EOD_TREND_MOMENTUM / 1.0.0')).toBeInTheDocument();
  });

  it('does not offer Retry for an already superseded source', async () => {
    show('?version=1');
    await loaded(1);
    expect(screen.queryByRole('button', { name: 'Retry aus Snapshot' })).not.toBeInTheDocument();
    expect(
      screen.getByText('Diese historische Version wurde bereits ersetzt.'),
    ).toBeInTheDocument();
  });

  it('retries only after explicit confirmation using the exact stored source and reason', async () => {
    events = [];
    const user = userEvent.setup();
    const router = show('?version=1');
    await openRetry();
    expect(screen.getAllByRole('form')).toHaveLength(1);
    expect(screen.getByRole('heading', { name: 'Retry aus Snapshot · Version 1' })).toHaveFocus();
    await user.type(screen.getByLabelText('Begründung'), 'Historischen Snapshot erneut berechnen');
    expect(analysisApiClient.retry).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Retry aus Snapshot bestätigen' }));
    expect(await screen.findByText(/Retry als Version 3 bestätigt/)).toBeInTheDocument();
    expect(analysisApiClient.retry).toHaveBeenCalledExactlyOnceWith(
      analysisId,
      1,
      'Historischen Snapshot erneut berechnen',
    );
    expect(screen.getByRole('link', { name: 'Ergebnis des Retries · Version 3' })).toHaveAttribute(
      'href',
      `/market-analyses/${analysisId}?version=3`,
    );
    expect(router.state.location.search).toBe('?version=1');
    expect(analysisApiClient.run).not.toHaveBeenCalled();
    expect(analysisApiClient.runReference).not.toHaveBeenCalled();
  });

  it('supersedes with a separate chosen newer version and a saved exact receipt', async () => {
    events = [];
    const user = userEvent.setup();
    show('?version=1');
    await loaded(1);
    await user.click(screen.getByRole('button', { name: 'Ersatzversion festlegen' }));
    expect(screen.queryByRole('button', { name: 'Retry aus Snapshot' })).not.toBeInTheDocument();
    await user.type(screen.getByLabelText('Begründung'), 'Explizit ersetzt');
    await user.selectOptions(screen.getByLabelText('Ersatzversion'), '2');
    await user.click(screen.getByRole('button', { name: 'Als ersetzt markieren' }));
    expect(await screen.findByText('Version 1 wurde durch Version 2 ersetzt.')).toBeInTheDocument();
    expect(analysisApiClient.supersede).toHaveBeenCalledExactlyOnceWith(
      analysisId,
      1,
      2,
      'Explizit ersetzt',
    );
    expect(screen.getByText('Grund: Explizit ersetzt')).toBeInTheDocument();
  });

  it('guards query changes and browser back/forward while preserving a reason until explicit discard', async () => {
    events = [];
    const user = userEvent.setup();
    const entries = [
      `/market-analyses/${analysisId}?version=2`,
      `/market-analyses/${analysisId}?version=1`,
    ];
    const router = show('', entries, 1);
    await openRetry();
    await user.type(screen.getByLabelText('Begründung'), 'Entwurf bleibt');
    await act(async () => {
      await router.navigate(-1);
    });
    const dialog = await screen.findByRole('alertdialog');
    expect(within(dialog).getByRole('button', { name: 'Hier bleiben' })).toHaveFocus();
    await user.keyboard('{Escape}');
    expect(screen.getByLabelText('Begründung')).toHaveValue('Entwurf bleibt');
    await user.selectOptions(screen.getByLabelText('Analyseversion'), '2');
    await user.click(
      within(await screen.findByRole('alertdialog')).getByRole('button', {
        name: 'Eingaben verwerfen und wechseln',
      }),
    );
    await loaded(2);
    expect(screen.queryByLabelText('Begründung')).not.toBeInTheDocument();
    await act(async () => {
      await router.navigate(-1);
    });
    await loaded(1);
    await openRetry();
    await user.type(screen.getByLabelText('Begründung'), 'Vorwärts schützen');
    await act(async () => {
      await router.navigate(1);
    });
    expect(await screen.findByRole('alertdialog')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    expect(router.state.location.search).toBe('?version=1');
    expect(screen.getByLabelText('Begründung')).toHaveValue('Vorwärts schützen');
    noWrites();
  });

  it('protects cancel and local action switches with one focused discard decision', async () => {
    events = [];
    const user = userEvent.setup();
    show('?version=1');
    await openRetry();
    await user.type(screen.getByLabelText('Begründung'), 'Keep');
    await user.click(screen.getByRole('button', { name: 'Abbrechen' }));
    await user.click(
      within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Hier bleiben' }),
    );
    expect(screen.getByLabelText('Begründung')).toHaveValue('Keep');
    await user.click(screen.getByRole('button', { name: 'Stattdessen Ersatzversion wählen' }));
    await user.click(screen.getByRole('button', { name: 'Entwurf verwerfen und fortfahren' }));
    expect(screen.getByLabelText('Begründung')).toHaveValue('');
    expect(screen.getByLabelText('Ersatzversion')).toHaveValue('');
    expect(screen.getAllByRole('form')).toHaveLength(1);
    noWrites();
  });

  it('locks double-submit synchronously and forbids discard while a lifecycle POST is pending', async () => {
    events = [];
    const user = userEvent.setup();
    const pending = deferred<AnalysisRun>();
    vi.mocked(analysisApiClient.retry).mockReturnValue(pending.promise);
    show('?version=1');
    await openRetry();
    fireEvent.submit(screen.getByRole('form'));
    fireEvent.submit(screen.getByRole('form'));
    await waitFor(() => expect(analysisApiClient.retry).toHaveBeenCalledTimes(1));
    expect(screen.getByRole('button', { name: 'Abbrechen' })).toBeDisabled();
    await user.click(screen.getByRole('link', { name: 'Zurück zu Marktanalysen' }));
    const dialog = await screen.findByRole('alertdialog');
    expect(within(dialog).getByText('Speicherung läuft')).toBeInTheDocument();
    expect(within(dialog).queryByRole('button', { name: /verwerfen/ })).not.toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Hier bleiben' }));
    detail = { ...detail, runs: [...detail.runs, retryRun] };
    events = [{ ...superseded, replacement_version: 3 }];
    await act(async () => {
      pending.resolve(retryRun);
      await pending.promise;
    });
    expect(await screen.findByText(/Retry als Version 3 bestätigt/)).toBeInTheDocument();
    expect(analysisApiClient.retry).toHaveBeenCalledTimes(1);
  });

  it('retains a specific conflict and inputs for correction without treating it as an uncertain POST', async () => {
    events = [];
    const user = userEvent.setup();
    vi.mocked(analysisApiClient.retry).mockRejectedValue(
      new MarketApiError(409, {
        code: 'ANALYSIS_CONFLICT',
        message: 'Stored model unavailable',
        details: [],
        timestamp: '2026-10-27T10:00:00Z',
      }),
    );
    show('?version=1');
    await openRetry();
    await user.type(screen.getByLabelText('Begründung'), 'Beleg bleibt');
    await user.click(screen.getByRole('button', { name: 'Retry aus Snapshot bestätigen' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'ANALYSIS_CONFLICT: Stored model unavailable',
    );
    expect(screen.getByLabelText('Begründung')).toHaveValue('Beleg bleibt');
    expect(screen.queryByText(/Abschluss unbekannt/)).not.toBeInTheDocument();
  });

  it('requires a new review when a fresh lifecycle state differs and keeps the reason', async () => {
    events = [];
    const user = userEvent.setup();
    show('?version=1');
    await openRetry();
    await user.type(screen.getByLabelText('Begründung'), 'Nicht löschen');
    events = [superseded];
    await user.click(screen.getByRole('button', { name: 'Retry aus Snapshot bestätigen' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Lesestand hat sich geändert');
    expect(screen.getByLabelText('Begründung')).toHaveValue('Nicht löschen');
    expect(analysisApiClient.retry).not.toHaveBeenCalled();
  });

  it('keeps acknowledged Retry separate from failed readback and retries GET only', async () => {
    events = [];
    const user = userEvent.setup();
    const realRetry = vi.mocked(analysisApiClient.retry).getMockImplementation()!;
    vi.mocked(analysisApiClient.retry).mockImplementation(async (...args) => {
      const result = await realRetry(...args);
      vi.mocked(analysisApiClient.get).mockRejectedValueOnce(new Error('Readback down'));
      return result;
    });
    show('?version=1');
    await openRetry();
    await user.click(screen.getByRole('button', { name: 'Retry aus Snapshot bestätigen' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Schritt bestätigt; Nachlesen fehlgeschlagen: Readback down',
    );
    expect(screen.getByText(/Retry als Version 3 bestätigt/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry aus Snapshot' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Nur Lesestand erneut laden' }));
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(
      screen.getByText('Diese historische Version wurde bereits ersetzt.'),
    ).toBeInTheDocument();
    expect(analysisApiClient.retry).toHaveBeenCalledTimes(1);
  });

  it('does not clear a confirmed receipt when GET still lacks its exact version/event', async () => {
    events = [];
    const user = userEvent.setup();
    vi.mocked(analysisApiClient.retry).mockResolvedValue(retryRun);
    show('?version=1');
    await openRetry();
    await user.click(screen.getByRole('button', { name: 'Retry aus Snapshot bestätigen' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'bestätigte Retry ist im aktuellen Lesestand',
    );
    await user.click(screen.getByRole('button', { name: 'Nur Lesestand erneut laden' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'bestätigte Retry ist im aktuellen Lesestand',
    );
    expect(analysisApiClient.retry).toHaveBeenCalledTimes(1);
  });

  it.each(['transport', 'malformed', 'server'])(
    'reads after %s uncertainty but never reissues or treats a matching state as its own completion',
    async (kind) => {
      events = [];
      const user = userEvent.setup();
      vi.mocked(analysisApiClient.retry).mockImplementation(() => {
        detail = { ...detail, runs: [...detail.runs, retryRun] };
        events = [{ ...superseded, replacement_version: 3 }];
        if (kind === 'transport')
          return Promise.reject(new MarketTransportError('Connection ended'));
        if (kind === 'server')
          return Promise.reject(
            new MarketApiError(500, {
              code: 'ANALYSIS_EXECUTION_FAILED',
              message: 'Stored failure',
              details: [],
              timestamp: '2026-10-27T10:00:00Z',
            }),
          );
        return Promise.resolve({ ...retryRun, model_version: 'invented' });
      });
      show('?version=1');
      await openRetry();
      await user.type(screen.getByLabelText('Begründung'), 'Offener Abschluss');
      await user.click(screen.getByRole('button', { name: 'Retry aus Snapshot bestätigen' }));
      expect(await screen.findByText(/Abschluss unbekannt/)).toBeInTheDocument();
      expect(screen.queryByText(/Retry als Version 3 bestätigt/)).not.toBeInTheDocument();
      await waitFor(() =>
        expect(screen.getByRole('button', { name: 'Nur Lesestand erneut laden' })).toBeEnabled(),
      );
      await user.click(screen.getByRole('button', { name: 'Nur Lesestand erneut laden' }));
      expect(screen.getByRole('button', { name: 'Retry aus Snapshot bestätigen' })).toBeDisabled();
      expect(screen.getByLabelText('Begründung')).toHaveValue('Offener Abschluss');
      expect(analysisApiClient.retry).toHaveBeenCalledTimes(1);
    },
  );

  it('retains an unknown request across version A→B→A instead of offering a blind new Retry', async () => {
    events = [];
    const user = userEvent.setup();
    vi.mocked(analysisApiClient.retry).mockRejectedValue(
      new MarketTransportError('Unknown receipt'),
    );
    const router = show('?version=1');
    await openRetry();
    await user.click(screen.getByRole('button', { name: 'Retry aus Snapshot bestätigen' }));
    expect(await screen.findByText(/Abschluss unbekannt/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText('Analyseversion')).toBeEnabled());
    await user.selectOptions(screen.getByLabelText('Analyseversion'), '2');
    await loaded(2);
    await act(async () => {
      await router.navigate(-1);
    });
    await loaded(1);
    expect(screen.getByText(/Abschluss unbekannt/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry aus Snapshot' })).toBeDisabled();
    expect(analysisApiClient.retry).toHaveBeenCalledTimes(1);
  });

  it('preserves an open reason when uncertain-state GETs fail and later succeed', async () => {
    events = [];
    const user = userEvent.setup();
    vi.mocked(analysisApiClient.retry).mockImplementation(() => {
      vi.mocked(analysisApiClient.events).mockRejectedValueOnce(new Error('Readback unavailable'));
      return Promise.reject(new MarketTransportError('Unknown receipt'));
    });
    show('?version=1');
    await openRetry();
    await user.type(screen.getByLabelText('Begründung'), 'Gebundener Entwurf');
    await user.click(screen.getByRole('button', { name: 'Retry aus Snapshot bestätigen' }));
    expect(await screen.findByText('Readback unavailable')).toBeInTheDocument();
    const input = screen.getByLabelText('Begründung');
    await user.click(screen.getByRole('button', { name: 'Nur Lesestand erneut laden' }));
    await waitFor(() => expect(screen.queryByText('Readback unavailable')).not.toBeInTheDocument());
    expect(screen.getByLabelText('Begründung')).toBe(input);
    expect(input).toHaveValue('Gebundener Entwurf');
    expect(screen.getByRole('button', { name: 'Retry aus Snapshot bestätigen' })).toBeDisabled();
    expect(analysisApiClient.retry).toHaveBeenCalledTimes(1);
  });

  it('keeps successful Verify and failed GET distinct without another Verify POST', async () => {
    const user = userEvent.setup();
    vi.mocked(analysisApiClient.verify).mockImplementation(() => {
      vi.mocked(analysisApiClient.events).mockRejectedValueOnce(new Error('Events unavailable'));
      return Promise.resolve(verification);
    });
    show();
    await loaded();
    await user.click(screen.getByRole('button', { name: 'Reproduzierbarkeit prüfen' }));
    expect(await screen.findByText('Reproduktion bestätigt')).toBeInTheDocument();
    expect(await screen.findByRole('alert')).toHaveTextContent('Events unavailable');
    await user.click(screen.getByRole('button', { name: 'Nur Lesestand erneut laden' }));
    expect(analysisApiClient.verify).toHaveBeenCalledTimes(1);
  });
});

describe('read-only paged snapshot', () => {
  it('loads only on request, with the selected version and exact page scope', async () => {
    const user = userEvent.setup();
    show('?version=1');
    await loaded(1);
    expect(analysisApiClient.getSnapshot).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Snapshot anzeigen (20)' }));
    expect(await screen.findByText('EODHD · SIE.XETRA')).toBeInTheDocument();
    expect(analysisApiClient.getSnapshot).toHaveBeenCalledWith(
      analysisId,
      1,
      0,
      50,
      expect.any(AbortSignal),
    );
    noWrites();
  });

  it('does not adopt an old snapshot response after the selected version changes', async () => {
    const user = userEvent.setup();
    const pending = deferred<Awaited<ReturnType<typeof analysisApiClient.getSnapshot>>>();
    vi.mocked(analysisApiClient.getSnapshot).mockReturnValueOnce(pending.promise);
    show('?version=1');
    await loaded(1);
    await user.click(screen.getByRole('button', { name: 'Snapshot anzeigen (20)' }));
    await user.selectOptions(screen.getByLabelText('Analyseversion'), '2');
    await loaded(2);
    await act(async () => {
      pending.resolve({ items: [], offset: 0, limit: 50, total: 999 });
      await pending.promise;
    });
    expect(screen.queryByText(/von 999/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Snapshot anzeigen (250)' })).toBeInTheDocument();
  });
});
