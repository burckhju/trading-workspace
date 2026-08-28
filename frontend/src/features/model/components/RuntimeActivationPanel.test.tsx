import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { RuntimeActivationPanel } from './RuntimeActivationPanel';

const mocks = vi.hoisted(() => ({
  getCurrent: vi.fn(),
  activate: vi.fn(),
}));

vi.mock('../services/runtimeActivationClient', () => ({
  runtimeActivationClient: mocks,
}));

describe('RuntimeActivationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getCurrent.mockResolvedValue(null);
  });

  it('shows approved version as not active and offers explicit activation', async () => {
    render(
      <RuntimeActivationPanel
        modelId="model-1"
        approvedVersionId="version-2"
        approvedVersionNumber={2}
      />,
    );

    expect(await screen.findByText(/noch keine Runtime-Version aktiviert/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Version 2 aktivieren' })).toBeInTheDocument();
  });

  it('activates explicitly and then shows the active version', async () => {
    mocks.activate.mockResolvedValue({
      id: 'activation-1',
      model_id: 'model-1',
      model_version_id: 'version-2',
      activated_at: '2026-08-28T20:00:00Z',
      activated_by: 'actor-1',
      correlation_id: 'corr-1',
      model_version: {
        id: 'version-2',
        model_id: 'model-1',
        version: 2,
        status: 'APPROVED',
        definition: {},
        change_summary: 'change',
        created_at: '2026-08-28T19:00:00Z',
        created_by: 'actor-1',
        previous_version_id: 'version-1',
      },
    });

    render(
      <RuntimeActivationPanel
        modelId="model-1"
        approvedVersionId="version-2"
        approvedVersionNumber={2}
      />,
    );
    await screen.findByText(/noch keine Runtime-Version aktiviert/);
    fireEvent.change(screen.getByLabelText('Correlation ID (optional)'), {
      target: { value: 'corr-1' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Version 2 aktivieren' }));

    await waitFor(() =>
      expect(mocks.activate).toHaveBeenCalledWith('model-1', 'version-2', 'corr-1'),
    );
    expect(await screen.findByText(/Version 2 ist aktuell aktiv/)).toBeInTheDocument();
  });

  it('suppresses duplicate activation when target is already active', async () => {
    mocks.getCurrent.mockResolvedValue({
      id: 'activation-1',
      model_id: 'model-1',
      model_version_id: 'version-2',
      activated_at: '2026-08-28T20:00:00Z',
      activated_by: 'actor-1',
      correlation_id: null,
      model_version: {
        id: 'version-2',
        model_id: 'model-1',
        version: 2,
        status: 'APPROVED',
        definition: {},
        change_summary: 'change',
        created_at: '2026-08-28T19:00:00Z',
        created_by: 'actor-1',
        previous_version_id: 'version-1',
      },
    });

    render(
      <RuntimeActivationPanel
        modelId="model-1"
        approvedVersionId="version-2"
        approvedVersionNumber={2}
      />,
    );

    expect(await screen.findByText(/Version 2 ist aktuell aktiv/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Version 2 aktivieren' })).toBeNull();
  });
});
