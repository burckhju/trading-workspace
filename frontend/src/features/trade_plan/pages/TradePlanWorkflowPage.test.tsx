import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useNavigate } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { candidateApiClient } from '../../candidate/services/client';
import { marketApiClient } from '../../market/services/client';
import type { UnderlyingDetailResponse } from '../../market/types/api';
import { tradePlanApiClient } from '../services/client';
import { TradePlanWorkflowPage } from './TradePlanWorkflowPage';

vi.mock('../../market/services/client', () => ({
  marketApiClient: { searchUnderlyings: vi.fn(), getUnderlying: vi.fn() },
}));
vi.mock('../../candidate/services/client', () => ({
  candidateApiClient: { list: vi.fn(), evaluations: vi.fn() },
}));
vi.mock('../services/client', () => ({
  tradePlanApiClient: { create: vi.fn(), get: vi.fn(), versions: vi.fn(), version: vi.fn() },
}));
const marketApi = vi.mocked(marketApiClient);
const candidateApi = vi.mocked(candidateApiClient);
const apple: UnderlyingDetailResponse = {
  id: 'underlying-apple',
  type: 'STOCK',
  name: 'Apple Inc.',
  isin: 'US0378331005',
  wkn: '865985',
  lifecycle_status: 'ACTIVE',
  quality_status: 'VERIFIED',
  version: 1,
  created_at: '2026-09-04T00:00:00Z',
  updated_at: '2026-09-04T00:00:00Z',
  primary_listing: {
    id: 'listing-apple',
    ticker: 'AAPL',
    trading_venue_id: 'venue-1',
    trading_venue_mic: 'XNAS',
    trading_venue_name: 'Nasdaq',
    currency_code: 'USD',
  },
  listings: [],
};
const evaluation = {
  id: 'evaluation-1',
  version: 7,
  direction: 'LONG',
  model_id: 'TEST',
  model_version: '1.0',
  qualification: 'QUALIFIED' as const,
  quality_status: 'GOOD',
  evaluated_at: apple.created_at,
  warnings: [],
  criteria: [],
};
function mount(path = '/trade-plans') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <TradePlanWorkflowPage />
    </MemoryRouter>,
  );
}

describe('TradePlanWorkflowPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    marketApi.searchUnderlyings.mockResolvedValue({
      items: [apple],
      total: 1,
      offset: 0,
      limit: 10,
    });
    marketApi.getUnderlying.mockResolvedValue(apple);
    candidateApi.list.mockResolvedValue([
      {
        id: 'candidate-1',
        underlying_id: apple.id,
        status: 'READY_FOR_PLANNING',
        created_at: apple.created_at,
        created_by: 'actor',
      },
    ]);
    candidateApi.evaluations.mockResolvedValue([evaluation]);
  });

  it('selects an active underlying once by business identifiers and binds it without a UUID input', async () => {
    mount();
    expect(screen.queryByLabelText('Trade Thesis')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Basiswert suchen'), { target: { value: 'Apple' } });
    fireEvent.click(screen.getByRole('button', { name: 'Suchen' }));
    await waitFor(() =>
      expect(marketApi.searchUnderlyings).toHaveBeenCalledWith(
        { query: 'Apple', lifecycleStatus: 'ACTIVE', limit: 10 },
        expect.any(AbortSignal),
      ),
    );
    fireEvent.click(await screen.findByRole('button', { name: /Apple Inc\./ }));
    expect(await screen.findByRole('heading', { name: 'Apple Inc.' })).toBeInTheDocument();
    expect(screen.queryByLabelText('Basiswert suchen')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Underlying-ID')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Währung')).toHaveValue('');
    expect(screen.getByLabelText('Trade Thesis')).toBeInTheDocument();
  });

  it('shows the exact candidate evaluation and its underlying as readable context', async () => {
    mount('/trade-plans?candidate_id=candidate-1&candidate_evaluation_id=evaluation-1');
    expect(screen.queryByLabelText('Basiswert suchen')).not.toBeInTheDocument();
    expect(await screen.findByText(/CandidateEvaluation · Version 7/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Apple Inc.' })).toBeInTheDocument();
    expect(screen.queryByLabelText('Candidate-ID')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('CandidateEvaluation-ID')).not.toBeInTheDocument();
  });

  it.each([
    '?candidate_id=candidate-1',
    '?candidate_evaluation_id=evaluation-1',
    '?candidate_id=&candidate_evaluation_id=evaluation-1',
    '?underlying_id=',
    '?underlying_id=underlying-apple&underlying_id=other',
  ])(
    'rejects incomplete or ambiguous origin %s without silently selecting another one',
    async (query) => {
      mount(`/trade-plans${query}`);
      expect(await screen.findByRole('alert')).toBeInTheDocument();
      expect(screen.queryByLabelText('Basiswert suchen')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Trade Thesis')).not.toBeInTheDocument();
      expect(marketApi.searchUnderlyings).not.toHaveBeenCalled();
      expect(tradePlanApiClient.create).not.toHaveBeenCalled();
      fireEvent.click(screen.getByRole('button', { name: 'Ursprung neu auswählen' }));
      expect(await screen.findByLabelText('Basiswert suchen')).toBeInTheDocument();
    },
  );

  it('rejects a candidate / underlying mismatch', async () => {
    mount(
      '/trade-plans?candidate_id=candidate-1&candidate_evaluation_id=evaluation-1&underlying_id=other',
    );
    expect(
      await screen.findByText(/Basiswert passt nicht zum gewählten Kandidaten/),
    ).toBeInTheDocument();
    expect(marketApi.getUnderlying).not.toHaveBeenCalled();
    expect(screen.queryByLabelText('Trade Thesis')).not.toBeInTheDocument();
  });

  it('does not replace a missing evaluation with the latest one', async () => {
    candidateApi.evaluations.mockResolvedValue([{ ...evaluation, id: 'evaluation-2', version: 8 }]);
    mount('/trade-plans?candidate_id=candidate-1&candidate_evaluation_id=evaluation-1');
    expect(await screen.findByText(/Es wurde kein Ersatz gewählt/)).toBeInTheDocument();
    expect(screen.queryByLabelText('Trade Thesis')).not.toBeInTheDocument();
  });

  it.each(['identity', 'inactive', 'short', 'missing-candidate'])(
    'rejects invalid loaded origin %s',
    async (kind) => {
      if (kind === 'identity') marketApi.getUnderlying.mockResolvedValue({ ...apple, id: 'other' });
      if (kind === 'inactive')
        marketApi.getUnderlying.mockResolvedValue({ ...apple, lifecycle_status: 'INACTIVE' });
      if (kind === 'short')
        candidateApi.evaluations.mockResolvedValue([{ ...evaluation, direction: 'SHORT' }]);
      if (kind === 'missing-candidate') candidateApi.list.mockResolvedValue([]);
      mount(
        kind === 'short' || kind === 'missing-candidate'
          ? '/trade-plans?candidate_id=candidate-1&candidate_evaluation_id=evaluation-1'
          : '/trade-plans?underlying_id=underlying-apple',
      );
      expect(await screen.findByRole('alert')).toBeInTheDocument();
      expect(screen.queryByLabelText('Trade Thesis')).not.toBeInTheDocument();
    },
  );

  it('does not show stale search results after another query', async () => {
    let resolve!: (value: {
      items: UnderlyingDetailResponse[];
      total: number;
      offset: number;
      limit: number;
    }) => void;
    marketApi.searchUnderlyings.mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    mount();
    fireEvent.change(screen.getByLabelText('Basiswert suchen'), { target: { value: 'Apple' } });
    fireEvent.click(screen.getByRole('button', { name: 'Suchen' }));
    fireEvent.change(screen.getByLabelText('Basiswert suchen'), { target: { value: 'Microsoft' } });
    await act(async () => {
      resolve({ items: [apple], total: 1, offset: 0, limit: 10 });
      await Promise.resolve();
    });
    expect(screen.queryByRole('button', { name: /Apple Inc/ })).not.toBeInTheDocument();
    expect(screen.getByLabelText('Basiswert suchen')).toHaveValue('Microsoft');
  });

  it('ignores a late origin response after navigating to another underlying', async () => {
    let resolve!: (value: UnderlyingDetailResponse) => void;
    marketApi.getUnderlying.mockImplementation((id) =>
      id === apple.id
        ? new Promise((done) => {
            resolve = done;
          })
        : Promise.resolve({ ...apple, id: 'other', name: 'Other underlying' }),
    );
    function NavigateContext() {
      const navigate = useNavigate();
      return (
        <>
          <button onClick={() => void navigate('/trade-plans?underlying_id=other')}>
            Other context
          </button>
          <TradePlanWorkflowPage />
        </>
      );
    }
    render(
      <MemoryRouter initialEntries={['/trade-plans?underlying_id=underlying-apple']}>
        <NavigateContext />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Other context' }));
    expect(await screen.findByRole('heading', { name: 'Other underlying' })).toBeInTheDocument();
    await act(async () => {
      resolve(apple);
      await Promise.resolve();
    });
    expect(screen.getByRole('heading', { name: 'Other underlying' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Apple Inc.' })).not.toBeInTheDocument();
  });

  it.each([
    '?trade_plan_version_id=version-only',
    '?trade_plan_id=',
    '?trade_plan_id=one&trade_plan_id=two',
  ])('rejects invalid stored-plan routing %s', (query) => {
    mount(`/trade-plans${query}`);
    expect(screen.getByRole('alert')).toHaveTextContent('unvollständig oder mehrdeutig');
    expect(screen.queryByLabelText('Basiswert suchen')).not.toBeInTheDocument();
  });

  it('shows failed searches and empty results without starting a plan', async () => {
    marketApi.searchUnderlyings
      .mockRejectedValueOnce(new Error('Search unavailable'))
      .mockResolvedValueOnce({ items: [], total: 0, offset: 0, limit: 10 });
    mount();
    fireEvent.change(screen.getByLabelText('Basiswert suchen'), { target: { value: 'AAPL' } });
    fireEvent.click(screen.getByRole('button', { name: 'Suchen' }));
    expect(await screen.findByText('Search unavailable')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Suchen' }));
    expect(await screen.findByText('Keine aktiven Basiswerte gefunden.')).toBeInTheDocument();
    expect(tradePlanApiClient.create).not.toHaveBeenCalled();
  });
});
