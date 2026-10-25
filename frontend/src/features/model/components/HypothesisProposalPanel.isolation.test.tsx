import { StrictMode } from 'react';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { HypothesisProposalPanel } from './HypothesisProposalPanel';
import { LessonHypothesisPanel } from './LessonHypothesisPanel';
import type {
  CreateModelChangeProposalInput,
  GovernedModelSummary,
  GovernedModelVersion,
  ModelChangeProposalSummary,
} from '../types/hypothesisProposal';
import type { LessonHypothesis } from '../types/lessonHypothesis';

const mocks = vi.hoisted(() => ({
  listForHypothesis: vi.fn(),
  listModels: vi.fn(),
  listVersions: vi.fn(),
  create: vi.fn(),
  listForLessonVersion: vi.fn(),
  createFromLessonVersion: vi.fn(),
}));

vi.mock('../services/hypothesisProposalClient', () => ({ hypothesisProposalClient: mocks }));
vi.mock('../services/lessonHypothesisClient', () => ({ lessonHypothesisClient: mocks }));
vi.mock('./ProposalValidationPanel', () => ({
  ProposalValidationPanel: ({ proposalId }: { proposalId: string }) => (
    <div>Validation workflow {proposalId}</div>
  ),
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

const models: GovernedModelSummary[] = ['alpha', 'beta'].map((name) => ({
  id: `model-${name}`,
  model_key: `SYNTHETIC_${name.toUpperCase()}`,
  name,
  purpose: 'Synthetic proposal isolation fixture',
  created_at: '2026-10-24T08:00:00Z',
  created_by: 'synthetic-actor',
}));

function version(modelId: string, id = `base-${modelId}`, number = 1): GovernedModelVersion {
  return {
    id,
    model_id: modelId,
    version: number,
    status: 'APPROVED',
    definition: { schema: 'SYNTHETIC/1.0', criterion: id },
    change_summary: 'Synthetic approved base',
    created_at: '2026-10-24T08:00:00Z',
    created_by: 'synthetic-actor',
    previous_version_id: null,
  };
}

function proposal(
  hypothesisId = 'hypothesis-1',
  overrides: Partial<ModelChangeProposalSummary> = {},
): ModelChangeProposalSummary {
  return {
    id: `proposal-${hypothesisId}`,
    model_id: 'model-alpha',
    base_model_version_id: 'base-model-alpha',
    hypothesis_id: hypothesisId,
    status: 'DRAFT',
    proposed_definition: { schema: 'SYNTHETIC/1.0', criterion: 'changed' },
    rationale: `Saved for ${hypothesisId}`,
    created_at: '2026-10-24T08:00:00Z',
    created_by: 'synthetic-actor',
    ...overrides,
  };
}

function hypothesis(id: string, lessonVersionId: string): LessonHypothesis {
  return {
    id,
    title: `Hypothesis ${id}`,
    statement: `Synthetic statement ${id}`,
    status: 'OPEN',
    source_lesson_version_id: lessonVersionId,
    created_at: '2026-10-24T08:00:00Z',
    created_by: 'synthetic-actor',
  };
}

async function selectModel(modelId = 'model-alpha', baseId = `base-${modelId}`) {
  fireEvent.change(await screen.findByLabelText('Governed Model'), {
    target: { value: modelId },
  });
  await waitFor(() => expect(screen.getByLabelText('APPROVED Base-Version')).toHaveValue(baseId));
}

function rationale(value: string) {
  fireEvent.change(screen.getByLabelText('Rationale'), { target: { value } });
}

function form() {
  const element = screen.getByLabelText('Rationale').closest('form');
  if (!element) throw new Error('Expected proposal form');
  return element;
}

function submit() {
  // Bypass the disabled button and browser validation: the event handler owns the guard.
  fireEvent.submit(form());
}

async function resolve<T>(pending: ReturnType<typeof deferred<T>>, value: T) {
  await act(async () => {
    pending.resolve(value);
    await Promise.resolve();
  });
}

async function reject<T>(pending: ReturnType<typeof deferred<T>>) {
  await act(async () => {
    pending.reject(new Error('Synthetic request failure'));
    await Promise.resolve();
  });
}

describe('HypothesisProposalPanel context and submission isolation', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocks.listForHypothesis.mockResolvedValue([]);
    mocks.listModels.mockResolvedValue(models);
    mocks.listVersions.mockImplementation((modelId: string) => Promise.resolve([version(modelId)]));
    mocks.create.mockReturnValue(new Promise<ModelChangeProposalSummary>(() => {}));
  });

  it('blocks direct submit during a model switch and then snapshots only the loaded new base', async () => {
    const beta = deferred<GovernedModelVersion[]>();
    mocks.listVersions.mockImplementation((id: string) =>
      id === 'model-beta' ? beta.promise : Promise.resolve([version(id)]),
    );
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    await selectModel();
    rationale('Alpha draft');
    fireEvent.change(screen.getByLabelText('Governed Model'), { target: { value: 'model-beta' } });
    submit();
    expect(mocks.create).not.toHaveBeenCalled();
    expect(screen.getByLabelText('APPROVED Base-Version')).toHaveValue('');
    expect(screen.getByLabelText('Proposed Definition (JSON)')).toHaveValue('');
    expect(screen.getByLabelText('Rationale')).toHaveValue('');
    expect(screen.getByRole('button', { name: /als DRAFT anlegen/ })).toBeDisabled();

    await resolve(beta, [version('model-beta')]);
    rationale('Beta intent');
    fireEvent.change(screen.getByLabelText('Proposed Definition (JSON)'), {
      target: { value: '{"schema":"SYNTHETIC/1.0","criterion":"beta change"}' },
    });
    submit();
    expect(mocks.create).toHaveBeenCalledTimes(1);
    expect(mocks.create).toHaveBeenCalledWith({
      hypothesis_id: 'hypothesis-1',
      model_id: 'model-beta',
      base_model_version_id: 'base-model-beta',
      proposed_definition: { schema: 'SYNTHETIC/1.0', criterion: 'beta change' },
      rationale: 'Beta intent',
    });
  });

  it.each(['switch', 'round trip'] as const)(
    'invalidates the old base synchronously for a model %s and submit before another render',
    async (change) => {
      const currentVersions = deferred<GovernedModelVersion[]>();
      render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
      await selectModel();
      rationale('Bound to the original model visit');
      mocks.listVersions.mockReturnValueOnce(currentVersions.promise);
      const modelSelect = screen.getByLabelText('Governed Model');
      const proposalForm = form();
      act(() => {
        fireEvent.change(modelSelect, { target: { value: 'model-beta' } });
        if (change === 'round trip') {
          fireEvent.change(modelSelect, { target: { value: 'model-alpha' } });
        }
        fireEvent.submit(proposalForm);
      });
      expect(mocks.create).not.toHaveBeenCalled();
      expect(screen.getByLabelText('APPROVED Base-Version')).toHaveValue('');
      expect(screen.getByLabelText('Rationale')).toHaveValue('');
      await resolve(currentVersions, [version(change === 'switch' ? 'model-beta' : 'model-alpha')]);
    },
  );

  it('ignores an old successful version read after the new model is ready', async () => {
    const alpha = deferred<GovernedModelVersion[]>();
    mocks.listVersions.mockImplementation((id: string) =>
      id === 'model-alpha' ? alpha.promise : Promise.resolve([version(id)]),
    );
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    fireEvent.change(await screen.findByLabelText('Governed Model'), {
      target: { value: 'model-alpha' },
    });
    await selectModel('model-beta');
    rationale('Keep beta input');
    await resolve(alpha, [version('model-alpha')]);
    expect(screen.getByLabelText('APPROVED Base-Version')).toHaveValue('base-model-beta');
    expect(screen.getByLabelText('Proposed Definition (JSON)')).toHaveValue(
      JSON.stringify(version('model-beta').definition, null, 2),
    );
    expect(screen.getByLabelText('Rationale')).toHaveValue('Keep beta input');
    submit();
    expect(mocks.create).toHaveBeenCalledWith(
      expect.objectContaining({ model_id: 'model-beta', base_model_version_id: 'base-model-beta' }),
    );
  });

  it('distinguishes M1 -> M2 -> M1 visits even when the model ID is equal again', async () => {
    const firstAlpha = deferred<GovernedModelVersion[]>();
    const beta = deferred<GovernedModelVersion[]>();
    const currentAlpha = deferred<GovernedModelVersion[]>();
    mocks.listVersions
      .mockReturnValueOnce(firstAlpha.promise)
      .mockReturnValueOnce(beta.promise)
      .mockReturnValueOnce(currentAlpha.promise);
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    const modelSelect = await screen.findByLabelText('Governed Model');
    fireEvent.change(modelSelect, { target: { value: 'model-alpha' } });
    fireEvent.change(modelSelect, { target: { value: 'model-beta' } });
    fireEvent.change(modelSelect, { target: { value: 'model-alpha' } });
    await resolve(currentAlpha, [version('model-alpha', 'current-alpha', 2)]);
    rationale('Current visit');
    await resolve(firstAlpha, [version('model-alpha', 'old-alpha')]);
    await resolve(beta, [version('model-beta')]);
    expect(screen.getByLabelText('APPROVED Base-Version')).toHaveValue('current-alpha');
    expect(screen.getByLabelText('Rationale')).toHaveValue('Current visit');
    submit();
    expect(mocks.create).toHaveBeenCalledWith(
      expect.objectContaining({ model_id: 'model-alpha', base_model_version_id: 'current-alpha' }),
    );
  });

  it('keeps a pending current model locked when an old read rejects and finishes', async () => {
    const alpha = deferred<GovernedModelVersion[]>();
    const beta = deferred<GovernedModelVersion[]>();
    mocks.listVersions.mockReturnValueOnce(alpha.promise).mockReturnValueOnce(beta.promise);
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    const modelSelect = await screen.findByLabelText('Governed Model');
    fireEvent.change(modelSelect, { target: { value: 'model-alpha' } });
    fireEvent.change(modelSelect, { target: { value: 'model-beta' } });
    await reject(alpha);
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.getByLabelText('APPROVED Base-Version')).toBeDisabled();
    submit();
    expect(mocks.create).not.toHaveBeenCalled();
    await resolve(beta, [version('model-beta')]);
    expect(screen.getByLabelText('APPROVED Base-Version')).toHaveValue('base-model-beta');
  });

  it('rejects an already fulfilled promise whose callback runs after the model changed', async () => {
    const alpha = deferred<GovernedModelVersion[]>();
    const beta = deferred<GovernedModelVersion[]>();
    mocks.listVersions.mockReturnValueOnce(alpha.promise).mockReturnValueOnce(beta.promise);
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    const modelSelect = await screen.findByLabelText('Governed Model');
    fireEvent.change(modelSelect, { target: { value: 'model-alpha' } });
    act(() => {
      alpha.resolve([version('model-alpha')]);
      fireEvent.change(modelSelect, { target: { value: 'model-beta' } });
    });
    await act(async () => {});
    expect(screen.getByLabelText('APPROVED Base-Version')).toHaveValue('');
    fireEvent.change(screen.getByLabelText('Proposed Definition (JSON)'), {
      target: { value: '{}' },
    });
    submit();
    expect(mocks.create).not.toHaveBeenCalled();
    await resolve(beta, [version('model-beta')]);
  });

  it('blocks the handler after a current version-load failure rather than reusing the old base', async () => {
    const beta = deferred<GovernedModelVersion[]>();
    mocks.listVersions.mockImplementation((id: string) =>
      id === 'model-beta' ? beta.promise : Promise.resolve([version(id)]),
    );
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    await selectModel();
    rationale('Old base must not be reused');
    fireEvent.change(screen.getByLabelText('Governed Model'), { target: { value: 'model-beta' } });
    await reject(beta);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Proposed Definition (JSON)'), {
      target: { value: '{}' },
    });
    submit();
    expect(mocks.create).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /als DRAFT anlegen/ })).toBeDisabled();
  });

  it.each([
    ['empty', []],
    ['missing base identity', [version('model-alpha', '')]],
    ['unapproved', [{ ...version('model-alpha'), status: 'DRAFT' }]],
    ['foreign model', [version('model-beta')]],
    ['mixed model identities', [version('model-alpha'), version('model-beta')]],
  ])('rejects %s version responses at the handler', async (_name, versions) => {
    mocks.listVersions.mockResolvedValue(versions);
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    fireEvent.change(await screen.findByLabelText('Governed Model'), {
      target: { value: 'model-alpha' },
    });
    await act(async () => {});
    rationale('Invalid base request');
    fireEvent.change(screen.getByLabelText('Proposed Definition (JSON)'), {
      target: { value: '{}' },
    });
    submit();
    expect(mocks.create).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /als DRAFT anlegen/ })).toBeDisabled();
  });

  it('requires a selected approved base even when a programmatic submit bypasses required fields', async () => {
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    await selectModel();
    rationale('Base intentionally cleared');
    fireEvent.change(screen.getByLabelText('APPROVED Base-Version'), { target: { value: '' } });
    fireEvent.change(screen.getByLabelText('Proposed Definition (JSON)'), {
      target: { value: '{}' },
    });
    submit();
    expect(mocks.create).not.toHaveBeenCalled();
  });

  it.each(['', '   '])('requires a nonblank rationale in the handler: %j', async (input) => {
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    await selectModel();
    rationale(input);
    submit();
    expect(mocks.create).not.toHaveBeenCalled();
  });

  it.each(['null', '[]', '{invalid JSON'])(
    'rejects invalid generic definition %j without a POST',
    async (definition) => {
      render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
      await selectModel();
      rationale('Requires an object definition');
      fireEvent.change(screen.getByLabelText('Proposed Definition (JSON)'), {
        target: { value: definition },
      });
      submit();
      expect(mocks.create).not.toHaveBeenCalled();
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByLabelText('Rationale')).toHaveValue('Requires an object definition');
    },
  );

  it('preserves inputs on an equivalent rerender and clears rationale only for a real base/model change', async () => {
    mocks.listVersions.mockImplementation((id: string) =>
      Promise.resolve([version(id, `${id}-base-1`), version(id, `${id}-base-2`, 2)]),
    );
    const view = render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    await selectModel('model-alpha', 'model-alpha-base-2');
    rationale('Deliberate input');
    view.rerender(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    fireEvent.change(screen.getByLabelText('APPROVED Base-Version'), {
      target: { value: 'model-alpha-base-2' },
    });
    expect(screen.getByLabelText('Rationale')).toHaveValue('Deliberate input');
    expect(mocks.listVersions).toHaveBeenCalledTimes(1);
    fireEvent.change(screen.getByLabelText('APPROVED Base-Version'), {
      target: { value: 'model-alpha-base-1' },
    });
    expect(screen.getByLabelText('Rationale')).toHaveValue('');
    rationale('Bound to the older base');
    await selectModel('model-beta', 'model-beta-base-2');
    expect(screen.getByLabelText('Rationale')).toHaveValue('');
  });

  it('permits only one create from two submit events in the same React batch', async () => {
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    await selectModel();
    rationale('One explicit command');
    const proposalForm = form();
    act(() => {
      fireEvent.submit(proposalForm);
      fireEvent.submit(proposalForm);
    });
    expect(mocks.create).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: 'Proposal wird angelegt …' })).toBeDisabled();
  });

  it('locks the submitted draft until its save ends and preserves the snapshot on equivalent rerenders', async () => {
    const save = deferred<ModelChangeProposalSummary>();
    mocks.create.mockReturnValueOnce(save.promise);
    const view = render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    await selectModel();
    rationale('Submitted intent');
    submit();
    view.rerender(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    expect(screen.getByLabelText('Governed Model')).toBeDisabled();
    expect(screen.getByLabelText('APPROVED Base-Version')).toBeDisabled();
    expect(screen.getByLabelText('Proposed Definition (JSON)')).toBeDisabled();
    expect(screen.getByLabelText('Rationale')).toBeDisabled();
    expect(screen.getByLabelText('Rationale')).toHaveValue('Submitted intent');
    submit();
    expect(mocks.create).toHaveBeenCalledTimes(1);
    expect(mocks.create).toHaveBeenCalledWith({
      hypothesis_id: 'hypothesis-1',
      model_id: 'model-alpha',
      base_model_version_id: 'base-model-alpha',
      proposed_definition: version('model-alpha').definition,
      rationale: 'Submitted intent',
    });
    await reject(save);
    expect(screen.getByLabelText('Governed Model')).not.toBeDisabled();
    expect(screen.getByLabelText('Rationale')).toHaveValue('Submitted intent');
  });

  it('retains the exact current draft after a failure and permits an explicit retry', async () => {
    const firstSave = deferred<ModelChangeProposalSummary>();
    const retrySave = deferred<ModelChangeProposalSummary>();
    mocks.create.mockReturnValueOnce(firstSave.promise).mockReturnValueOnce(retrySave.promise);
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    await selectModel();
    rationale('Keep this rationale');
    fireEvent.change(screen.getByLabelText('Proposed Definition (JSON)'), {
      target: { value: '{"criterion":"intentional change"}' },
    });
    submit();
    const snapshot = mocks.create.mock.calls[0][0] as CreateModelChangeProposalInput;
    await reject(firstSave);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByLabelText('Rationale')).toHaveValue('Keep this rationale');
    expect(screen.getByLabelText('Proposed Definition (JSON)')).toHaveValue(
      '{"criterion":"intentional change"}',
    );
    expect(mocks.create).toHaveBeenCalledTimes(1);
    submit();
    expect(mocks.create).toHaveBeenCalledTimes(2);
    expect(mocks.create.mock.calls[1][0]).toEqual(snapshot);
    await resolve(retrySave, proposal('hypothesis-1', snapshot));
    expect(
      await screen.findByText('Validation workflow proposal-hypothesis-1'),
    ).toBeInTheDocument();
  });

  it.each(['model_id', 'base_model_version_id', 'hypothesis_id'] as const)(
    'does not display or hand off a create response with a different %s',
    async (field) => {
      mocks.create.mockResolvedValue(proposal('hypothesis-1', { [field]: 'unexpected-identity' }));
      render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
      await selectModel();
      rationale('Keep on identity failure');
      submit();
      await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
      expect(screen.getByLabelText('Rationale')).toHaveValue('Keep on identity failure');
      expect(screen.queryByText(/Validation workflow/)).toBeNull();
      expect(mocks.create).toHaveBeenCalledTimes(1);
    },
  );

  it('treats a non-DRAFT create response as an error without handing it to the governance panels', async () => {
    mocks.create.mockResolvedValue(proposal('hypothesis-1', { status: 'APPROVED' }));
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    await selectModel();
    rationale('Explicit draft only');
    submit();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByLabelText('Rationale')).toHaveValue('Explicit draft only');
    expect(screen.queryByText(/Validation workflow/)).toBeNull();
    expect(mocks.create).toHaveBeenCalledTimes(1);
  });

  it('does not automatically retry an ambiguous failure and reads the saved draft on explicit return', async () => {
    mocks.create.mockRejectedValue(new Error('Connection closed after server commit'));
    const view = render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    await selectModel();
    rationale('Possibly stored');
    submit();
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(mocks.create).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Rationale')).toHaveValue('Possibly stored');
    view.unmount();
    mocks.listForHypothesis.mockResolvedValue([proposal('hypothesis-1')]);
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    expect(
      await screen.findByText('Validation workflow proposal-hypothesis-1'),
    ).toBeInTheDocument();
    expect(mocks.listForHypothesis).toHaveBeenLastCalledWith(
      'hypothesis-1',
      expect.any(AbortSignal),
    );
    expect(mocks.create).toHaveBeenCalledTimes(1);
  });

  describe('synthetic hypothesis prop changes (separate from the keyed real parent)', () => {
    it('ignores an old hypothesis read after the current context accepts input', async () => {
      const oldRead = deferred<ModelChangeProposalSummary[]>();
      mocks.listForHypothesis.mockImplementation((id: string) =>
        id === 'hypothesis-1' ? oldRead.promise : Promise.resolve([]),
      );
      const view = render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
      view.rerender(<HypothesisProposalPanel hypothesisId="hypothesis-2" />);
      await selectModel();
      rationale('Current H2');
      await resolve(oldRead, [proposal('hypothesis-1')]);
      expect(screen.queryByText('Validation workflow proposal-hypothesis-1')).toBeNull();
      expect(screen.getByLabelText('Rationale')).toHaveValue('Current H2');
      submit();
      expect(mocks.create).toHaveBeenCalledWith(
        expect.objectContaining({ hypothesis_id: 'hypothesis-2' }),
      );
    });

    it('distinguishes H1 -> H2 -> H1 visits instead of accepting the old same-ID read', async () => {
      const oldRead = deferred<ModelChangeProposalSummary[]>();
      mocks.listForHypothesis
        .mockReturnValueOnce(oldRead.promise)
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce([proposal('hypothesis-1')]);
      const view = render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
      view.rerender(<HypothesisProposalPanel hypothesisId="hypothesis-2" />);
      await screen.findByLabelText('Governed Model');
      view.rerender(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
      expect(
        await screen.findByText('Validation workflow proposal-hypothesis-1'),
      ).toBeInTheDocument();
      await resolve(oldRead, []);
      expect(screen.getByText('Validation workflow proposal-hypothesis-1')).toBeInTheDocument();
      expect(screen.queryByLabelText('Governed Model')).toBeNull();
    });

    it.each(['listModels', 'listForHypothesis'] as const)(
      'cannot submit an old form after the current hypothesis %s read failed',
      async (method) => {
        const view = render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
        await selectModel();
        rationale('Old H1 draft');
        mocks[method].mockRejectedValueOnce(new Error('Current context failed'));
        view.rerender(<HypothesisProposalPanel hypothesisId="hypothesis-2" />);
        await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
        const currentForm = screen.queryByLabelText('Rationale')?.closest('form');
        if (currentForm) fireEvent.submit(currentForm);
        expect(mocks.create).not.toHaveBeenCalled();
        expect(screen.queryByText(/Validation workflow/)).toBeNull();
      },
    );

    it.each(['success', 'failure'] as const)(
      'does not let an old save %s or finally overwrite H2 or release its newer save',
      async (outcome) => {
        const oldSave = deferred<ModelChangeProposalSummary>();
        const newSave = deferred<ModelChangeProposalSummary>();
        mocks.create.mockReturnValueOnce(oldSave.promise).mockReturnValueOnce(newSave.promise);
        const view = render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
        await selectModel();
        rationale('Original H1 command');
        submit();
        view.rerender(<HypothesisProposalPanel hypothesisId="hypothesis-2" />);
        await selectModel();
        rationale('New H2 command');
        submit();
        expect(mocks.create).toHaveBeenCalledTimes(2);
        expect(
          mocks.create.mock.calls.map(
            ([input]) => (input as CreateModelChangeProposalInput).hypothesis_id,
          ),
        ).toEqual(['hypothesis-1', 'hypothesis-2']);
        if (outcome === 'success') await resolve(oldSave, proposal('hypothesis-1'));
        else await reject(oldSave);
        expect(screen.queryByText('Validation workflow proposal-hypothesis-1')).toBeNull();
        expect(screen.queryByRole('alert')).toBeNull();
        expect(screen.getByLabelText('Rationale')).toHaveValue('New H2 command');
        expect(screen.getByRole('button', { name: 'Proposal wird angelegt …' })).toBeDisabled();
        submit();
        expect(mocks.create).toHaveBeenCalledTimes(2);
        await resolve(newSave, proposal('hypothesis-2'));
        expect(
          await screen.findByText('Validation workflow proposal-hypothesis-2'),
        ).toBeInTheDocument();
      },
    );
  });

  it('ignores the first StrictMode request even if it succeeds after the current request', async () => {
    const firstRead = deferred<ModelChangeProposalSummary[]>();
    mocks.listForHypothesis.mockReturnValueOnce(firstRead.promise).mockResolvedValueOnce([]);
    render(
      <StrictMode>
        <HypothesisProposalPanel hypothesisId="hypothesis-1" />
      </StrictMode>,
    );
    await selectModel();
    rationale('StrictMode current input');
    expect(mocks.listForHypothesis).toHaveBeenCalledTimes(2);
    await resolve(firstRead, [proposal('hypothesis-1')]);
    expect(screen.queryByText('Validation workflow proposal-hypothesis-1')).toBeNull();
    expect(screen.getByLabelText('Rationale')).toHaveValue('StrictMode current input');
  });

  it('rejects a proposal list that belongs to another hypothesis', async () => {
    mocks.listForHypothesis.mockResolvedValue([proposal('hypothesis-foreign')]);
    render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.queryByText('Validation workflow proposal-hypothesis-foreign')).toBeNull();
    expect(mocks.create).not.toHaveBeenCalled();
  });

  describe('preserved FT-020 Candidate contract at the actual submit handler', () => {
    const permissive = {
      schema: 'TOP_DOWN_CANDIDATE/2.0',
      direction: 'LONG',
      market_context_allowed: ['FAVORABLE', 'CAUTIOUS'],
    };
    const strict = { ...permissive, market_context_allowed: ['FAVORABLE'] };

    beforeEach(() => {
      mocks.listModels.mockResolvedValue([
        { ...models[0], model_key: 'TOP_DOWN_CANDIDATE', name: 'Candidate' },
      ]);
    });

    it.each([
      [
        'immutable V1 to strict V2',
        { ...permissive, schema: 'TOP_DOWN_CANDIDATE/1.0' },
        'FAVORABLE only',
        strict,
      ],
      ['permissive V2 to strict V2', permissive, 'FAVORABLE only', strict],
      ['strict V2 to permissive V2', strict, 'FAVORABLE + CAUTIOUS', permissive],
    ])(
      'creates only the explicit supported definition: %s',
      async (_name, baseDefinition, choice, expectedDefinition) => {
        const original = structuredClone(baseDefinition);
        mocks.listVersions.mockResolvedValue([
          { ...version('model-alpha'), definition: baseDefinition },
        ]);
        mocks.create.mockResolvedValue(
          proposal('hypothesis-1', { proposed_definition: expectedDefinition }),
        );
        render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
        await selectModel();
        expect(screen.queryByLabelText('Proposed Definition (JSON)')).toBeNull();
        fireEvent.click(screen.getByLabelText(choice));
        rationale('Explicit supported policy');
        submit();
        expect(mocks.create).toHaveBeenCalledTimes(1);
        expect(mocks.create).toHaveBeenCalledWith({
          hypothesis_id: 'hypothesis-1',
          model_id: 'model-alpha',
          base_model_version_id: 'base-model-alpha',
          proposed_definition: expectedDefinition,
          rationale: 'Explicit supported policy',
        });
        expect(baseDefinition).toEqual(original);
        expect(await screen.findByText('DRAFT')).toBeInTheDocument();
      },
    );

    it.each([
      ['unknown key', { ...permissive, future_rule: true }],
      ['missing parameter', { schema: 'TOP_DOWN_CANDIDATE/2.0', direction: 'LONG' }],
      ['unsupported schema', { ...permissive, schema: 'TOP_DOWN_CANDIDATE/3.0' }],
      ['unsupported direction', { ...permissive, direction: 'SHORT' }],
    ])('does not submit or normalize %s', async (_name, definition) => {
      mocks.listVersions.mockResolvedValue([{ ...version('model-alpha'), definition }]);
      render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
      await selectModel();
      expect(screen.getByRole('alert')).toHaveTextContent('nicht vollständig verstanden');
      expect(screen.queryByLabelText('FAVORABLE only')).toBeNull();
      expect(screen.queryByLabelText('Proposed Definition (JSON)')).toBeNull();
      rationale('Cannot change unknown content');
      submit();
      expect(mocks.create).not.toHaveBeenCalled();
    });

    it('rejects a no-op even when submitted directly', async () => {
      mocks.listVersions.mockResolvedValue([{ ...version('model-alpha'), definition: permissive }]);
      render(<HypothesisProposalPanel hypothesisId="hypothesis-1" />);
      await selectModel();
      rationale('Still no policy change');
      submit();
      expect(mocks.create).not.toHaveBeenCalled();
      expect(screen.getByText('Keine Änderung.')).toBeInTheDocument();
    });
  });

  it.each(['success', 'failure'] as const)(
    'preserves the real keyed parent isolation when an unmounted H1 save ends with %s',
    async (outcome) => {
      const oldSave = deferred<ModelChangeProposalSummary>();
      mocks.create.mockReturnValueOnce(oldSave.promise);
      mocks.listForLessonVersion.mockImplementation((id: string) =>
        Promise.resolve([
          hypothesis(id === 'lesson-version-1' ? 'hypothesis-1' : 'hypothesis-2', id),
        ]),
      );
      const view = render(<LessonHypothesisPanel lessonVersionId="lesson-version-1" />);
      await selectModel();
      rationale('Original parent instance');
      submit();
      view.rerender(<LessonHypothesisPanel lessonVersionId="lesson-version-2" />);
      await selectModel();
      rationale('Current parent instance');
      if (outcome === 'success') await resolve(oldSave, proposal('hypothesis-1'));
      else await reject(oldSave);
      const article = screen
        .getByRole('heading', { name: 'Hypothesis hypothesis-2' })
        .closest('article');
      if (!article) throw new Error('Expected keyed hypothesis article');
      expect(within(article).getByLabelText('Rationale')).toHaveValue('Current parent instance');
      expect(within(article).queryByRole('alert')).toBeNull();
      expect(screen.queryByText('Validation workflow proposal-hypothesis-1')).toBeNull();
      expect(mocks.create).toHaveBeenCalledTimes(1);
      expect(mocks.create).toHaveBeenCalledWith(
        expect.objectContaining({ hypothesis_id: 'hypothesis-1' }),
      );
    },
  );
});
