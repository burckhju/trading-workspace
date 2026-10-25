import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RuntimeActivationPanel } from './RuntimeActivationPanel';

const mocks = vi.hoisted(() => ({ getCurrent: vi.fn(), activate: vi.fn(), listVersions: vi.fn() }));
vi.mock('../services/runtimeActivationClient', () => ({ runtimeActivationClient: mocks }));
vi.mock('../services/hypothesisProposalClient', () => ({ hypothesisProposalClient: mocks }));

const version = (n: number) => ({
  id: `v${n}`,
  model_id: 'model-1',
  version: n,
  status: 'APPROVED',
  definition: {
    schema: 'TOP_DOWN_CANDIDATE/2.0',
    direction: 'LONG',
    market_context_allowed: n === 1 ? ['FAVORABLE', 'CAUTIOUS'] : ['FAVORABLE'],
  },
  previous_version_id: n === 1 ? null : 'v1',
  change_summary: 'Synthetic',
});
const activation = (n: number) => ({
  id: `activation-${n}`,
  model_id: 'model-1',
  model_version_id: `v${n}`,
  model_version: version(n),
  activated_at: '2026-10-25T09:00:00Z',
  activated_by: 'actor',
  correlation_id: null,
});
function panel() {
  return (
    <RuntimeActivationPanel modelId="model-1" approvedVersionId="v2" approvedVersionNumber={2} />
  );
}

describe('explicit activation and return', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listVersions.mockResolvedValue([version(1), version(2)]);
    mocks.getCurrent.mockResolvedValue(activation(1));
    mocks.activate.mockImplementation((_model: string, id: string) =>
      Promise.resolve(activation(Number(id.slice(1)))),
    );
  });

  it('can explicitly return to the retained initial approved version A', async () => {
    render(panel());
    fireEvent.click(await screen.findByRole('button', { name: 'Version 2 aktivieren' }));
    expect(await screen.findByText('APPROVED Version 2 ist aktuell aktiv.')).toBeInTheDocument();
    fireEvent.change(screen.getByRole('combobox', { name: 'Genehmigte Zielversion' }), {
      target: { value: 'v1' },
    });
    expect(mocks.activate).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Version 1 aktivieren' }));
    await waitFor(() =>
      expect(mocks.activate).toHaveBeenLastCalledWith('model-1', 'v1', undefined),
    );
    expect(await screen.findByText('APPROVED Version 1 ist aktuell aktiv.')).toBeInTheDocument();
  });

  it('sends only one activation for two synchronous clicks', async () => {
    mocks.activate.mockReturnValue(new Promise(() => undefined));
    render(panel());
    const button = await screen.findByRole('button', { name: 'Version 2 aktivieren' });
    act(() => {
      fireEvent.click(button);
      fireEvent.click(button);
    });
    expect(mocks.activate).toHaveBeenCalledTimes(1);
  });

  it('does not mistake an unsuccessful current-state read for no active version', async () => {
    mocks.getCurrent.mockRejectedValue(new Error('read unavailable'));
    render(panel());
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.queryByText(/noch keine Runtime-Version aktiviert/)).toBeNull();
    expect(screen.queryByRole('button', { name: 'Version 2 aktivieren' })).toBeNull();
  });

  it('ignores a late activation response after leaving and reopening the governance view', async () => {
    let finish: (value: ReturnType<typeof activation>) => void = () => undefined;
    const pending = new Promise<ReturnType<typeof activation>>((resolve) => {
      finish = resolve;
    });
    mocks.activate.mockReturnValue(pending);
    const oldView = render(panel());
    fireEvent.click(await screen.findByRole('button', { name: 'Version 2 aktivieren' }));
    oldView.unmount();
    mocks.getCurrent.mockResolvedValue(activation(1));
    render(panel());
    await screen.findByRole('button', { name: 'Version 2 aktivieren' });
    await act(async () => {
      finish(activation(2));
      await pending;
    });
    expect(screen.getByText(/Aktuell aktiv: Version 1/)).toBeInTheDocument();
    expect(screen.queryByText('APPROVED Version 2 ist aktuell aktiv.')).toBeNull();
    expect(mocks.activate).toHaveBeenCalledTimes(1);
  });

  it('requires deliberate readback after an uncertain write and never retries automatically', async () => {
    mocks.activate.mockRejectedValue(new Error('connection lost'));
    render(panel());
    fireEvent.click(await screen.findByRole('button', { name: 'Version 2 aktivieren' }));
    expect(await screen.findByText(/Der Befehlsabschluss ist nicht bestätigt/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Version 2 aktivieren' })).toBeDisabled();
    mocks.getCurrent.mockResolvedValue(activation(2));
    fireEvent.click(screen.getByRole('button', { name: 'Aktivierungsstand neu laden' }));
    expect(await screen.findByText('APPROVED Version 2 ist aktuell aktiv.')).toBeInTheDocument();
    expect(mocks.activate).toHaveBeenCalledTimes(1);
  });

  it('does not offer DRAFT or unknown Candidate definitions as return targets', async () => {
    mocks.listVersions.mockResolvedValue([
      version(1),
      version(2),
      { ...version(3), status: 'DRAFT' },
      {
        ...version(4),
        definition: {
          schema: 'TOP_DOWN_CANDIDATE/99.0',
          direction: 'LONG',
          market_context_allowed: ['FAVORABLE'],
        },
      },
    ]);
    render(
      <RuntimeActivationPanel
        modelId="model-1"
        approvedVersionId="v2"
        approvedVersionNumber={2}
        modelKey="TOP_DOWN_CANDIDATE"
      />,
    );
    await screen.findByRole('button', { name: 'Version 2 aktivieren' });
    expect(
      screen.getAllByRole('option').map((option) => (option as HTMLOptionElement).value),
    ).toEqual(['', 'v1', 'v2']);
    expect(screen.getByText(/Neueste Modellversion: 4/)).toBeInTheDocument();
    expect(mocks.activate).not.toHaveBeenCalled();
  });

  it('fails closed for a mixed model version list', async () => {
    mocks.listVersions.mockResolvedValue([
      version(1),
      { ...version(2), model_id: 'foreign-model' },
    ]);
    render(panel());
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Version 2 aktivieren' })).toBeNull();
  });
});
