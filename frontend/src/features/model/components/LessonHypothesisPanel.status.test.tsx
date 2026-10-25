import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { LessonHypothesisPanel } from './LessonHypothesisPanel';
import type { LessonHypothesis } from '../types/lessonHypothesis';

const mocks = vi.hoisted(() => ({
  hypotheses: { listForLessonVersion: vi.fn(), createFromLessonVersion: vi.fn() },
  proposals: {
    listForHypothesis: vi.fn(),
    listModels: vi.fn(),
    listVersions: vi.fn(),
    create: vi.fn(),
  },
  validations: { listForProposal: vi.fn(), create: vi.fn() },
  approvals: { getForProposal: vi.fn(), approve: vi.fn() },
}));

vi.mock('../services/lessonHypothesisClient', () => ({ lessonHypothesisClient: mocks.hypotheses }));
vi.mock('../services/hypothesisProposalClient', () => ({
  hypothesisProposalClient: mocks.proposals,
}));
vi.mock('../services/proposalValidationClient', () => ({
  proposalValidationClient: mocks.validations,
}));
vi.mock('../services/proposalApprovalClient', () => ({ proposalApprovalClient: mocks.approvals }));
vi.mock('./RuntimeActivationPanel', () => ({
  RuntimeActivationPanel: () => <div>Activation readback</div>,
}));

const hypothesis: LessonHypothesis = {
  id: 'hypothesis-1',
  title: 'Synthetic L1 hypothesis',
  statement: 'Explicit synthetic steering only.',
  status: 'OPEN',
  source_lesson_version_id: 'lesson-version-1',
  created_at: '2026-10-25T05:00:00Z',
  created_by: 'actor-1',
};
const definition = {
  schema: 'TOP_DOWN_CANDIDATE/2.0',
  direction: 'LONG',
  market_context_allowed: ['FAVORABLE', 'CAUTIOUS'],
};
const base = {
  id: 'version-a',
  model_id: 'model-1',
  version: 1,
  status: 'APPROVED',
  definition,
  change_summary: 'Synthetic base',
  created_at: '2026-10-25T05:00:00Z',
  created_by: 'actor-1',
  previous_version_id: null,
};
const proposal = {
  id: 'proposal-1',
  model_id: 'model-1',
  base_model_version_id: 'version-a',
  hypothesis_id: hypothesis.id,
  status: 'DRAFT',
  proposed_definition: { ...definition, market_context_allowed: ['FAVORABLE'] },
  rationale: 'Synthetic steering',
  created_at: '2026-10-25T05:01:00Z',
  created_by: 'actor-1',
};
const validation = {
  id: 'validation-1',
  proposal_id: proposal.id,
  evidence_ids: ['evidence-1'],
  evidence_cutoff_at: '2026-10-25T05:02:00Z',
  conclusion: 'INCONCLUSIVE',
  metrics: {},
  notes: 'Synthetic only.',
  created_at: '2026-10-25T05:02:00Z',
  created_by: 'actor-1',
};
const approval = {
  model_version: { ...base, id: 'version-b', version: 2, previous_version_id: base.id },
  approval: {
    id: 'approval-1',
    proposal_id: proposal.id,
    model_version_id: 'version-b',
    approved_at: '2026-10-25T05:03:00Z',
    approved_by: 'actor-1',
    correlation_id: null,
  },
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

async function createProposal() {
  fireEvent.change(await screen.findByLabelText('Governed Model'), {
    target: { value: 'model-1' },
  });
  await waitFor(() => expect(screen.getByLabelText('APPROVED Base-Version')).toHaveValue(base.id));
  fireEvent.click(screen.getByLabelText('FAVORABLE only'));
  fireEvent.change(screen.getByLabelText('Rationale'), { target: { value: proposal.rationale } });
  fireEvent.click(screen.getByRole('button', { name: 'ModelChangeProposal als DRAFT anlegen' }));
  await screen.findByText('ModelChangeProposal vorhanden');
}

async function approveProposal() {
  fireEvent.click(await screen.findByRole('button', { name: 'VALIDATED Proposal approven' }));
  await screen.findByText('Proposal approved');
}

describe('Lesson hypothesis owner status after explicit child commands', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocks.hypotheses.listForLessonVersion.mockResolvedValue([hypothesis]);
    mocks.proposals.listForHypothesis.mockResolvedValue([]);
    mocks.proposals.listModels.mockResolvedValue([
      { id: 'model-1', model_key: 'TOP_DOWN_CANDIDATE', name: 'Candidate', purpose: 'Synthetic' },
    ]);
    mocks.proposals.listVersions.mockResolvedValue([base]);
    mocks.proposals.create.mockResolvedValue(proposal);
    mocks.validations.listForProposal.mockResolvedValue([]);
    mocks.validations.create.mockResolvedValue(validation);
    mocks.approvals.getForProposal.mockResolvedValue(null);
    mocks.approvals.approve.mockResolvedValue(approval);
  });

  it('reads PROPOSED from the owner after creation and retains the confirmed proposal while reading', async () => {
    const readback = deferred<LessonHypothesis[]>();
    mocks.hypotheses.listForLessonVersion
      .mockResolvedValueOnce([hypothesis])
      .mockReturnValueOnce(readback.promise);
    render(<LessonHypothesisPanel lessonVersionId="lesson-version-1" />);
    expect(await screen.findByText('OPEN', { exact: true })).toBeInTheDocument();

    await createProposal();

    expect(mocks.hypotheses.listForLessonVersion).toHaveBeenCalledTimes(2);
    expect(mocks.hypotheses.listForLessonVersion).toHaveBeenLastCalledWith(
      'lesson-version-1',
      expect.any(AbortSignal),
    );
    expect(screen.queryByText('OPEN', { exact: true })).toBeNull();
    expect(screen.getByText('Status wird geprüft …')).toBeInTheDocument();
    expect(screen.getByText('ModelChangeProposal vorhanden')).toBeInTheDocument();
    await act(async () => {
      readback.resolve([{ ...hypothesis, status: 'PROPOSED' }]);
      await readback.promise;
    });

    expect(screen.getByText('PROPOSED', { exact: true })).toBeInTheDocument();
    expect(mocks.proposals.create).toHaveBeenCalledTimes(1);
    expect(mocks.validations.create).not.toHaveBeenCalled();
    expect(mocks.approvals.approve).not.toHaveBeenCalled();
  });

  it('reads CLOSED from the owner after approval and retains the explicit approval readback', async () => {
    const readback = deferred<LessonHypothesis[]>();
    mocks.hypotheses.listForLessonVersion
      .mockResolvedValueOnce([{ ...hypothesis, status: 'PROPOSED' }])
      .mockReturnValueOnce(readback.promise);
    mocks.proposals.listForHypothesis.mockResolvedValue([{ ...proposal, status: 'VALIDATED' }]);
    mocks.validations.listForProposal.mockResolvedValue([validation]);
    render(<LessonHypothesisPanel lessonVersionId="lesson-version-1" />);

    await approveProposal();

    expect(mocks.hypotheses.listForLessonVersion).toHaveBeenCalledTimes(2);
    expect(screen.queryByText('PROPOSED', { exact: true })).toBeNull();
    expect(screen.getByText('Status wird geprüft …')).toBeInTheDocument();
    expect(screen.getByText('Proposal approved')).toBeInTheDocument();
    await act(async () => {
      readback.resolve([{ ...hypothesis, status: 'CLOSED' }]);
      await readback.promise;
    });

    expect(screen.getByText('CLOSED', { exact: true })).toBeInTheDocument();
    expect(mocks.approvals.approve).toHaveBeenCalledTimes(1);
    expect(mocks.proposals.create).not.toHaveBeenCalled();
  });

  it('marks a failed status read as unverified and retries only the read on explicit request', async () => {
    mocks.hypotheses.listForLessonVersion
      .mockResolvedValueOnce([hypothesis])
      .mockRejectedValueOnce(new Error('status read unavailable'))
      .mockResolvedValueOnce([{ ...hypothesis, status: 'PROPOSED' }]);
    render(<LessonHypothesisPanel lessonVersionId="lesson-version-1" />);
    await createProposal();

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Status nicht verifiziert')).toBeInTheDocument();
    expect(screen.queryByText('OPEN', { exact: true })).toBeNull();
    expect(screen.getByText('ModelChangeProposal vorhanden')).toBeInTheDocument();
    expect(mocks.proposals.create).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Hypothesenstand neu laden' }));

    expect(await screen.findByText('PROPOSED', { exact: true })).toBeInTheDocument();
    expect(mocks.hypotheses.listForLessonVersion).toHaveBeenCalledTimes(3);
    expect(mocks.proposals.create).toHaveBeenCalledTimes(1);
    expect(mocks.approvals.approve).not.toHaveBeenCalled();
  });

  it('ignores a superseded proposal read that settles after the approval owner read', async () => {
    const proposalRead = deferred<LessonHypothesis[]>();
    const approvalRead = deferred<LessonHypothesis[]>();
    mocks.hypotheses.listForLessonVersion
      .mockResolvedValueOnce([hypothesis])
      .mockReturnValueOnce(proposalRead.promise)
      .mockReturnValueOnce(approvalRead.promise);
    render(<LessonHypothesisPanel lessonVersionId="lesson-version-1" />);
    await createProposal();
    expect(mocks.hypotheses.listForLessonVersion).toHaveBeenCalledTimes(2);
    const proposalSignal = mocks.hypotheses.listForLessonVersion.mock.calls[1][1] as AbortSignal;
    fireEvent.change(await screen.findByLabelText('LearningEvidence IDs'), {
      target: { value: 'evidence-1' },
    });
    fireEvent.change(screen.getByLabelText('Evidence Cutoff'), {
      target: { value: '2026-10-25T05:02' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Proposal retrospektiv validieren' }));
    await approveProposal();

    expect(mocks.hypotheses.listForLessonVersion).toHaveBeenCalledTimes(3);
    expect(proposalSignal.aborted).toBe(true);
    await act(async () => {
      approvalRead.resolve([{ ...hypothesis, status: 'CLOSED' }]);
      await approvalRead.promise;
    });
    expect(screen.getByText('CLOSED', { exact: true })).toBeInTheDocument();
    await act(async () => {
      proposalRead.resolve([{ ...hypothesis, status: 'PROPOSED' }]);
      await proposalRead.promise;
    });

    expect(screen.getByText('CLOSED', { exact: true })).toBeInTheDocument();
    expect(screen.queryByText('PROPOSED', { exact: true })).toBeNull();
    expect(mocks.proposals.create).toHaveBeenCalledTimes(1);
    expect(mocks.validations.create).toHaveBeenCalledTimes(1);
    expect(mocks.approvals.approve).toHaveBeenCalledTimes(1);
  });

  it('ignores an old L1 status response after L1 to L2 to L1 remounts', async () => {
    const oldRead = deferred<LessonHypothesis[]>();
    mocks.hypotheses.listForLessonVersion
      .mockResolvedValueOnce([hypothesis])
      .mockReturnValueOnce(oldRead.promise)
      .mockResolvedValueOnce([
        {
          ...hypothesis,
          id: 'hypothesis-2',
          title: 'L2 hypothesis',
          source_lesson_version_id: 'lesson-version-2',
        },
      ])
      .mockResolvedValueOnce([{ ...hypothesis, status: 'CLOSED' }]);
    const view = render(<LessonHypothesisPanel lessonVersionId="lesson-version-1" />);
    await createProposal();
    expect(mocks.hypotheses.listForLessonVersion).toHaveBeenCalledTimes(2);
    const oldSignal = mocks.hypotheses.listForLessonVersion.mock.calls[1][1] as AbortSignal;

    view.rerender(<LessonHypothesisPanel lessonVersionId="lesson-version-2" />);
    await screen.findByRole('heading', { name: 'L2 hypothesis' });
    view.rerender(<LessonHypothesisPanel lessonVersionId="lesson-version-1" />);
    expect(await screen.findByText('CLOSED', { exact: true })).toBeInTheDocument();
    expect(oldSignal.aborted).toBe(true);
    await act(async () => {
      oldRead.resolve([{ ...hypothesis, status: 'PROPOSED' }]);
      await oldRead.promise;
    });

    expect(screen.getByText('CLOSED', { exact: true })).toBeInTheDocument();
    expect(screen.queryByText('PROPOSED', { exact: true })).toBeNull();
    expect(mocks.hypotheses.listForLessonVersion).toHaveBeenCalledTimes(4);
    expect(mocks.proposals.create).toHaveBeenCalledTimes(1);
  });

  it.each([
    [
      'foreign lesson',
      [{ ...hypothesis, status: 'CLOSED', source_lesson_version_id: 'lesson-version-2' }],
    ],
    ['missing confirmed hypothesis', []],
  ])(
    'rejects a %s in the status read without dropping the confirmed proposal',
    async (_label, response) => {
      mocks.hypotheses.listForLessonVersion
        .mockResolvedValueOnce([hypothesis])
        .mockResolvedValueOnce(response);
      render(<LessonHypothesisPanel lessonVersionId="lesson-version-1" />);
      await createProposal();

      expect(await screen.findByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Status nicht verifiziert')).toBeInTheDocument();
      expect(screen.getByText('ModelChangeProposal vorhanden')).toBeInTheDocument();
      expect(screen.queryByText('OPEN', { exact: true })).toBeNull();
      expect(screen.queryByText('CLOSED', { exact: true })).toBeNull();
      expect(screen.queryByRole('button', { name: 'Hypothese für FT-013 anlegen' })).toBeNull();
      expect(mocks.proposals.create).toHaveBeenCalledTimes(1);
    },
  );
});
