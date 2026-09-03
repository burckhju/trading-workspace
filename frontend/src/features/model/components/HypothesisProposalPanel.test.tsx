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
vi.mock('./ProposalValidationPanel', () => ({
  ProposalValidationPanel: ({ proposalId }: { proposalId: string }) => (
    <div>Validation workflow {proposalId}</div>
  ),
}));

const candidateModel = {
  id: 'model-1',
  model_key: 'TOP_DOWN_CANDIDATE',
  name: 'Candidate',
  purpose: 'Qualify candidates',
  created_at: '2026-09-01T00:00:00Z',
  created_by: 'actor-1',
};
function version(id: string, number: number, definition: Record<string, unknown>) {
  return {
    id,
    model_id: 'model-1',
    version: number,
    status: 'APPROVED',
    definition,
    change_summary: 'Approved',
    created_at: '2026-09-01T00:00:00Z',
    created_by: 'actor-1',
    previous_version_id: null,
  };
}
const v1 = {
  schema: 'TOP_DOWN_CANDIDATE/1.0',
  direction: 'LONG',
  market_context_allowed: ['FAVORABLE', 'CAUTIOUS'],
};
const permissiveV2 = {
  schema: 'TOP_DOWN_CANDIDATE/2.0',
  direction: 'LONG',
  market_context_allowed: ['FAVORABLE', 'CAUTIOUS'],
};
const strictV2 = {
  schema: 'TOP_DOWN_CANDIDATE/2.0',
  direction: 'LONG',
  market_context_allowed: ['FAVORABLE'],
};

async function selectCandidate() {
  fireEvent.change(screen.getByLabelText('Governed Model'), {
    target: { value: 'model-1' },
  });
  await waitFor(() =>
    expect(screen.getByLabelText('APPROVED Base-Version')).toHaveValue('version-1'),
  );
}

describe('HypothesisProposalPanel FT-020', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listForHypothesis.mockResolvedValue([]);
    mocks.listModels.mockResolvedValue([candidateModel]);
    mocks.listVersions.mockResolvedValue([version('version-1', 1, permissiveV2)]);
  });

  it('renders V2 current policy without Candidate JSON editing', async () => {
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    await selectCandidate();
    expect(
      screen.getByText('Candidate market context policy: FAVORABLE + CAUTIOUS'),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText('Proposed Definition (JSON)')).toBeNull();
    expect(screen.getByText('Keine Änderung.')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'ModelChangeProposal als DRAFT anlegen' }),
    ).toBeDisabled();
  });

  it('derives an explicit V2 strict proposal from immutable V1', async () => {
    mocks.listVersions.mockResolvedValue([version('version-1', 1, v1)]);
    mocks.create.mockResolvedValue({
      id: 'proposal-1',
      model_id: 'model-1',
      base_model_version_id: 'version-1',
      hypothesis_id: 'hypothesis-1',
      status: 'DRAFT',
      proposed_definition: strictV2,
      rationale: 'Tighten policy',
      created_at: '2026-09-03T00:00:00Z',
      created_by: 'actor-1',
    });
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    await selectCandidate();
    expect(screen.getByText(/Legacy 1.0 bleibt unverändert/)).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('FAVORABLE only'));
    expect(screen.getByText(/CAUTIOUS market context will no longer satisfy/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Rationale'), {
      target: { value: 'Tighten policy' },
    });
    fireEvent.click(
      screen.getByRole('button', { name: 'ModelChangeProposal als DRAFT anlegen' }),
    );
    await waitFor(() =>
      expect(mocks.create).toHaveBeenCalledWith({
        model_id: 'model-1',
        base_model_version_id: 'version-1',
        hypothesis_id: 'hypothesis-1',
        proposed_definition: strictV2,
        rationale: 'Tighten policy',
      }),
    );
  });

  it('previews strict to permissive impact', async () => {
    mocks.listVersions.mockResolvedValue([version('version-1', 2, strictV2)]);
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    await selectCandidate();
    fireEvent.click(screen.getByLabelText('FAVORABLE + CAUTIOUS'));
    expect(screen.getByText(/CAUTIOUS market context will become eligible/)).toBeInTheDocument();
  });

  it('fails closed for invalid or unknown Candidate definitions', async () => {
    mocks.listVersions.mockResolvedValue([
      version('version-1', 2, { schema: 'TOP_DOWN_CANDIDATE/2.0', direction: 'LONG' }),
    ]);
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    await selectCandidate();
    expect(screen.getByRole('alert')).toHaveTextContent('nicht vollständig verstanden');
    expect(screen.queryByLabelText('FAVORABLE only')).toBeNull();
    expect(
      screen.getByRole('button', { name: 'ModelChangeProposal als DRAFT anlegen' }),
    ).toBeDisabled();
  });

  it('rejects unknown definition content instead of lossy round-tripping', async () => {
    mocks.listVersions.mockResolvedValue([
      version('version-1', 2, { ...permissiveV2, future_rule: true }),
    ]);
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    await selectCandidate();
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(mocks.create).not.toHaveBeenCalled();
  });
});
