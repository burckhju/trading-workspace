import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';

import { candidateApiClient } from '../../candidate/services/client';
import type { CandidateEvaluation } from '../../candidate/types/api';
import { marketApiClient } from '../../market/services/client';
import { MarketTransportError } from '../../market/services/http';
import type { UnderlyingDetailResponse } from '../../market/types/api';
import { tradePlanApiClient } from '../services/client';
import { loadCandidatePlanCurrencySuggestion } from '../services/planCurrencySuggestion';
import type { TradePlanDetailResponse } from '../types/api';
import { TradePlanWorkflowPage } from './TradePlanWorkflowPage';

vi.mock('../services/planCurrencySuggestion', () => ({
  loadCandidatePlanCurrencySuggestion: vi.fn(),
}));
vi.mock('../services/client', () => ({
  tradePlanApiClient: {
    create: vi.fn(),
    get: vi.fn(),
    versions: vi.fn(),
    version: vi.fn(),
    amend: vi.fn(),
    submitForReview: vi.fn(),
    approve: vi.fn(),
    returnToDraft: vi.fn(),
    abandon: vi.fn(),
    delete: vi.fn(),
  },
}));
vi.mock('../../market/services/client', () => ({
  marketApiClient: { getUnderlying: vi.fn(), searchUnderlyings: vi.fn() },
}));
vi.mock('../../candidate/services/client', () => ({
  candidateApiClient: { list: vi.fn(), evaluations: vi.fn() },
}));

const candidateApi = vi.mocked(candidateApiClient);
const marketApi = vi.mocked(marketApiClient);
const planApi = vi.mocked(tradePlanApiClient);
const readSuggestion = vi.mocked(loadCandidatePlanCurrencySuggestion);
type Suggestion = Awaited<ReturnType<typeof loadCandidatePlanCurrencySuggestion>>;
const now = '2026-11-06T08:00:00Z';
const suggestion = {
  currency: 'USD',
  analysisId: 'analysis-a',
  version: 3,
  listingId: 'historical-listing-a',
};

function underlying(key: string): UnderlyingDetailResponse {
  return {
    id: `underlying-${key}`,
    type: 'STOCK',
    name: `Planaktie ${key}`,
    isin: null,
    wkn: null,
    lifecycle_status: 'ACTIVE',
    quality_status: 'VERIFIED',
    version: 1,
    created_at: now,
    updated_at: now,
    primary_listing: {
      id: `current-listing-${key}`,
      ticker: key.toUpperCase(),
      trading_venue_id: 'venue',
      trading_venue_mic: 'XETR',
      trading_venue_name: 'Xetra',
      currency_code: 'EUR',
    },
    listings: [],
  };
}

function evaluation(key: string): CandidateEvaluation {
  return {
    id: `evaluation-${key}`,
    version: 7,
    direction: 'LONG',
    model_id: 'candidate-model',
    model_version: '1.0.0',
    qualification: 'QUALIFIED',
    quality_status: 'GOOD',
    warnings: [],
    evaluated_at: now,
    criteria: [],
    sources: [
      {
        role: 'UNDERLYING',
        source_type: 'ANALYSIS',
        source_id: `analysis-${key}`,
        source_version: 3,
        model_id: 'analysis-model',
        model_version: '1.0.0',
      },
    ],
  };
}

function savedPlan(currency: string): TradePlanDetailResponse {
  return {
    plan: {
      id: 'plan-a',
      underlying_id: 'underlying-a',
      origin_type: 'CANDIDATE_EVALUATION',
      candidate_id: 'candidate-a',
      candidate_evaluation_id: 'evaluation-a',
      created_at: now,
      created_by: 'actor',
    },
    latest_version: {
      id: 'version-a',
      trade_plan_id: 'plan-a',
      version: 1,
      direction: 'LONG',
      thesis: 'Bewusste These',
      entry: {
        type: 'PRICE',
        currency,
        price: '100',
        price_from: null,
        price_to: null,
        trigger: null,
        reference_price: null,
        valid_until: null,
        rationale: null,
      },
      invalidation: { stop_price: '95', invalidation_rule: null, rationale: null },
      targets: [{ sequence: 1, price: '110', rationale: null }],
      risk_assumptions: { thesis_risk: 'Fehlausbruch', max_loss_assumption: null, notes: null },
      status: 'DRAFT',
      created_at: now,
      created_by: 'actor',
      previous_version_id: null,
      change_reason: null,
      candidate_evaluation: {
        candidate_id: 'candidate-a',
        evaluation_id: 'evaluation-a',
        evaluation_version: 7,
        direction: 'LONG',
        model_id: 'candidate-model',
        model_version: '1.0.0',
        qualification: 'QUALIFIED',
        quality_status: 'GOOD',
        evaluated_at: now,
        sources: evaluation('a').sources!,
      },
      approval: null,
      events: [],
    },
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

const candidatePath = (key = 'a') =>
  `/trade-plans?candidate_id=candidate-${key}&candidate_evaluation_id=evaluation-${key}`;

function mount(path = candidatePath()) {
  const router = createMemoryRouter(
    [{ path: '/trade-plans', element: <TradePlanWorkflowPage /> }],
    { initialEntries: [path] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

function edit(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

function fillAssumptions() {
  edit('Trade Thesis', 'Bewusste These');
  edit('Entry-Preis', '100');
  edit('Technischer Stop', '95');
  edit('Target 1', '110');
  edit('Plan-Risiko / Annahme', 'Fehlausbruch');
}

let stored: TradePlanDetailResponse;
beforeEach(() => {
  vi.resetAllMocks();
  stored = savedPlan('CHF');
  candidateApi.list.mockResolvedValue(
    ['a', 'b'].map((key) => ({
      id: `candidate-${key}`,
      underlying_id: `underlying-${key}`,
      status: 'READY_FOR_PLANNING',
      created_at: now,
      created_by: 'actor',
    })),
  );
  candidateApi.evaluations.mockImplementation((id) => {
    const exact = evaluation(id.slice(-1));
    return Promise.resolve([{ ...exact, id: 'newer-evaluation', version: 8 }, exact]);
  });
  marketApi.getUnderlying.mockImplementation((id) => Promise.resolve(underlying(id.slice(-1))));
  readSuggestion.mockResolvedValue(suggestion);
  planApi.get.mockImplementation(() => Promise.resolve(stored));
  planApi.version.mockImplementation(() => Promise.resolve(stored.latest_version));
  planApi.versions.mockImplementation(() => Promise.resolve([stored.latest_version]));
  planApi.create.mockImplementation((request) => {
    stored = savedPlan(request.entry.currency);
    return Promise.resolve(stored);
  });
});

describe('new Candidate TradePlan currency suggestion', () => {
  it('initializes only currency from the validated historical origin, then saves the visible value explicitly', async () => {
    const router = mount();
    await waitFor(() => expect(screen.getByLabelText('Währung')).toHaveValue('USD'));
    expect(screen.getByLabelText('Währung')).toBeEnabled();
    expect(screen.getByLabelText('Währung')).toHaveAccessibleDescription(
      'Initialvorschlag aus Analyse analysis-a, Version 3. Die Planwährung bleibt editierbar.',
    );
    expect(readSuggestion).toHaveBeenCalledExactlyOnceWith(
      {
        type: 'CANDIDATE_EVALUATION',
        candidateId: 'candidate-a',
        evaluation: evaluation('a'),
        underlying: underlying('a'),
      },
      expect.any(AbortSignal),
    );
    for (const label of ['Trade Thesis', 'Entry-Preis', 'Technischer Stop', 'Target 1'])
      expect(screen.getByLabelText(label)).toHaveValue('');
    expect(router.state.location.search).toBe(new URL(candidatePath(), 'https://test').search);
    expect(planApi.create).not.toHaveBeenCalled();
    expect(planApi.approve).not.toHaveBeenCalled();

    fillAssumptions();
    expect(screen.getByText(/Initialvorschlag aus Analyse analysis-a, Version 3/)).toBeVisible();
    edit('Währung', 'CHF');
    expect(screen.queryByText(/Initialvorschlag/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'TradePlan als DRAFT erstellen' }));
    await screen.findByRole('heading', { name: 'Version 1 · DRAFT' });
    expect(planApi.create).toHaveBeenCalledExactlyOnceWith({
      origin_type: 'CANDIDATE_EVALUATION',
      candidate_id: 'candidate-a',
      candidate_evaluation_id: 'evaluation-a',
      thesis: 'Bewusste These',
      entry: { type: 'PRICE', currency: 'CHF', price: '100' },
      invalidation: { stop_price: '95' },
      targets: [{ sequence: 1, price: '110' }],
      risk_assumptions: { thesis_risk: 'Fehlausbruch' },
    });
    expect(within(screen.getByRole('region', { name: 'Einstieg' })).getByText('CHF')).toBeVisible();
    expect(screen.queryByText(/Initialvorschlag/)).not.toBeInTheDocument();
    expect(planApi.submitForReview).not.toHaveBeenCalled();
    expect(planApi.approve).not.toHaveBeenCalled();
    expect(readSuggestion).toHaveBeenCalledTimes(1);
  });

  it.each(['missing', 'failed'])(
    'keeps manual currency entry and creation usable for an optional %s snapshot',
    async (outcome) => {
      if (outcome === 'missing') readSuggestion.mockResolvedValue(null);
      else readSuggestion.mockRejectedValue(new Error('optional snapshot unavailable'));
      mount();
      await screen.findByLabelText('Trade Thesis');
      await waitFor(() => expect(readSuggestion).toHaveBeenCalledTimes(1));
      expect(screen.getByLabelText('Währung')).toHaveValue('');
      expect(screen.getByRole('button', { name: 'TradePlan als DRAFT erstellen' })).toBeEnabled();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      fillAssumptions();
      edit('Währung', 'CHF');
      fireEvent.click(screen.getByRole('button', { name: 'TradePlan als DRAFT erstellen' }));
      await screen.findByRole('heading', { name: 'Version 1 · DRAFT' });
      expect(planApi.create).toHaveBeenCalledTimes(1);
      expect(planApi.create.mock.calls[0][0].entry.currency).toBe('CHF');
    },
  );

  it('does not let optional fallback validate an invalid required Candidate origin', async () => {
    candidateApi.evaluations.mockResolvedValue([]);
    mount();
    expect(await screen.findByRole('alert')).toHaveTextContent(/kein Ersatz gewählt/);
    expect(screen.queryByLabelText('Währung')).not.toBeInTheDocument();
    expect(readSuggestion).not.toHaveBeenCalled();
    expect(planApi.create).not.toHaveBeenCalled();
  });

  it('keeps manual creation blank without starting an Analysis read', async () => {
    mount('/trade-plans?underlying_id=underlying-a');
    expect(await screen.findByLabelText('Währung')).toHaveValue('');
    expect(readSuggestion).not.toHaveBeenCalled();
    expect(screen.queryByText(/Initialvorschlag/)).not.toBeInTheDocument();
  });

  it.each(['DRAFT', 'APPROVED'] as const)(
    'keeps a stored Candidate %s and its amendment on the saved currency without new source reads',
    async (status) => {
      stored.latest_version.status = status;
      mount('/trade-plans?trade_plan_id=plan-a&trade_plan_version_id=version-a');
      await screen.findByRole('heading', { name: `Version 1 · ${status}` });
      expect(
        within(screen.getByRole('region', { name: 'Einstieg' })).getByText('CHF'),
      ).toBeVisible();
      if (status === 'APPROVED') {
        fireEvent.click(screen.getByRole('button', { name: 'Neue Planversion erstellen' }));
        expect(screen.getByLabelText('Währung')).toHaveValue('CHF');
      }
      expect(readSuggestion).not.toHaveBeenCalled();
      expect(screen.queryByText(/Initialvorschlag/)).not.toBeInTheDocument();
      expect(planApi.amend).not.toHaveBeenCalled();
    },
  );

  it.each([
    ['Trade Thesis', 'Meine These'],
    ['Entry-Preis', '101'],
    ['Referenzpreis', '99'],
    ['Technischer Stop', '90'],
    ['Target 1', '120'],
    ['Währung', 'CHF'],
    ['Plan-Risiko / Annahme', 'Mein Risiko'],
    ['Entry-Art', 'TRIGGER'],
  ])('protects an earlier %s edit against a delayed source', async (label, value) => {
    const pending = deferred<Suggestion>();
    readSuggestion.mockReturnValue(pending.promise);
    mount();
    await screen.findByLabelText('Währung');
    await waitFor(() => expect(readSuggestion).toHaveBeenCalledTimes(1));
    if (label === 'Referenzpreis') fireEvent.click(screen.getByText('Weitere Entry-Angaben'));
    edit(label, value);
    await act(async () => {
      pending.resolve(suggestion);
      await pending.promise;
    });
    expect(screen.getByLabelText(label)).toHaveValue(value);
    expect(screen.getByLabelText('Währung')).toHaveValue(label === 'Währung' ? value : '');
    expect(screen.queryByText(/Initialvorschlag/)).not.toBeInTheDocument();
    expect(planApi.create).not.toHaveBeenCalled();
  });

  it.each(['Währung', 'Entry-Preis', 'Trade Thesis'])(
    'keeps the suggestion locked after editing and clearing %s',
    async (label) => {
      const pending = deferred<Suggestion>();
      readSuggestion.mockReturnValue(pending.promise);
      mount();
      await screen.findByLabelText('Währung');
      await waitFor(() => expect(readSuggestion).toHaveBeenCalledTimes(1));
      edit(label, label === 'Währung' ? 'USD' : '100');
      edit(label, '');
      await act(async () => {
        pending.resolve(suggestion);
        await pending.promise;
      });
      expect(screen.getByLabelText('Währung')).toHaveValue('');
      expect(screen.queryByText(/Initialvorschlag/)).not.toBeInTheDocument();
    },
  );

  it.each(['Entry-Preis', 'Trade Thesis'])(
    'does not claim a queued suggestion after a %s edit wins before React commits it',
    async (label) => {
      const pending = deferred<Suggestion>();
      readSuggestion.mockReturnValue(pending.promise);
      mount();
      await screen.findByLabelText('Währung');
      await waitFor(() => expect(readSuggestion).toHaveBeenCalledTimes(1));
      const input = screen.getByLabelText(label);
      await act(async () => {
        pending.resolve(suggestion);
        await pending.promise;
        // The source callback has queued its updates, but this edit still sees the old form.
        fireEvent.change(input, { target: { value: '101' } });
      });
      expect(screen.getByLabelText(label)).toHaveValue('101');
      expect(screen.getByLabelText('Währung')).toHaveValue('');
      expect(screen.queryByText(/Initialvorschlag/)).not.toBeInTheDocument();
      edit('Währung', 'USD');
      expect(screen.queryByText(/Initialvorschlag/)).not.toBeInTheDocument();
      expect(readSuggestion).toHaveBeenCalledTimes(1);
    },
  );

  it('does not restore automatic provenance when the user enters the suggested code again', async () => {
    mount();
    await waitFor(() => expect(screen.getByLabelText('Währung')).toHaveValue('USD'));
    edit('Währung', 'CHF');
    edit('Währung', 'USD');
    expect(screen.getByLabelText('Währung')).not.toHaveAttribute('aria-describedby');
    expect(screen.queryByText(/Initialvorschlag/)).not.toBeInTheDocument();
    expect(readSuggestion).toHaveBeenCalledTimes(1);
  });

  it('does not mark initialization dirty and gives a new form its own edit protection', async () => {
    const router = mount();
    await waitFor(() => expect(screen.getByLabelText('Währung')).toHaveValue('USD'));
    fireEvent.click(screen.getByRole('button', { name: 'Ursprung wechseln' }));
    expect(await screen.findByLabelText('Basiswert suchen')).toBeInTheDocument();
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    await act(() => router.navigate(candidatePath()));
    await waitFor(() => expect(screen.getByLabelText('Währung')).toHaveValue('USD'));
    expect(readSuggestion).toHaveBeenCalledTimes(2);
    edit('Trade Thesis', 'Mein Entwurf');
    fireEvent.click(screen.getByRole('button', { name: 'Ursprung wechseln' }));
    expect(await screen.findByRole('alertdialog')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    expect(screen.getByLabelText('Trade Thesis')).toHaveValue('Mein Entwurf');
    expect(planApi.create).not.toHaveBeenCalled();
  });

  it.each(['success', 'error'])(
    'does not revive an already completed A %s when returning through B to a new pending A',
    async (outcome) => {
      const current = deferred<Suggestion>();
      readSuggestion.mockReset();
      if (outcome === 'success') readSuggestion.mockResolvedValueOnce(suggestion);
      else readSuggestion.mockRejectedValueOnce(new Error('previous A failure'));
      readSuggestion.mockResolvedValueOnce(null).mockReturnValueOnce(current.promise);
      const router = mount();
      if (outcome === 'success')
        await waitFor(() => expect(screen.getByLabelText('Währung')).toHaveValue('USD'));
      else await screen.findByText(/Kein Währungsvorschlag verfügbar/);
      await act(() => router.navigate(candidatePath('b')));
      await waitFor(() => expect(readSuggestion).toHaveBeenCalledTimes(2));
      await act(() => router.navigate(candidatePath()));
      await waitFor(() => expect(readSuggestion).toHaveBeenCalledTimes(3));
      expect(screen.getByLabelText('Währung')).toHaveValue('');
      expect(screen.getByLabelText('Währung')).not.toHaveAttribute('aria-describedby');
      expect(
        screen.queryByText(/Währungsvorschlag verfügbar|Initialvorschlag/),
      ).not.toBeInTheDocument();
      await act(async () => {
        current.resolve(suggestion);
        await current.promise;
      });
      expect(screen.getByLabelText('Währung')).toHaveValue('USD');
      expect(screen.getByText(/Initialvorschlag aus Analyse analysis-a, Version 3/)).toBeVisible();
      expect(planApi.create).not.toHaveBeenCalled();
    },
  );

  it.each(['success', 'error'])(
    'ignores old A and B %s responses across A to B to A, even when abort is ignored',
    async (outcome) => {
      const firstA = deferred<Suggestion>();
      const b = deferred<Suggestion>();
      const secondA = deferred<Suggestion>();
      readSuggestion
        .mockReturnValueOnce(firstA.promise)
        .mockReturnValueOnce(b.promise)
        .mockReturnValueOnce(secondA.promise);
      const router = mount();
      await waitFor(() => expect(readSuggestion).toHaveBeenCalledTimes(1));
      await act(() => router.navigate(candidatePath('b')));
      await waitFor(() => expect(readSuggestion).toHaveBeenCalledTimes(2));
      await act(() => router.navigate(candidatePath()));
      await waitFor(() => expect(readSuggestion).toHaveBeenCalledTimes(3));
      expect(readSuggestion.mock.calls[0][1].aborted).toBe(true);
      expect(readSuggestion.mock.calls[1][1].aborted).toBe(true);
      await act(async () => {
        if (outcome === 'success') firstA.resolve(suggestion);
        else firstA.reject(new Error('old A failure'));
        await firstA.promise.catch(() => undefined);
      });
      expect(screen.getByLabelText('Währung')).toHaveValue('');
      expect(
        screen.queryByText(/Währungsvorschlag verfügbar|Initialvorschlag/),
      ).not.toBeInTheDocument();
      await act(async () => {
        secondA.resolve(suggestion);
        await secondA.promise;
      });
      expect(screen.getByLabelText('Währung')).toHaveValue('USD');
      await act(async () => {
        if (outcome === 'success')
          b.resolve({ ...suggestion, currency: 'EUR', analysisId: 'analysis-b' });
        else b.reject(new Error('old B failure'));
        await b.promise.catch(() => undefined);
      });
      expect(screen.getByLabelText('Währung')).toHaveValue('USD');
      expect(screen.getByText(/Initialvorschlag aus Analyse analysis-a, Version 3/)).toBeVisible();
      expect(screen.queryByText(/Kein Währungsvorschlag/)).not.toBeInTheDocument();
      expect(planApi.create).not.toHaveBeenCalled();
    },
  );

  it('keeps busy navigation and unknown-write replay protection after initialization', async () => {
    const pending = deferred<TradePlanDetailResponse>();
    planApi.create.mockReturnValue(pending.promise);
    mount();
    await waitFor(() => expect(screen.getByLabelText('Währung')).toHaveValue('USD'));
    fillAssumptions();
    const form = screen.getByLabelText('Trade Thesis').closest('form')!;
    act(() => {
      fireEvent.submit(form);
      fireEvent.submit(form);
    });
    expect(planApi.create).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Währung')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Ursprung wechseln' })).toBeDisabled();
    await act(async () => {
      pending.reject(new MarketTransportError('unknown outcome'));
      await pending.promise.catch(() => undefined);
    });
    expect(await screen.findByRole('alert')).toHaveTextContent(
      /Abschluss der Speicherung ist unklar/,
    );
    expect(screen.getByLabelText('Währung')).toHaveValue('USD');
    expect(screen.getByRole('button', { name: 'TradePlan als DRAFT erstellen' })).toBeDisabled();
    fireEvent.submit(form);
    expect(planApi.create).toHaveBeenCalledTimes(1);
    expect(readSuggestion).toHaveBeenCalledTimes(1);
    expect(planApi.approve).not.toHaveBeenCalled();
  });
});
