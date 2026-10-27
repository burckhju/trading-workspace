import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { createMemoryRouter, MemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CandidatePage } from './CandidatePage';

const mocks = vi.hoisted(() => ({
  list: vi.fn(),
  evaluations: vi.fn(),
  liveWorkflow: vi.fn(),
  evaluateAuto: vi.fn(),
}));
vi.mock('../services/client', () => ({ candidateApiClient: mocks }));

function renderHistory(evaluation = 'eval-a') {
  return render(
    <MemoryRouter
      initialEntries={[
        `/candidates?candidate=candidate-1&${evaluation ? `evaluation=${evaluation}` : ''}`,
      ]}
    >
      <CandidatePage />
    </MemoryRouter>,
  );
}

describe('exact persisted Candidate history', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.list.mockResolvedValue([
      { id: 'candidate-1', underlying_id: 'underlying-1', status: 'UNDER_REVIEW' },
    ]);
    mocks.liveWorkflow.mockResolvedValue({ can_evaluate: true, ready: true, steps: [] });
    mocks.evaluations.mockResolvedValue(
      [2, 1].map((n) => ({
        id: n === 1 ? 'eval-a' : 'eval-b',
        version: n,
        direction: 'LONG',
        model_id: 'TOP_DOWN_CANDIDATE',
        model_version: String(n),
        qualification: n === 1 ? 'QUALIFIED' : 'NOT_QUALIFIED',
        quality_status: 'GOOD',
        warnings: [],
        evaluated_at: '2026-10-25T10:00:00Z',
        criteria: [],
        sources: [
          {
            role: 'MARKET',
            source_type: 'MarketContextAssessment',
            source_id: 'market-analysis-1',
            source_version: 4,
            model_id: 'MARKET_CONTEXT',
            model_version: '1.0',
          },
        ],
      })),
    );
    mocks.evaluateAuto.mockReturnValue(new Promise(() => undefined));
  });

  it('reads the exact historical evaluation and retains model and analysis provenance after a later result', async () => {
    renderHistory();
    const region = await screen.findByRole('region', { name: 'Evaluation eval-a' });
    expect(within(region).getByText('Version 1')).toBeInTheDocument();
    expect(within(region).getByRole('heading', { name: 'QUALIFIED' })).toBeInTheDocument();
    expect(within(region).getByText(/market-analysis-1.*Quellversion 4/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Bewertungsstand 1/ })).toHaveAttribute(
      'href',
      '/candidates?candidate=candidate-1&evaluation=eval-a',
    );
    expect(mocks.evaluateAuto).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('link', { name: /Bewertungsstand 2/ }));
    expect(await screen.findByRole('region', { name: 'Evaluation eval-b' })).toBeInTheDocument();
    expect(mocks.evaluateAuto).not.toHaveBeenCalled();
  });

  it('does not replace an unknown evaluation link with latest', async () => {
    renderHistory('missing');
    await screen.findByRole('link', { name: /Bewertungsstand 2/ });
    expect(screen.getByText(/angeforderte Evaluation.*nicht im Lesestand/)).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Evaluation eval-b' })).toBeNull();
    expect(mocks.evaluateAuto).not.toHaveBeenCalled();
  });

  it('sends one evaluation for two synchronous explicit clicks', async () => {
    renderHistory('');
    const button = await screen.findByRole('button', { name: 'Top-down neu bewerten' });
    await screen.findByRole('region', { name: 'Evaluation eval-b' });
    act(() => {
      fireEvent.click(button);
      fireEvent.click(button);
    });
    expect(mocks.evaluateAuto).toHaveBeenCalledTimes(1);
  });
  it('opens exactly the persisted analysis source with a return to this historical evaluation', async () => {
    mocks.evaluations.mockResolvedValue([
      {
        id: 'eval-a',
        version: 1,
        direction: 'LONG',
        model_id: 'TOP_DOWN_CANDIDATE',
        model_version: '1.0',
        qualification: 'QUALIFIED',
        quality_status: 'GOOD',
        warnings: [],
        evaluated_at: '2026-10-25T10:00:00Z',
        criteria: [],
        sources: [
          {
            role: 'MARKET',
            source_type: 'ANALYSIS',
            source_id: 'analysis-1',
            source_version: 3,
            model_id: 'EOD_TREND_MOMENTUM',
            model_version: '1.0.0',
          },
        ],
      },
    ]);
    const router = createMemoryRouter(
      [
        { path: '/candidates', element: <CandidatePage /> },
        { path: '/market-analyses/:analysisId', element: <h1>Exakte Analysequelle</h1> },
      ],
      { initialEntries: ['/candidates?candidate=candidate-1&evaluation=eval-a'] },
    );
    render(<RouterProvider router={router} />);
    const source = await screen.findByRole('link', { name: 'MARKET: Analyseversion 3 öffnen' });
    fireEvent.click(source);
    await screen.findByRole('heading', { name: 'Exakte Analysequelle' });
    const params = new URLSearchParams(router.state.location.search);
    expect(router.state.location.pathname).toBe('/market-analyses/analysis-1');
    expect(params.get('version')).toBe('3');
    expect(params.get('candidate_id')).toBe('candidate-1');
    expect(params.get('evaluation_id')).toBe('eval-a');
    expect(mocks.evaluateAuto).not.toHaveBeenCalled();
  });

  it('does not reinterpret a legacy source type as an analysis link', async () => {
    renderHistory();
    await screen.findByRole('region', { name: 'Evaluation eval-a' });
    expect(
      screen.queryByRole('link', { name: /Analyseversion .* öffnen/ }),
    ).not.toBeInTheDocument();
  });
});
