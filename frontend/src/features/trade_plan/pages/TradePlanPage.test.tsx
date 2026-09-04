import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import { tradePlanApiClient } from '../services/client';
import type { TradePlanDetailResponse, TradePlanVersionResponse } from '../types/api';
import { TradePlanPage } from './TradePlanPage';

vi.mock('../services/client', () => ({
  tradePlanApiClient: {
    create: vi.fn(),
    get: vi.fn(),
    versions: vi.fn(),
    submitForReview: vi.fn(),
    approve: vi.fn(),
    returnToDraft: vi.fn(),
    abandon: vi.fn(),
  },
}));

const mockedClient = vi.mocked(tradePlanApiClient);

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

describe('TradePlanPage', () => {
  beforeEach(() => {
    mockedClient.create.mockReset();
    mockedClient.get.mockReset();
    mockedClient.versions.mockReset();
    mockedClient.submitForReview.mockReset();
    mockedClient.approve.mockReset();
    mockedClient.returnToDraft.mockReset();
    mockedClient.abandon.mockReset();
    mockedClient.get.mockResolvedValue(detail);
    mockedClient.versions.mockResolvedValue([version]);
  });

  it('renders exact CandidateEvaluation provenance, source snapshots and lifecycle audit', async () => {
    render(
      <MemoryRouter>
        <TradePlanPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText('TradePlan-ID'), {
      target: { value: detail.plan.id },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Laden' }));

    expect(await screen.findByText('CandidateEvaluation-Provenance')).toBeInTheDocument();
    expect(screen.getByText(/v7/)).toBeInTheDocument();
    expect(screen.getAllByText(/MARKET_CONTEXT/).length).toBeGreaterThan(0);
    expect(screen.getByText('Audit / Lifecycle')).toBeInTheDocument();
    expect(screen.getAllByText('APPROVED').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Correlation corr-approve/).length).toBeGreaterThan(0);
    expect(screen.getByText('Approval-Nachweis')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'TP-11111111' })).toBeInTheDocument();
    expect(screen.getByText('Produktauswahl starten')).toBeInTheDocument();
  });

  it('creates a manual PRICE TradePlan with product-neutral plan inputs', async () => {
    const draftVersion: TradePlanVersionResponse = {
      ...version,
      version: 1,
      status: 'DRAFT',
      previous_version_id: null,
      change_reason: null,
      candidate_evaluation: null,
      approval: null,
      events: [],
    };
    const manualDetail: TradePlanDetailResponse = {
      plan: {
        ...detail.plan,
        origin_type: 'MANUAL',
        candidate_id: null,
        candidate_evaluation_id: null,
      },
      latest_version: draftVersion,
    };
    mockedClient.create.mockResolvedValue(manualDetail);

    render(
      <MemoryRouter>
        <TradePlanPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText('Underlying-ID'), {
      target: { value: manualDetail.plan.underlying_id },
    });
    fireEvent.change(screen.getByLabelText('Trade Thesis'), {
      target: { value: 'Breakout continuation' },
    });
    fireEvent.change(screen.getByLabelText('Entry-Preis'), { target: { value: '100' } });
    fireEvent.change(screen.getByLabelText('Technischer Stop'), { target: { value: '95' } });
    fireEvent.change(screen.getByLabelText('Invalidierungsregel'), {
      target: { value: 'Close below support' },
    });
    fireEvent.change(screen.getByLabelText('Target 1'), { target: { value: '110' } });
    fireEvent.change(screen.getByLabelText('Target-Begründung'), {
      target: { value: 'Prior high' },
    });
    fireEvent.change(screen.getByLabelText('Plan-Risiko / Annahme'), {
      target: { value: 'Breakout failure' },
    });
    fireEvent.change(screen.getByLabelText('Max-Loss-Annahme (optional)'), {
      target: { value: '5%' },
    });
    fireEvent.change(screen.getByLabelText('Risk Notes'), {
      target: { value: 'No position sizing' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'TradePlan als DRAFT erstellen' }));

    await waitFor(() => expect(mockedClient.create).toHaveBeenCalledTimes(1));
    const request = mockedClient.create.mock.calls[0]?.[0];
    expect(request).toBeDefined();
    if (!request) throw new Error('Expected create request');
    expect(request.origin_type).toBe('MANUAL');
    if (request.origin_type !== 'MANUAL') throw new Error('Expected manual request');
    expect(request.underlying_id).toBe(manualDetail.plan.underlying_id);
    expect(request.thesis).toBe('Breakout continuation');
    expect(request.entry).toEqual({
      type: 'PRICE',
      currency: 'EUR',
      price: '100',
      price_from: null,
      price_to: null,
      trigger: null,
    });
    expect(request.invalidation).toEqual({
      stop_price: '95',
      invalidation_rule: 'Close below support',
    });
    expect(request.targets).toEqual([{ sequence: 1, price: '110', rationale: 'Prior high' }]);
    expect(request.risk_assumptions).toEqual({
      thesis_risk: 'Breakout failure',
      max_loss_assumption: '5%',
      notes: 'No position sizing',
    });
    expect(
      await screen.findByText(
        'TradePlan TP-11111111 wurde als DRAFT erstellt. Nächster Schritt: Zur Prüfung einreichen.',
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'TP-11111111' })).toBeInTheDocument();
    expect(screen.getByText('Zur Prüfung einreichen')).toBeInTheDocument();
    expect(screen.getAllByText(/Manueller Ursprung/).length).toBeGreaterThan(0);
  });

  it('creates a CandidateEvaluation-originated TRIGGER plan without client underlying override', async () => {
    const draftCandidate: TradePlanDetailResponse = {
      ...detail,
      latest_version: { ...version, status: 'DRAFT', approval: null, events: [] },
    };
    mockedClient.create.mockResolvedValue(draftCandidate);

    render(
      <MemoryRouter>
        <TradePlanPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText('Ursprung'), {
      target: { value: 'CANDIDATE_EVALUATION' },
    });
    expect(
      screen.getByText(/serverseitig ausschließlich aus der konkreten CandidateEvaluation/),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Candidate-ID'), {
      target: { value: detail.plan.candidate_id },
    });
    fireEvent.change(screen.getByLabelText('CandidateEvaluation-ID'), {
      target: { value: detail.plan.candidate_evaluation_id },
    });
    fireEvent.change(screen.getByLabelText('Trade Thesis'), {
      target: { value: 'Candidate handoff thesis' },
    });
    fireEvent.change(screen.getByLabelText('Entry-Art'), { target: { value: 'TRIGGER' } });
    fireEvent.change(screen.getByLabelText('Trigger'), { target: { value: 'Break above 101' } });
    fireEvent.change(screen.getByLabelText('Target 1'), { target: { value: '112' } });
    fireEvent.change(screen.getByLabelText('Plan-Risiko / Annahme'), {
      target: { value: 'False breakout' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'TradePlan als DRAFT erstellen' }));

    await waitFor(() => expect(mockedClient.create).toHaveBeenCalledTimes(1));
    const request = mockedClient.create.mock.calls[0]?.[0];
    expect(request).toBeDefined();
    if (!request) throw new Error('Expected create request');
    expect(request.origin_type).toBe('CANDIDATE_EVALUATION');
    if (request.origin_type !== 'CANDIDATE_EVALUATION') {
      throw new Error('Expected CandidateEvaluation request');
    }
    expect(request.candidate_id).toBe(detail.plan.candidate_id);
    expect(request.candidate_evaluation_id).toBe(detail.plan.candidate_evaluation_id);
    expect(request.entry.type).toBe('TRIGGER');
    expect(request.entry.trigger).toBe('Break above 101');
    expect(request.entry.price).toBeNull();
    expect(request).not.toHaveProperty('underlying_id');
  });

  it('executes review and explicit approval through the client', async () => {
    const draft = { ...version, status: 'DRAFT' as const, approval: null, events: [] };
    const ready = { ...version, status: 'READY_FOR_REVIEW' as const, approval: null, events: [] };
    const draftDetail = { ...detail, latest_version: draft };
    const readyDetail = { ...detail, latest_version: ready };

    mockedClient.get
      .mockResolvedValueOnce(draftDetail)
      .mockResolvedValueOnce(readyDetail)
      .mockResolvedValueOnce(detail);
    mockedClient.versions
      .mockResolvedValueOnce([draft])
      .mockResolvedValueOnce([ready])
      .mockResolvedValueOnce([version]);
    mockedClient.submitForReview.mockResolvedValue(ready);
    mockedClient.approve.mockResolvedValue(version);

    render(
      <MemoryRouter>
        <TradePlanPage />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText('TradePlan-ID'), { target: { value: detail.plan.id } });
    fireEvent.click(screen.getByRole('button', { name: 'Laden' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Zur Prüfung' })).toBeEnabled());

    fireEvent.click(screen.getByRole('button', { name: 'Zur Prüfung' }));
    await waitFor(() =>
      expect(mockedClient.submitForReview).toHaveBeenCalledWith(detail.plan.id, draft.id),
    );
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Explizit freigeben' })).toBeEnabled(),
    );

    fireEvent.click(screen.getByRole('button', { name: 'Explizit freigeben' }));
    await waitFor(() =>
      expect(mockedClient.approve).toHaveBeenCalledWith(detail.plan.id, ready.id),
    );
    expect(await screen.findByText('Approval-Nachweis')).toBeInTheDocument();
  });

  it('executes return-to-draft and abandon through the client', async () => {
    const ready = { ...version, status: 'READY_FOR_REVIEW' as const, approval: null, events: [] };
    const draft = { ...version, status: 'DRAFT' as const, approval: null, events: [] };
    const abandoned = { ...draft, status: 'ABANDONED' as const };
    const readyDetail = { ...detail, latest_version: ready };
    const draftDetail = { ...detail, latest_version: draft };
    const abandonedDetail = { ...detail, latest_version: abandoned };

    mockedClient.get
      .mockResolvedValueOnce(readyDetail)
      .mockResolvedValueOnce(draftDetail)
      .mockResolvedValueOnce(abandonedDetail);
    mockedClient.versions
      .mockResolvedValueOnce([ready])
      .mockResolvedValueOnce([draft])
      .mockResolvedValueOnce([abandoned]);
    mockedClient.returnToDraft.mockResolvedValue(draft);
    mockedClient.abandon.mockResolvedValue(abandoned);

    render(
      <MemoryRouter>
        <TradePlanPage />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText('TradePlan-ID'), { target: { value: detail.plan.id } });
    fireEvent.click(screen.getByRole('button', { name: 'Laden' }));
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Zurück zu DRAFT' })).toBeEnabled(),
    );

    fireEvent.click(screen.getByRole('button', { name: 'Zurück zu DRAFT' }));
    await waitFor(() =>
      expect(mockedClient.returnToDraft).toHaveBeenCalledWith(detail.plan.id, ready.id),
    );
    await waitFor(() => expect(screen.getByRole('button', { name: 'Aufgeben' })).toBeEnabled());

    fireEvent.click(screen.getByRole('button', { name: 'Aufgeben' }));
    await waitFor(() =>
      expect(mockedClient.abandon).toHaveBeenCalledWith(detail.plan.id, draft.id),
    );
  });
});
