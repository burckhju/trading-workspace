import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LessonHypothesisPanel } from './LessonHypothesisPanel';
import { ProposalValidationPanel } from './ProposalValidationPanel';
import { ProposalApprovalPanel } from './ProposalApprovalPanel';

const mocks = vi.hoisted(() => ({
  listForLessonVersion: vi.fn(),
  createFromLessonVersion: vi.fn(),
  listForProposal: vi.fn(),
  create: vi.fn(),
  getForProposal: vi.fn(),
  approve: vi.fn(),
}));
vi.mock('../services/lessonHypothesisClient', () => ({ lessonHypothesisClient: mocks }));
vi.mock('../services/proposalValidationClient', () => ({ proposalValidationClient: mocks }));
vi.mock('../services/proposalApprovalClient', () => ({ proposalApprovalClient: mocks }));
vi.mock('./HypothesisProposalPanel', () => ({ HypothesisProposalPanel: () => null }));
vi.mock('./RuntimeActivationPanel', () => ({ RuntimeActivationPanel: () => null }));

describe('explicit Governance command submission', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listForLessonVersion.mockResolvedValue([]);
    mocks.listForProposal.mockResolvedValue([]);
    mocks.getForProposal.mockResolvedValue(null);
    mocks.createFromLessonVersion.mockReturnValue(new Promise(() => undefined));
    mocks.create.mockReturnValue(new Promise(() => undefined));
    mocks.approve.mockReturnValue(new Promise(() => undefined));
  });

  it('sends one hypothesis for two synchronous form events', async () => {
    render(<LessonHypothesisPanel lessonVersionId="l1" />);
    const button = await screen.findByRole('button', { name: 'Hypothese für FT-013 anlegen' });
    fireEvent.change(screen.getByLabelText('Titel'), { target: { value: 'Synthetic hypothesis' } });
    fireEvent.change(screen.getByLabelText('Hypothese'), { target: { value: 'Synthetic only' } });
    act(() => {
      fireEvent.submit(button.closest('form')!);
      fireEvent.submit(button.closest('form')!);
    });
    expect(mocks.createFromLessonVersion).toHaveBeenCalledTimes(1);
  });

  it('sends one validation with its exact second and evidence set for two synchronous submits', async () => {
    render(<ProposalValidationPanel proposalId="p1" proposalStatus="DRAFT" />);
    const button = await screen.findByRole('button', { name: 'Proposal retrospektiv validieren' });
    fireEvent.change(screen.getByLabelText('LearningEvidence IDs'), { target: { value: 'e1' } });
    const cutoff = screen.getByLabelText<HTMLInputElement>('Evidence Cutoff');
    fireEvent.change(cutoff, { target: { value: '2026-10-25T09:00:37.123' } });
    expect(cutoff.validity.stepMismatch).toBe(false);
    act(() => {
      fireEvent.submit(button.closest('form')!);
      fireEvent.submit(button.closest('form')!);
    });
    expect(mocks.create).toHaveBeenCalledTimes(1);
    expect(mocks.create).toHaveBeenCalledWith('p1', {
      evidence_ids: ['e1'],
      evidence_cutoff_at: new Date('2026-10-25T09:00:37.123').toISOString(),
      conclusion: 'INCONCLUSIVE',
      metrics: {},
      notes: null,
    });
  });

  it('sends one approval for two synchronous clicks', async () => {
    render(<ProposalApprovalPanel proposalId="p1" proposalStatus="VALIDATED" />);
    const button = await screen.findByRole('button', { name: 'VALIDATED Proposal approven' });
    act(() => {
      fireEvent.click(button);
      fireEvent.click(button);
    });
    expect(mocks.approve).toHaveBeenCalledTimes(1);
  });

  it('keeps a failed validation read visible for an already approved proposal', async () => {
    mocks.listForProposal.mockRejectedValue(new Error('validation read unavailable'));
    render(<ProposalValidationPanel proposalId="p1" proposalStatus="APPROVED" />);
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(mocks.approve).not.toHaveBeenCalled();
  });

  it('keeps a failed approval read visible for an already approved proposal', async () => {
    mocks.getForProposal.mockRejectedValue(new Error('approval read unavailable'));
    render(<ProposalApprovalPanel proposalId="p1" proposalStatus="APPROVED" />);
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(mocks.approve).not.toHaveBeenCalled();
  });
});
