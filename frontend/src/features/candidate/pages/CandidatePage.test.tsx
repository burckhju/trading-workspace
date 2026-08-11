import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import { candidateApiClient } from '../services/client';
import { CandidatePage } from './CandidatePage';

vi.mock('../services/client', () => ({
  candidateApiClient: {
    list: vi.fn(),
    evaluations: vi.fn(),
    evaluateAuto: vi.fn(),
    liveWorkflow: vi.fn(),
  },
}));

const mockedClient = vi.mocked(candidateApiClient);

describe('CandidatePage', () => {
  beforeEach(() => {
    mockedClient.list.mockResolvedValue([
      {
        id: 'candidate-1',
        underlying_id: 'underlying-1',
        status: 'UNDER_REVIEW',
        created_at: '2026-08-08T20:00:00Z',
        created_by: 'Test User',
      },
    ]);
    mockedClient.evaluateAuto.mockResolvedValue({} as never);
    mockedClient.liveWorkflow.mockResolvedValue({
      candidate_id: 'candidate-1',
      underlying_id: 'underlying-1',
      as_of: '2026-08-08T20:00:00Z',
      ready: false,
      can_evaluate: false,
      next_action: 'CREATE_EODHD_MAPPING',
      steps: [
        {
          code: 'MARKET_PROVIDER_MAPPING',
          label: 'Market EODHD mapping',
          status: 'BLOCKED',
          detail: 'No EODHD mapping exists.',
          action: 'CREATE_EODHD_MAPPING',
          resource_id: null,
          action_params: null,
        },
      ],
    });
    mockedClient.evaluations.mockResolvedValue([
      {
        id: 'evaluation-1',
        version: 1,
        direction: 'LONG',
        model_id: 'TOP_DOWN_CANDIDATE',
        model_version: '1.0.0',
        qualification: 'QUALIFIED',
        quality_status: 'GOOD',
        warnings: ['Market context is CAUTIOUS'],
        evaluated_at: '2026-08-08T20:01:00Z',
        criteria: [
          {
            criterion_id: 'TD-MARKET-001',
            group: 'MARKET',
            severity: 'REQUIRED',
            evaluation: 'FULFILLED',
            source: 'MarketContextAssessment',
            actual_value: 'CAUTIOUS',
            expected_value: 'FAVORABLE or CAUTIOUS',
            numeric_value: null,
            explanation: 'Primary market context must support the requested direction',
          },
        ],
      },
    ]);
  });

  it('shows qualification separately from user status and explains market gate', async () => {
    render(
      <MemoryRouter>
        <CandidatePage />
      </MemoryRouter>,
    );

    expect(await screen.findByText('QUALIFIED')).toBeInTheDocument();
    expect(screen.getByText('Benutzerstatus: UNDER_REVIEW')).toBeInTheDocument();
    expect(screen.getByText('TD-MARKET-001')).toBeInTheDocument();
    expect(screen.getByText(/Market context is CAUTIOUS/)).toBeInTheDocument();
    expect(screen.getByText(/Nächster Schritt: CREATE_EODHD_MAPPING/)).toBeInTheDocument();
    expect(screen.getByText('Market EODHD mapping')).toBeInTheDocument();
  });
});
