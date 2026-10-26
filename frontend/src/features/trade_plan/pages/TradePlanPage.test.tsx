import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, createMemoryRouter, RouterProvider } from 'react-router-dom';

import { candidateApiClient } from '../../candidate/services/client';
import { marketApiClient } from '../../market/services/client';
import { MarketApiError, MarketTransportError } from '../../market/services/http';
import type { UnderlyingDetailResponse } from '../../market/types/api';
import { tradePlanApiClient } from '../services/client';
import type { TradePlanDetailResponse, TradePlanVersionResponse } from '../types/api';
import { TradePlanPage } from './TradePlanPage';
import { TradePlanWorkflowPage } from './TradePlanWorkflowPage';

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
const mockedClient = vi.mocked(tradePlanApiClient);
const marketApi = vi.mocked(marketApiClient);
const candidateApi = vi.mocked(candidateApiClient);

const version: TradePlanVersionResponse = {
  id: '22222222-2222-4222-8222-222222222222',
  trade_plan_id: '11111111-1111-4111-8111-111111111111',
  version: 3,
  direction: 'LONG',
  thesis: 'Continuation thesis',
  entry: {
    type: 'PRICE',
    currency: 'EUR',
    price: '100',
    price_from: null,
    price_to: null,
    trigger: null,
    reference_price: null,
    valid_until: null,
    rationale: null,
  },
  invalidation: { stop_price: '95', invalidation_rule: 'Close below support', rationale: null },
  targets: [{ sequence: 1, price: '110', rationale: null }],
  risk_assumptions: { thesis_risk: 'Breakout failure', max_loss_assumption: null, notes: null },
  status: 'APPROVED',
  created_at: '2026-08-11T15:00:00Z',
  created_by: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  previous_version_id: '33333333-3333-4333-8333-333333333333',
  change_reason: 'Raise stop',
  candidate_evaluation: {
    candidate_id: '44444444-4444-4444-8444-444444444444',
    evaluation_id: '55555555-5555-4555-8555-555555555555',
    evaluation_version: 7,
    direction: 'LONG',
    model_id: 'TOP_DOWN_CANDIDATE',
    model_version: '1.0.0',
    qualification: 'QUALIFIED',
    quality_status: 'GOOD',
    evaluated_at: '2026-08-11T14:30:00Z',
    sources: [
      {
        role: 'MARKET_CONTEXT',
        source_type: 'MarketContextAssessment',
        source_id: '66666666-6666-4666-8666-666666666666',
        source_version: 2,
        model_id: 'MARKET_CONTEXT',
        model_version: '1.0.0',
      },
    ],
  },
  approval: {
    approval_id: '77777777-7777-4777-8777-777777777777',
    trade_plan_version_id: '22222222-2222-4222-8222-222222222222',
    version: 3,
    actor: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    approved_at: '2026-08-11T15:10:00Z',
    correlation_id: 'corr-approve',
  },
  events: [
    {
      id: '88888888-8888-4888-8888-888888888888',
      event_type: 'APPROVED',
      from_status: 'READY_FOR_REVIEW',
      to_status: 'APPROVED',
      reason: null,
      actor: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      correlation_id: 'corr-approve',
      occurred_at: '2026-08-11T15:10:00Z',
    },
  ],
};

const detail: TradePlanDetailResponse = {
  plan: {
    id: '11111111-1111-4111-8111-111111111111',
    underlying_id: '99999999-9999-4999-8999-999999999999',
    origin_type: 'CANDIDATE_EVALUATION',
    candidate_id: '44444444-4444-4444-8444-444444444444',
    candidate_evaluation_id: '55555555-5555-4555-8555-555555555555',
    created_at: '2026-08-11T14:45:00Z',
    created_by: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  },
  latest_version: version,
};

const underlying: UnderlyingDetailResponse = {
  id: detail.plan.underlying_id,
  type: 'STOCK',
  name: 'Apple Inc.',
  isin: 'US0378331005',
  wkn: '865985',
  lifecycle_status: 'ACTIVE',
  quality_status: 'VERIFIED',
  version: 1,
  created_at: version.created_at,
  updated_at: version.created_at,
  primary_listing: null,
  listings: [],
};
const manualDetail: TradePlanDetailResponse = {
  plan: {
    ...detail.plan,
    origin_type: 'MANUAL',
    candidate_id: null,
    candidate_evaluation_id: null,
  },
  latest_version: {
    ...version,
    version: 1,
    status: 'DRAFT',
    previous_version_id: null,
    change_reason: null,
    candidate_evaluation: null,
    approval: null,
    events: [],
  },
};
function mount(path = `/trade-plans?underlying_id=${underlying.id}`) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <TradePlanPage />
    </MemoryRouter>,
  );
}
async function fillContent() {
  await screen.findByLabelText('Trade Thesis');
  expect(screen.getByLabelText('Währung')).toHaveValue('');
  fireEvent.change(screen.getByLabelText('Trade Thesis'), {
    target: { value: 'Breakout continuation' },
  });
  fireEvent.change(screen.getByLabelText('Währung'), { target: { value: 'USD' } });
  fireEvent.change(screen.getByLabelText('Entry-Preis'), {
    target: { value: '100.000000123456789' },
  });
  fireEvent.change(screen.getByLabelText('Technischer Stop'), { target: { value: '95' } });
  fireEvent.change(screen.getByLabelText('Target 1'), { target: { value: '110' } });
  fireEvent.change(screen.getByLabelText('Plan-Risiko / Annahme'), {
    target: { value: 'False breakout' },
  });
}
function submit() {
  fireEvent.click(screen.getByRole('button', { name: 'TradePlan als DRAFT erstellen' }));
}

describe('TradePlanPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    marketApi.getUnderlying.mockResolvedValue(underlying);
    mockedClient.get.mockResolvedValue(manualDetail);
    mockedClient.versions.mockResolvedValue([manualDetail.latest_version]);
    mockedClient.version.mockResolvedValue(manualDetail.latest_version);
    mockedClient.create.mockResolvedValue(manualDetail);
    candidateApi.list.mockResolvedValue([
      {
        id: detail.plan.candidate_id!,
        underlying_id: underlying.id,
        status: 'READY_FOR_PLANNING',
        created_at: version.created_at,
        created_by: version.created_by,
      },
    ]);
    candidateApi.evaluations.mockResolvedValue([
      {
        id: detail.plan.candidate_evaluation_id!,
        version: 7,
        direction: 'LONG',
        model_id: 'TOP_DOWN_CANDIDATE',
        model_version: '1.0.0',
        qualification: 'QUALIFIED',
        quality_status: 'GOOD',
        warnings: [],
        evaluated_at: version.created_at,
        criteria: [],
      },
    ]);
  });

  it('shows exact stored candidate provenance, source snapshots and lifecycle on the central view', async () => {
    mockedClient.get.mockResolvedValue(detail);
    mockedClient.versions.mockResolvedValue([version]);
    mount(`/trade-plans?trade_plan_id=${detail.plan.id}`);
    await screen.findByRole('heading', { name: 'TP-11111111' });
    fireEvent.click(screen.getByText('Herkunft und Lifecycle anzeigen'));
    fireEvent.click(screen.getByText('Technische Provenance anzeigen'));
    expect(screen.getByText(/gespeicherte Evaluation v7/)).toBeInTheDocument();
    expect(screen.getAllByText(/MARKET_CONTEXT/).length).toBeGreaterThan(0);
    expect(screen.getByText('Lifecycle für Version 3')).toBeInTheDocument();
    expect(screen.getByText(/Correlation corr-approve/)).toBeInTheDocument();
    expect(screen.getByText('Approval-Nachweis')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Produktauswahl starten' })).toHaveAttribute(
      'href',
      `/product-selection?trade_plan_id=${detail.plan.id}&trade_plan_version_id=${version.id}`,
    );
    expect(screen.queryByLabelText('Underlying-ID')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Trade Thesis')).not.toBeInTheDocument();
  });

  it('creates with one bound underlying, explicit plan currency and full content, then shows only the central view', async () => {
    mount();
    await fillContent();
    expect(screen.queryByLabelText('Underlying-ID')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Apple Inc.' })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Invalidierungsregel'), {
      target: { value: 'Close below support' },
    });
    fireEvent.change(screen.getByLabelText('Target-Begründung 1'), {
      target: { value: 'Prior high' },
    });
    fireEvent.click(screen.getByText('Weitere Risikoangaben'));
    fireEvent.change(screen.getByLabelText('Max-Loss-Annahme (optional)'), {
      target: { value: '5%' },
    });
    fireEvent.change(screen.getByLabelText('Risk Notes'), {
      target: { value: 'No position sizing' },
    });
    submit();
    await waitFor(() => expect(mockedClient.create).toHaveBeenCalledTimes(1));
    expect(mockedClient.create.mock.calls[0][0]).toEqual({
      origin_type: 'MANUAL',
      underlying_id: underlying.id,
      thesis: 'Breakout continuation',
      entry: { type: 'PRICE', currency: 'USD', price: '100.000000123456789' },
      invalidation: { stop_price: '95', invalidation_rule: 'Close below support' },
      targets: [{ sequence: 1, price: '110', rationale: 'Prior high' }],
      risk_assumptions: {
        thesis_risk: 'False breakout',
        max_loss_assumption: '5%',
        notes: 'No position sizing',
      },
    });
    await screen.findByRole('heading', { name: 'TP-11111111' });
    expect(screen.getByText('TradePlan wurde als DRAFT erstellt.')).toBeInTheDocument();
    expect(screen.queryByLabelText('Trade Thesis')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'TradePlan als DRAFT erstellen' }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Zur Prüfung einreichen' })).toBeInTheDocument();
  });

  it('pins a concrete CandidateEvaluation despite a newer evaluation and never sends an underlying override', async () => {
    const exact = (await candidateApi.evaluations(detail.plan.candidate_id!))[0];
    candidateApi.evaluations.mockResolvedValue([
      { ...exact, id: 'new-evaluation', version: 8 },
      exact,
    ]);
    mockedClient.create.mockResolvedValue({
      ...detail,
      latest_version: { ...version, status: 'DRAFT' },
    });
    mount(
      `/trade-plans?candidate_id=${detail.plan.candidate_id}&candidate_evaluation_id=${detail.plan.candidate_evaluation_id}`,
    );
    await fillContent();
    fireEvent.change(screen.getByLabelText('Entry-Art'), { target: { value: 'TRIGGER' } });
    fireEvent.change(screen.getByLabelText('Trigger'), { target: { value: 'Break above 101' } });
    expect(screen.getByText(/CandidateEvaluation · Version 7/)).toBeInTheDocument();
    expect(screen.queryByLabelText('Candidate-ID')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('CandidateEvaluation-ID')).not.toBeInTheDocument();
    submit();
    await waitFor(() => expect(mockedClient.create).toHaveBeenCalledTimes(1));
    expect(mockedClient.create.mock.calls[0][0]).toMatchObject({
      origin_type: 'CANDIDATE_EVALUATION',
      candidate_id: detail.plan.candidate_id,
      candidate_evaluation_id: detail.plan.candidate_evaluation_id,
      entry: { type: 'TRIGGER', trigger: 'Break above 101', price: null },
    });
    expect(mockedClient.create.mock.calls[0][0]).not.toHaveProperty('underlying_id');
  });

  it('locks all affected inputs synchronously and ignores repeated submission', async () => {
    let resolve!: (value: TradePlanDetailResponse) => void;
    mockedClient.create.mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    mount();
    await fillContent();
    const form = screen.getByLabelText('Trade Thesis').closest('form')!;
    act(() => {
      fireEvent.submit(form);
      fireEvent.submit(form);
    });
    expect(mockedClient.create).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Trade Thesis')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Ursprung wechseln' })).toBeDisabled();
    await act(async () => {
      resolve(manualDetail);
      await Promise.resolve();
    });
    expect(await screen.findByRole('heading', { name: 'TP-11111111' })).toBeInTheDocument();
  });

  it('retains inputs and a visible conflict without changing the selected origin', async () => {
    mockedClient.create.mockRejectedValue(
      new MarketApiError(409, {
        code: 'CONTEXT_CONFLICT',
        message: 'Ursprung ist nicht mehr verfügbar',
        details: [],
        timestamp: version.created_at,
      }),
    );
    mount();
    await fillContent();
    submit();
    expect(await screen.findByText('Ursprung ist nicht mehr verfügbar')).toBeInTheDocument();
    expect(screen.getByLabelText('Trade Thesis')).toHaveValue('Breakout continuation');
    expect(screen.getByLabelText('Währung')).toHaveValue('USD');
    expect(mockedClient.create).toHaveBeenCalledTimes(1);
  });

  it('does not repeat a write when the result is unknown', async () => {
    mockedClient.create.mockRejectedValue(new MarketTransportError('network unavailable'));
    mount();
    await fillContent();
    submit();
    expect(await screen.findByText(/Abschluss der Speicherung ist unklar/)).toBeInTheDocument();
    expect(screen.getByLabelText('Trade Thesis')).toHaveValue('Breakout continuation');
    expect(screen.getByRole('button', { name: 'TradePlan als DRAFT erstellen' })).toBeDisabled();
    expect(mockedClient.create).toHaveBeenCalledTimes(1);
  });

  it('retains a confirmed creation when the following read fails', async () => {
    mockedClient.get.mockRejectedValue(new Error('reload failed'));
    mount();
    await fillContent();
    submit();
    expect(await screen.findByRole('heading', { name: 'TP-11111111' })).toBeInTheDocument();
    expect(screen.getByText('TradePlan wurde als DRAFT erstellt.')).toBeInTheDocument();
    expect(
      await screen.findByText(/Planansicht konnte nicht aktualisiert werden: reload failed/),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText('Trade Thesis')).not.toBeInTheDocument();
    expect(mockedClient.create).toHaveBeenCalledTimes(1);
  });

  it('does not accept a success response for a different underlying', async () => {
    mockedClient.create.mockResolvedValue({
      ...manualDetail,
      plan: { ...manualDetail.plan, underlying_id: 'other-underlying' },
    });
    mount();
    await fillContent();
    submit();
    expect(await screen.findByText(/zurückgegebenen Referenzen passen nicht/)).toBeInTheDocument();
    expect(screen.getByLabelText('Trade Thesis')).toHaveValue('Breakout continuation');
    expect(screen.getByRole('button', { name: 'TradePlan als DRAFT erstellen' })).toBeDisabled();
  });

  it.each(['empty', 'approved', 'manual-candidate', 'missing-version-id'])(
    'treats malformed success %s as an unconfirmed result and preserves input',
    async (kind) => {
      const returned = kind === 'empty' ? null : structuredClone(manualDetail);
      if (returned && kind === 'approved') returned.latest_version.status = 'APPROVED';
      if (returned && kind === 'manual-candidate')
        returned.plan.candidate_id = 'unexpected-candidate';
      if (returned && kind === 'missing-version-id') returned.latest_version.id = '';
      mockedClient.create.mockResolvedValue(returned as TradePlanDetailResponse);
      mount();
      await fillContent();
      submit();
      expect(
        await screen.findByText(/zurückgegebenen Referenzen passen nicht/),
      ).toBeInTheDocument();
      expect(screen.getByLabelText('Trade Thesis')).toHaveValue('Breakout continuation');
      expect(screen.getByRole('button', { name: 'TradePlan als DRAFT erstellen' })).toBeDisabled();
      expect(mockedClient.create).toHaveBeenCalledTimes(1);
    },
  );

  it('requires an explicit discard before changing an unsaved origin and preserves it when cancelled', async () => {
    const router = createMemoryRouter(
      [{ path: '/trade-plans', element: <TradePlanWorkflowPage /> }],
      { initialEntries: [`/trade-plans?underlying_id=${underlying.id}`] },
    );
    render(<RouterProvider router={router} />);
    await fillContent();
    fireEvent.click(screen.getByRole('button', { name: 'Ursprung wechseln' }));
    expect(await screen.findByRole('alertdialog')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Hier bleiben' })).toHaveFocus();
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    expect(screen.getByLabelText('Trade Thesis')).toHaveValue('Breakout continuation');
    fireEvent.click(screen.getByRole('button', { name: 'Ursprung wechseln' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
    expect(await screen.findByLabelText('Basiswert suchen')).toBeInTheDocument();
    expect(mockedClient.create).not.toHaveBeenCalled();
  });
});
