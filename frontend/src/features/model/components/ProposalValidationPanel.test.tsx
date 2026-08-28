import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ProposalValidationPanel } from './ProposalValidationPanel';

const mocks = vi.hoisted(() => ({
  listForProposal: vi.fn(),
  create: vi.fn(),
}));

vi.mock('../services/proposalValidationClient', () => ({
  proposalValidationClient: mocks,
}));

describe('ProposalValidationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listForProposal.mockResolvedValue([]);
  });

  it('shows existing validation and suppresses duplicate creation', async () => {
    mocks.listForProposal.mockResolvedValue([
      {
        id: 'validation-1',
        proposal_id: 'proposal-1',
        method: 'RETROSPECTIVE',
        evidence_cutoff_at: '2026-08-28T18:00:00Z',
        conclusion: 'SUPPORTS',
        metrics: {},
        notes: 'Stable',
        created_at: '2026-08-28T18:10:00Z',
        created_by: 'actor-1',
      },
    ]);

    render(<ProposalValidationPanel proposalId="proposal-1" proposalStatus="VALIDATED" />);

    expect(await screen.findByText('Retrospektiv validiert')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Proposal retrospektiv validieren' })).toBeNull();
  });

  it('creates a retrospective validation for a DRAFT proposal', async () => {
    mocks.create.mockResolvedValue({
      id: 'validation-1',
      proposal_id: 'proposal-1',
      method: 'RETROSPECTIVE',
      evidence_cutoff_at: '2026-08-28T18:00:00Z',
      conclusion: 'SUPPORTS',
      metrics: { expectancy_delta: 0.2 },
      notes: 'Stable',
      created_at: '2026-08-28T18:10:00Z',
      created_by: 'actor-1',
    });

    render(<ProposalValidationPanel proposalId="proposal-1" proposalStatus="DRAFT" />);
    await screen.findByRole('button', { name: 'Proposal retrospektiv validieren' });

    fireEvent.change(screen.getByLabelText('LearningEvidence IDs'), {
      target: { value: '11111111-1111-4111-8111-111111111111' },
    });
    fireEvent.change(screen.getByLabelText('Evidence Cutoff'), {
      target: { value: '2026-08-28T18:00' },
    });
    fireEvent.change(screen.getByLabelText('Conclusion'), { target: { value: 'SUPPORTS' } });
    fireEvent.change(screen.getByLabelText('Metrics (JSON)'), {
      target: { value: '{"expectancy_delta":0.2}' },
    });
    fireEvent.change(screen.getByLabelText('Notes'), { target: { value: 'Stable' } });
    fireEvent.click(screen.getByRole('button', { name: 'Proposal retrospektiv validieren' }));

    await waitFor(() => expect(mocks.create).toHaveBeenCalledOnce());
    expect(await screen.findByText('Retrospektiv validiert')).toBeInTheDocument();
  });
});
