import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { HypothesisProposalPanel } from './HypothesisProposalPanel';

const mocks = vi.hoisted(() => ({
  listForHypothesis: vi.fn(),
  listModels: vi.fn(),
  listVersions: vi.fn(),
  create: vi.fn(),
}));

vi.mock('../services/hypothesisProposalClient', () => ({
  hypothesisProposalClient: mocks,
}));

describe('HypothesisProposalPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listForHypothesis.mockResolvedValue([]);
    mocks.listModels.mockResolvedValue([
      {
        id: 'model-1',
        model_key: 'TOP_DOWN',
        name: 'Top Down',
        purpose: 'Rank candidates',
        created_at: '2026-08-28T18:00:00Z',
        created_by: 'actor-1',
      },
    ]);
    mocks.listVersions.mockResolvedValue([
      {
        id: 'version-1',
        model_id: 'model-1',
        version: 1,
        status: 'APPROVED',
        definition: { threshold: 1 },
        change_summary: 'Initial',
        created_at: '2026-08-28T18:00:00Z',
        created_by: 'actor-1',
        previous_version_id: null,
      },
    ]);
  });

  it('shows existing proposal and suppresses duplicate creation by default', async () => {
    mocks.listForHypothesis.mockResolvedValue([
      {
        id: 'proposal-1',
        model_id: 'model-1',
        base_model_version_id: 'version-1',
        hypothesis_id: 'hypothesis-1',
        status: 'DRAFT',
        proposed_definition: { threshold: 2 },
        rationale: 'Tighten selectivity',
        created_at: '2026-08-28T18:00:00Z',
        created_by: 'actor-1',
      },
    ]);

    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);

    expect(await screen.findByText('ModelChangeProposal vorhanden')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'ModelChangeProposal als DRAFT anlegen' }),
    ).toBeNull();
  });

  it('creates proposal from an approved base version', async () => {
    mocks.create.mockResolvedValue({
      id: 'proposal-1',
      model_id: 'model-1',
      base_model_version_id: 'version-1',
      hypothesis_id: 'hypothesis-1',
      status: 'DRAFT',
      proposed_definition: { threshold: 2 },
      rationale: 'Tighten selectivity',
      created_at: '2026-08-28T18:00:00Z',
      created_by: 'actor-1',
    });

    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);

    await screen.findByText('ModelChangeProposal erstellen');
    fireEvent.change(screen.getByLabelText('Governed Model'), {
      target: { value: 'model-1' },
    });
    await waitFor(() =>
      expect(mocks.listVersions).toHaveBeenCalledWith('model-1', expect.anything()),
    );
    await waitFor(() =>
      expect(screen.getByLabelText('APPROVED Base-Version')).toHaveValue('version-1'),
    );
    fireEvent.change(screen.getByLabelText('Proposed Definition (JSON)'), {
      target: { value: '{"threshold":2}' },
    });
    fireEvent.change(screen.getByLabelText('Rationale'), {
      target: { value: 'Tighten selectivity' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'ModelChangeProposal als DRAFT anlegen' }));

    await waitFor(() =>
      expect(mocks.create).toHaveBeenCalledWith({
        model_id: 'model-1',
        base_model_version_id: 'version-1',
        hypothesis_id: 'hypothesis-1',
        proposed_definition: { threshold: 2 },
        rationale: 'Tighten selectivity',
      }),
    );
    expect(await screen.findByText('ModelChangeProposal vorhanden')).toBeInTheDocument();
  });
});
