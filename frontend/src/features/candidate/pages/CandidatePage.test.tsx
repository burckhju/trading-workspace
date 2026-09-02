import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import { candidateApiClient } from '../services/client';
import type { CandidateLiveWorkflow } from '../types/api';
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

const baseWorkflow: CandidateLiveWorkflow = {
  candidate_id: 'candidate-1',
  underlying_id: 'underlying-1',
  as_of: '2026-08-08T20:00:00Z',
  ready: true,
  can_evaluate: true,
  next_action: null,
  steps: [
    {
      code: 'MARKET_PROVIDER_MAPPING',
      label: 'Market EODHD mapping',
      status: 'COMPLETE',
      detail: 'Mapping is valid.',
      action: null,
      resource_id: 'mapping-1',
      action_params: null,
    },
    {
      code: 'CANDIDATE_RUNTIME_MODEL',
      label: 'Candidate runtime model',
      status: 'COMPLETE',
      detail: 'Active executable model TOP_DOWN_CANDIDATE version 1.0.',
      action: null,
      resource_id: 'model-version-1',
      action_params: null,
    },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter>
      <CandidatePage />
    </MemoryRouter>,
  );
}

describe('CandidatePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
    mockedClient.liveWorkflow.mockResolvedValue(baseWorkflow);
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

  it('shows a COMPLETE runtime model as active and usable and enables evaluate from can_evaluate', async () => {
    renderPage();

    expect(await screen.findByText('Aktiv und verwendbar')).toBeInTheDocument();
    expect(screen.getByText(/TOP_DOWN_CANDIDATE version 1.0/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Top-down neu bewerten' })).toBeEnabled();
    expect(screen.getByText('Benutzerstatus: UNDER_REVIEW')).toBeInTheDocument();
    expect(screen.getByText('TD-MARKET-001')).toBeInTheDocument();
  });

  it('shows no-active runtime blocker and does not route it to top-down administration', async () => {
    mockedClient.liveWorkflow.mockResolvedValue({
      ...baseWorkflow,
      ready: false,
      can_evaluate: false,
      next_action: 'ACTIVATE_CANDIDATE_MODEL',
      steps: [
        {
          code: 'CANDIDATE_RUNTIME_MODEL',
          label: 'Candidate runtime model',
          status: 'BLOCKED',
          detail: 'No active TOP_DOWN_CANDIDATE model version is available.',
          action: 'ACTIVATE_CANDIDATE_MODEL',
          resource_id: null,
          action_params: null,
        },
      ],
    });

    renderPage();

    expect(
      await screen.findByText('Keine aktive Candidate-Modellversion vorhanden.'),
    ).toBeInTheDocument();
    expect(screen.getByText(/Nächster Schritt: Candidate-Modell aktivieren/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Top-down neu bewerten' })).toBeDisabled();
    expect(screen.queryByRole('link', { name: 'Schritt bearbeiten' })).not.toBeInTheDocument();
  });

  it('shows an incompatible active runtime as blocked and never presents it as ready', async () => {
    mockedClient.liveWorkflow.mockResolvedValue({
      ...baseWorkflow,
      ready: false,
      can_evaluate: false,
      next_action: 'ACTIVATE_COMPATIBLE_CANDIDATE_MODEL',
      steps: [
        {
          code: 'CANDIDATE_RUNTIME_MODEL',
          label: 'Candidate runtime model',
          status: 'BLOCKED',
          detail: 'Active Candidate model is not executable: unsupported schema 2.0.',
          action: 'ACTIVATE_COMPATIBLE_CANDIDATE_MODEL',
          resource_id: 'model-version-2',
          action_params: null,
        },
      ],
    });

    renderPage();

    expect(
      await screen.findByText(
        'Eine Candidate-Modellversion ist aktiviert, aber aktuell nicht ausführbar.',
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Nächster Schritt: Kompatible Candidate-Modellversion aktivieren'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Top-down neu bewerten' })).toBeDisabled();
    expect(screen.queryByText('Aktiv und verwendbar')).not.toBeInTheDocument();
  });

  it('uses global can_evaluate even when the runtime step is COMPLETE', async () => {
    mockedClient.liveWorkflow.mockResolvedValue({
      ...baseWorkflow,
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
        baseWorkflow.steps[1],
      ],
    });

    renderPage();

    expect(await screen.findByText('Aktiv und verwendbar')).toBeInTheDocument();
    const evaluateButton = screen.getByRole('button', { name: 'Top-down neu bewerten' });
    expect(evaluateButton).toBeDisabled();
    await userEvent.click(evaluateButton);
    expect(mockedClient.evaluateAuto).not.toHaveBeenCalled();
  });

  it('fails closed while readiness is loading', async () => {
    let resolveWorkflow: (workflow: CandidateLiveWorkflow) => void = () => undefined;
    mockedClient.liveWorkflow.mockReturnValue(
      new Promise((resolve) => {
        resolveWorkflow = resolve;
      }),
    );

    renderPage();

    expect(await screen.findByText('Voraussetzungen werden geprüft …')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Top-down neu bewerten' })).toBeDisabled();

    resolveWorkflow(baseWorkflow);
    expect(await screen.findByText('Aktiv und verwendbar')).toBeInTheDocument();
  });

  it('fails closed on readiness error and supports retry', async () => {
    mockedClient.liveWorkflow.mockRejectedValueOnce(new Error('readiness unavailable'));
    mockedClient.liveWorkflow.mockResolvedValueOnce(baseWorkflow);

    renderPage();

    expect(
      await screen.findByText('Voraussetzungen konnten nicht geprüft werden'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Top-down neu bewerten' })).toBeDisabled();

    await userEvent.click(screen.getByRole('button', { name: 'Erneut prüfen' }));

    expect(await screen.findByText('Aktiv und verwendbar')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Top-down neu bewerten' })).toBeEnabled();
  });

  it('reloads readiness after an evaluate rejection and surfaces the changed runtime state', async () => {
    mockedClient.evaluateAuto.mockRejectedValueOnce(new Error('Runtime activation changed'));
    mockedClient.liveWorkflow.mockResolvedValueOnce(baseWorkflow).mockResolvedValueOnce({
      ...baseWorkflow,
      ready: false,
      can_evaluate: false,
      next_action: 'ACTIVATE_CANDIDATE_MODEL',
      steps: [
        {
          code: 'CANDIDATE_RUNTIME_MODEL',
          label: 'Candidate runtime model',
          status: 'BLOCKED',
          detail: 'No active TOP_DOWN_CANDIDATE model version is available.',
          action: 'ACTIVATE_CANDIDATE_MODEL',
          resource_id: null,
          action_params: null,
        },
      ],
    });

    renderPage();
    expect(await screen.findByText('Aktiv und verwendbar')).toBeInTheDocument();
    const evaluateButton = screen.getByRole('button', { name: 'Top-down neu bewerten' });
    expect(evaluateButton).toBeEnabled();

    await userEvent.click(evaluateButton);

    expect(await screen.findByText(/Runtime activation changed/)).toBeInTheDocument();
    expect(
      await screen.findByText('Keine aktive Candidate-Modellversion vorhanden.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Top-down neu bewerten' })).toBeDisabled();
    expect(mockedClient.liveWorkflow).toHaveBeenCalledTimes(2);
  });
});
