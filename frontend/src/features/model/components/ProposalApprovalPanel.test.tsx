import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ProposalApprovalPanel } from './ProposalApprovalPanel';

const mocks = vi.hoisted(() => ({
  getForProposal: vi.fn(),
  approve: vi.fn(),
}));

vi.mock('../services/proposalApprovalClient', () => ({
  proposalApprovalClient: mocks,
}));

describe('ProposalApprovalPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getForProposal.mockResolvedValue(null);
  });

  it('offers approval only for VALIDATED proposals', async () => {
    render(<ProposalApprovalPanel proposalId="proposal-1" proposalStatus="VALIDATED" />);

    expect(await screen.findByText('Proposal freigeben')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'VALIDATED Proposal approven' })).toBeInTheDocument();
  });

  it('approves explicitly and shows the immutable model version', async () => {
    mocks.approve.mockResolvedValue({
      model_version: {
        id: 'version-2',
        model_id: 'model-1',
        version: 2,
        status: 'APPROVED',
        definition: { threshold: 2 },
        change_summary: 'Tighten selectivity',
        created_at: '2026-08-28T19:00:00Z',
        created_by: 'actor-1',
        previous_version_id: 'version-1',
      },
      approval: {
        id: 'approval-1',
        proposal_id: 'proposal-1',
        model_version_id: 'version-2',
        approved_at: '2026-08-28T19:00:00Z',
        approved_by: 'actor-1',
        correlation_id: 'corr-1',
      },
    });

    render(<ProposalApprovalPanel proposalId="proposal-1" proposalStatus="VALIDATED" />);
    await screen.findByText('Proposal freigeben');
    fireEvent.change(screen.getByLabelText('Correlation ID (optional)'), {
      target: { value: 'corr-1' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'VALIDATED Proposal approven' }));

    await waitFor(() => expect(mocks.approve).toHaveBeenCalledWith('proposal-1', 'corr-1'));
    expect(await screen.findByText('Proposal approved')).toBeInTheDocument();
    expect(screen.getByText('Version 2')).toBeInTheDocument();
  });

  it('shows existing approval and suppresses duplicate approval', async () => {
    mocks.getForProposal.mockResolvedValue({
      model_version: {
        id: 'version-2',
        model_id: 'model-1',
        version: 2,
        status: 'APPROVED',
        definition: { threshold: 2 },
        change_summary: 'Tighten selectivity',
        created_at: '2026-08-28T19:00:00Z',
        created_by: 'actor-1',
        previous_version_id: 'version-1',
      },
      approval: {
        id: 'approval-1',
        proposal_id: 'proposal-1',
        model_version_id: 'version-2',
        approved_at: '2026-08-28T19:00:00Z',
        approved_by: 'actor-1',
        correlation_id: null,
      },
    });

    render(<ProposalApprovalPanel proposalId="proposal-1" proposalStatus="APPROVED" />);

    expect(await screen.findByText('Proposal approved')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'VALIDATED Proposal approven' })).toBeNull();
  });
});
