import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, MemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import { MarketApiError } from '../../market/services/http';
import { tradePlanApiClient } from '../services/client';
import type {
  TradePlanDetailResponse,
  TradePlanStatus,
  TradePlanVersionResponse,
} from '../types/api';
import { ExistingTradePlanPage } from './ExistingTradePlanPage';

vi.mock('../../market/services/client', () => ({
  marketApiClient: { getUnderlying: vi.fn() },
}));

vi.mock('../services/client', () => ({
  tradePlanApiClient: {
    get: vi.fn(),
    versions: vi.fn(),
    version: vi.fn(),
    amend: vi.fn(),
    returnToDraft: vi.fn(),
    submitForReview: vi.fn(),
    approve: vi.fn(),
    abandon: vi.fn(),
    delete: vi.fn(),
  },
}));

const getPlan = vi.mocked(tradePlanApiClient.get);
const getVersions = vi.mocked(tradePlanApiClient.versions);
const abandon = vi.mocked(tradePlanApiClient.abandon);
const getVersion = vi.mocked(tradePlanApiClient.version);
const amend = vi.mocked(tradePlanApiClient.amend);
const returnToDraft = vi.mocked(tradePlanApiClient.returnToDraft);
const approve = vi.mocked(tradePlanApiClient.approve);
const hardDelete = vi.mocked(tradePlanApiClient.delete);
const getUnderlying = vi.mocked(marketApiClient.getUnderlying);

function version(status: TradePlanStatus): TradePlanVersionResponse {
  return {
    id: 'version-1',
    trade_plan_id: 'plan-1',
    version: 1,
    direction: 'LONG',
    thesis: 'Trendfortsetzung',
    entry: {
      type: 'PRICE',
      currency: 'EUR',
      price: '100',
      price_from: null,
      price_to: null,
      trigger: null,
      reference_price: null,
      valid_until: null,
      rationale: null,
    },
    invalidation: { stop_price: '95', invalidation_rule: null, rationale: null },
    targets: [{ sequence: 1, price: '110', rationale: null }],
    risk_assumptions: {
      thesis_risk: 'Trendbruch',
      max_loss_assumption: null,
      notes: null,
    },
    status,
    created_at: '2026-09-05T10:00:00Z',
    created_by: 'actor-1',
    previous_version_id: null,
    change_reason: null,
    candidate_evaluation: null,
    approval: null,
    events: [],
  };
}

function detail(status: TradePlanStatus): TradePlanDetailResponse {
  return {
    plan: {
      id: 'plan-1',
      underlying_id: 'underlying-1',
      origin_type: 'MANUAL',
      candidate_id: null,
      candidate_evaluation_id: null,
      created_at: '2026-09-05T10:00:00Z',
      created_by: 'actor-1',
    },
    latest_version: version(status),
  };
}

describe('ExistingTradePlanPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    getUnderlying.mockRejectedValue(new Error('optional context unavailable'));
    abandon.mockResolvedValue(version('ABANDONED'));
    hardDelete.mockResolvedValue({
      trade_plan_id: 'plan-1',
      trade_plan_versions: 1,
      product_selection_runs: 0,
      trades: 0,
      positions: 0,
      alerts: 0,
      notifications: 0,
      post_trade_observations: 0,
      exit_reviews: 0,
      trade_journals: 0,
      learning_evidence: 0,
      external_observation_trade_links: 0,
    });
  });

  it('allows a draft TradePlan to be abandoned and reloads the authoritative state', async () => {
    getPlan.mockResolvedValueOnce(detail('DRAFT')).mockResolvedValue(detail('ABANDONED'));
    getVersions.mockResolvedValueOnce([version('DRAFT')]).mockResolvedValue([version('ABANDONED')]);

    render(
      <MemoryRouter>
        <ExistingTradePlanPage tradePlanId="plan-1" />
      </MemoryRouter>,
    );

    const button = await screen.findByRole('button', { name: 'TradePlan aufgeben' });
    fireEvent.click(button);

    await waitFor(() => expect(abandon).toHaveBeenCalledWith('plan-1', 'version-1'));
    expect(
      await screen.findByRole('heading', { name: 'Version 1 · ABANDONED' }),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'TradePlan aufgeben' })).not.toBeInTheDocument();
  });

  it('does not offer abandon for an approved TradePlan', async () => {
    getPlan.mockResolvedValue(detail('APPROVED'));
    getVersions.mockResolvedValue([version('APPROVED')]);

    render(
      <MemoryRouter>
        <ExistingTradePlanPage tradePlanId="plan-1" />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole('heading', { name: 'Version 1 · APPROVED' }),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'TradePlan aufgeben' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Produktauswahl starten' })).toBeInTheDocument();
  });

  it('requires the visible TradePlan reference before permanent deletion', async () => {
    getPlan.mockResolvedValue(detail('APPROVED'));
    getVersions.mockResolvedValue([version('APPROVED')]);

    render(
      <MemoryRouter>
        <ExistingTradePlanPage tradePlanId="plan-1" />
      </MemoryRouter>,
    );

    const deleteButton = await screen.findByRole('button', {
      name: 'TradePlan unwiderruflich löschen',
    });
    expect(deleteButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/Zur Bestätigung/), {
      target: { value: 'TP-PLAN-1' },
    });
    expect(deleteButton).toBeEnabled();
    fireEvent.click(deleteButton);

    await waitFor(() => expect(hardDelete).toHaveBeenCalledWith('plan-1'));
  });
});

function richVersion(entryType: 'PRICE' | 'PRICE_RANGE' | 'TRIGGER'): TradePlanVersionResponse {
  const base = version('APPROVED');
  return {
    ...base,
    entry: {
      ...base.entry,
      type: entryType,
      price: entryType === 'PRICE' ? '100.123456789123456789' : null,
      price_from: entryType === 'PRICE_RANGE' ? '100.123456789123456789' : null,
      price_to: entryType === 'PRICE_RANGE' ? '101.123456789123456789' : null,
      trigger: entryType === 'TRIGGER' ? 'Schlusskurs über dem Wochenhoch' : null,
      reference_price: '100.123456789123456789',
      currency: 'USD',
      valid_until: '2026-12-01T15:30:45.123456+00:00',
      rationale: 'Bestätigung im Tageschart',
    },
    invalidation: {
      stop_price: '95.123456789123456789',
      invalidation_rule: 'Trendstruktur gebrochen',
      rationale: 'Tief des Ausbruchs',
    },
    targets: [
      { sequence: 1, price: '110.123456789123456789', rationale: 'Erster Widerstand' },
      { sequence: 2, price: '120.123456789123456789', rationale: 'Zweiter Widerstand' },
      { sequence: 3, price: '130.123456789123456789', rationale: 'Dritter Widerstand' },
    ],
    risk_assumptions: {
      thesis_risk: 'Fehlausbruch',
      max_loss_assumption: 'Planannahme ohne Positionsgröße',
      notes: 'Ereignisrisiko beachten',
    },
  };
}

function nextVersion(base: TradePlanVersionResponse): TradePlanVersionResponse {
  return {
    ...base,
    id: 'version-2',
    version: 2,
    status: 'DRAFT',
    thesis: 'Neue These',
    previous_version_id: base.id,
    change_reason: 'Neue Information',
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function usePlanData(base: TradePlanVersionResponse, latest = base) {
  getPlan.mockResolvedValue({ ...detail(base.status), latest_version: latest });
  getVersions.mockResolvedValue(base.id === latest.id ? [base] : [base, latest]);
  getVersion.mockImplementation((_planId, id) =>
    id === base.id
      ? Promise.resolve(base)
      : id === latest.id
        ? Promise.resolve(latest)
        : Promise.reject(new Error('Planversion nicht gefunden')),
  );
}

function renderVersion() {
  return render(
    <MemoryRouter
      initialEntries={['/trade-plans?trade_plan_id=plan-1&trade_plan_version_id=version-1']}
    >
      <ExistingTradePlanPage tradePlanId="plan-1" />
    </MemoryRouter>,
  );
}

describe('ExistingTradePlanPage version binding and amendments', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    getUnderlying.mockRejectedValue(new Error('labels unavailable'));
  });

  it('shows an exact approved historical version while the newest version is a draft', async () => {
    const base = richVersion('TRIGGER');
    usePlanData(base, nextVersion(base));
    renderVersion();
    expect(
      await screen.findByRole('heading', { name: 'Version 1 · APPROVED' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Neueste Version: 2 · DRAFT')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Produktauswahl starten' })).toHaveAttribute(
      'href',
      '/product-selection?trade_plan_id=plan-1&trade_plan_version_id=version-1',
    );
    expect(getVersion).toHaveBeenCalledWith('plan-1', 'version-1', expect.any(AbortSignal));
    expect(screen.getByText('Schlusskurs über dem Wochenhoch')).toBeInTheDocument();
    expect(screen.getByText('Dritter Widerstand')).toBeInTheDocument();
    expect(amend).not.toHaveBeenCalled();
    expect(approve).not.toHaveBeenCalled();
  });

  it('does not replace a missing or foreign explicitly requested version with latest', async () => {
    const base = richVersion('PRICE');
    usePlanData(base);
    getVersion.mockResolvedValue({ ...base, id: 'foreign-version', trade_plan_id: 'foreign-plan' });
    renderVersion();
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'angeforderte Planversion ist nicht verfügbar',
    );
    expect(screen.queryByRole('heading', { name: 'Version 1 · APPROVED' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Produktauswahl starten' })).not.toBeInTheDocument();
  });

  it('returns READY_FOR_REVIEW to DRAFT as an explicit status action without content revision', async () => {
    const review = version('READY_FOR_REVIEW');
    usePlanData(review);
    returnToDraft.mockImplementation(() => {
      usePlanData(version('DRAFT'));
      return Promise.resolve(version('DRAFT'));
    });
    renderVersion();
    fireEvent.click(await screen.findByRole('button', { name: 'Zurück zu DRAFT' }));
    expect(await screen.findByRole('heading', { name: 'Version 1 · DRAFT' })).toBeInTheDocument();
    expect(returnToDraft).toHaveBeenCalledExactlyOnceWith('plan-1', 'version-1');
    expect(
      screen.queryByRole('button', { name: 'Neue Planversion erstellen' }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/Gespeicherte Entwürfe können derzeit nicht inhaltlich/),
    ).toBeInTheDocument();
    expect(amend).not.toHaveBeenCalled();
  });

  it.each(['', 'version-1&trade_plan_version_id=version-2'])(
    'rejects an incomplete or ambiguous requested version (%s)',
    async (parameter) => {
      usePlanData(richVersion('PRICE'));
      render(
        <MemoryRouter
          initialEntries={[`/trade-plans?trade_plan_id=plan-1&trade_plan_version_id=${parameter}`]}
        >
          <ExistingTradePlanPage tradePlanId="plan-1" />
        </MemoryRouter>,
      );
      expect(await screen.findByRole('alert')).toHaveTextContent('unvollständig oder mehrdeutig');
      expect(getPlan).not.toHaveBeenCalled();
      expect(
        screen.queryByRole('button', { name: 'Neue Planversion erstellen' }),
      ).not.toBeInTheDocument();
    },
  );

  it.each(['PRICE', 'PRICE_RANGE', 'TRIGGER'] as const)(
    'preserves all %s content and decimal precision when only thesis changes',
    async (type) => {
      const base = richVersion(type);
      const created = nextVersion(base);
      usePlanData(base);
      amend.mockImplementation(() => {
        usePlanData(base, created);
        return Promise.resolve(created);
      });
      renderVersion();
      fireEvent.click(await screen.findByRole('button', { name: 'Neue Planversion erstellen' }));
      expect(screen.getByLabelText('Trade Thesis')).toHaveValue(base.thesis);
      expect(screen.getByLabelText('Währung')).toHaveValue('USD');
      expect(screen.getByLabelText('Target 3')).toHaveValue(base.targets[2].price);
      fireEvent.change(screen.getByLabelText('Trade Thesis'), { target: { value: 'Neue These' } });
      fireEvent.change(screen.getByLabelText('Änderungsgrund'), {
        target: { value: 'Neue Information' },
      });
      fireEvent.click(screen.getByRole('button', { name: 'Neue DRAFT-Version speichern' }));
      expect(await screen.findByRole('heading', { name: 'Version 2 · DRAFT' })).toBeInTheDocument();
      expect(amend).toHaveBeenCalledExactlyOnceWith('plan-1', 'version-1', {
        thesis: 'Neue These',
        entry: base.entry,
        invalidation: base.invalidation,
        targets: base.targets,
        risk_assumptions: base.risk_assumptions,
        change_reason: 'Neue Information',
      });
      expect(screen.queryByRole('form', { name: 'Planversion ändern' })).not.toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Version 1 · APPROVED' })).toBeInTheDocument();
      expect(approve).not.toHaveBeenCalled();
    },
  );

  it('keeps a frozen base and edited input when a background read finds a newer version', async () => {
    const base = richVersion('TRIGGER');
    usePlanData(base);
    renderVersion();
    fireEvent.click(await screen.findByRole('button', { name: 'Neue Planversion erstellen' }));
    fireEvent.change(screen.getByLabelText('Trade Thesis'), {
      target: { value: 'Bewusste Eingabe' },
    });
    fireEvent.change(screen.getByLabelText('Änderungsgrund'), { target: { value: 'Grund' } });
    usePlanData(base, nextVersion(base));
    fireEvent.click(screen.getByRole('button', { name: 'Planansicht aktualisieren' }));
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Neue DRAFT-Version speichern' })).toBeEnabled(),
    );
    expect(screen.getByLabelText('Trade Thesis')).toHaveValue('Bewusste Eingabe');
    expect(
      screen.getByRole('heading', { name: 'Neue Planversion aus Version 1' }),
    ).toBeInTheDocument();
    amend.mockRejectedValue(
      new MarketApiError(409, {
        code: 'CONFLICT',
        message: 'Konflikt: Ausgangsversion nicht mehr APPROVED',
        details: [],
        timestamp: '2026-10-25T12:00:00Z',
      }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Neue DRAFT-Version speichern' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Konflikt');
    expect(amend).toHaveBeenCalledWith(
      'plan-1',
      'version-1',
      expect.objectContaining({ thesis: 'Bewusste Eingabe' }),
    );
    expect(screen.getByLabelText('Trade Thesis')).toHaveValue('Bewusste Eingabe');
    expect(screen.getByLabelText('Änderungsgrund')).toHaveValue('Grund');
  });

  it('locks fields and duplicate submissions synchronously while saving', async () => {
    const base = richVersion('TRIGGER');
    const pending = deferred<TradePlanVersionResponse>();
    usePlanData(base);
    amend.mockReturnValue(pending.promise);
    renderVersion();
    fireEvent.click(await screen.findByRole('button', { name: 'Neue Planversion erstellen' }));
    fireEvent.change(screen.getByLabelText('Änderungsgrund'), { target: { value: 'Grund' } });
    const form = screen.getByRole('form', { name: 'Planversion ändern' });
    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(amend).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Trade Thesis')).toBeDisabled();
    expect(screen.getByLabelText('Änderungsgrund')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Abbrechen' })).toBeDisabled();
    await act(async () => {
      pending.reject(new Error('Netzwerkabschluss unbekannt'));
      await pending.promise.catch(() => undefined);
    });
    expect(screen.getByRole('alert')).toHaveTextContent('Netzwerkabschluss unbekannt');
    expect(screen.getByLabelText('Änderungsgrund')).toHaveValue('Grund');
    expect(amend).toHaveBeenCalledTimes(1);
  });

  it('distinguishes confirmed amendment from failed refresh and retains the new draft snapshot', async () => {
    const base = richVersion('TRIGGER');
    const created = nextVersion(base);
    usePlanData(base);
    amend.mockImplementation(() => {
      getPlan.mockRejectedValue(new Error('Refresh offline'));
      return Promise.resolve(created);
    });
    renderVersion();
    fireEvent.click(await screen.findByRole('button', { name: 'Neue Planversion erstellen' }));
    fireEvent.change(screen.getByLabelText('Änderungsgrund'), {
      target: { value: 'Neue Information' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Neue DRAFT-Version speichern' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Refresh offline');
    expect(screen.getByRole('status')).toHaveTextContent('wurde als DRAFT gespeichert');
    expect(screen.getByRole('heading', { name: 'Version 2 · DRAFT' })).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Neue DRAFT-Version speichern' }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Version 1 · APPROVED' })).toBeInTheDocument();
    expect(amend).toHaveBeenCalledTimes(1);
  });

  it('uses a confirmed create snapshot when its following read fails', async () => {
    getPlan.mockRejectedValue(new Error('Read offline'));
    getVersions.mockRejectedValue(new Error('Read offline'));
    getVersion.mockRejectedValue(new Error('Read offline'));
    const created = detail('DRAFT');
    render(
      <MemoryRouter
        initialEntries={[
          {
            pathname: '/trade-plans',
            search: '?trade_plan_id=plan-1&trade_plan_version_id=version-1',
            state: {
              confirmedTradePlan: created,
              confirmationMessage: 'TradePlan wurde als DRAFT erstellt.',
            },
          },
        ]}
      >
        <ExistingTradePlanPage tradePlanId="plan-1" />
      </MemoryRouter>,
    );
    expect(await screen.findByRole('alert')).toHaveTextContent('Read offline');
    expect(screen.getByRole('status')).toHaveTextContent('TradePlan wurde als DRAFT erstellt.');
    expect(screen.getByRole('heading', { name: 'Version 1 · DRAFT' })).toBeInTheDocument();
  });

  it('cancels consciously and never writes on cancellation', async () => {
    usePlanData(richVersion('TRIGGER'));
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    renderVersion();
    fireEvent.click(await screen.findByRole('button', { name: 'Neue Planversion erstellen' }));
    fireEvent.change(screen.getByLabelText('Trade Thesis'), { target: { value: 'Ungespeichert' } });
    fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
    expect(screen.getByLabelText('Trade Thesis')).toHaveValue('Ungespeichert');
    confirm.mockReturnValue(true);
    fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
    expect(screen.queryByRole('form', { name: 'Planversion ändern' })).not.toBeInTheDocument();
    expect(amend).not.toHaveBeenCalled();
  });

  it('requires a discard choice before switching version with unsaved changes', async () => {
    const base = richVersion('PRICE');
    usePlanData(base, nextVersion(base));
    const router = createMemoryRouter(
      [{ path: '/trade-plans', element: <ExistingTradePlanPage tradePlanId="plan-1" /> }],
      { initialEntries: ['/trade-plans?trade_plan_id=plan-1&trade_plan_version_id=version-1'] },
    );
    render(<RouterProvider router={router} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Neue Planversion erstellen' }));
    fireEvent.change(screen.getByLabelText('Trade Thesis'), { target: { value: 'Ungespeichert' } });
    fireEvent.change(screen.getByLabelText('Planversion'), { target: { value: 'version-2' } });
    expect(await screen.findByRole('alertdialog')).toHaveTextContent('Ungespeicherte Änderungen');
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    expect(screen.getByLabelText('Trade Thesis')).toHaveValue('Ungespeichert');
    fireEvent.change(screen.getByLabelText('Planversion'), { target: { value: 'version-2' } });
    fireEvent.click(await screen.findByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
    expect(await screen.findByRole('heading', { name: 'Version 2 · DRAFT' })).toBeInTheDocument();
    expect(amend).not.toHaveBeenCalled();
  });

  it('ignores late reads from a previous plan context', async () => {
    const oldDetail = deferred<TradePlanDetailResponse>();
    const oldVersions = deferred<TradePlanVersionResponse[]>();
    getPlan.mockImplementation((id) =>
      id === 'plan-1'
        ? oldDetail.promise
        : Promise.resolve({
            ...detail('DRAFT'),
            plan: { ...detail('DRAFT').plan, id: 'plan-2' },
            latest_version: {
              ...version('DRAFT'),
              id: 'version-other',
              trade_plan_id: 'plan-2',
              thesis: 'Anderer Plan',
            },
          }),
    );
    getVersions.mockImplementation((id) =>
      id === 'plan-1'
        ? oldVersions.promise
        : Promise.resolve([
            {
              ...version('DRAFT'),
              id: 'version-other',
              trade_plan_id: 'plan-2',
              thesis: 'Anderer Plan',
            },
          ]),
    );
    const rendered = render(
      <MemoryRouter>
        <ExistingTradePlanPage tradePlanId="plan-1" />
      </MemoryRouter>,
    );
    rendered.rerender(
      <MemoryRouter>
        <ExistingTradePlanPage tradePlanId="plan-2" />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Anderer Plan')).toBeInTheDocument();
    await act(async () => {
      oldDetail.resolve(detail('APPROVED'));
      oldVersions.resolve([version('APPROVED')]);
      await Promise.all([oldDetail.promise, oldVersions.promise]);
    });
    expect(screen.getByText('Anderer Plan')).toBeInTheDocument();
    expect(screen.queryByText('Trendfortsetzung')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Neue Planversion erstellen' }),
    ).not.toBeInTheDocument();
  });

  it('keeps candidate provenance and approval history tied to the selected evaluation', async () => {
    const base = richVersion('TRIGGER');
    base.candidate_evaluation = {
      candidate_id: 'candidate-1',
      evaluation_id: 'evaluation-7',
      evaluation_version: 7,
      direction: 'LONG',
      model_id: 'candidate-model',
      model_version: '1.2.3',
      qualification: 'QUALIFIED',
      quality_status: 'VALID',
      evaluated_at: '2026-09-05T08:00:00Z',
      sources: [
        {
          role: 'market',
          source_type: 'MARKET_ANALYSIS',
          source_id: 'analysis-4',
          source_version: 4,
          model_id: 'market-model',
          model_version: '2.0.0',
        },
      ],
    };
    base.approval = {
      approval_id: 'approval-1',
      trade_plan_version_id: base.id,
      version: 1,
      actor: 'actor-1',
      approved_at: '2026-09-05T11:00:00Z',
      correlation_id: 'approval-correlation',
    };
    base.events = [
      {
        id: 'event-1',
        event_type: 'TRADE_PLAN_APPROVED',
        from_status: 'READY_FOR_REVIEW',
        to_status: 'APPROVED',
        reason: 'Explizite Entscheidung',
        actor: 'actor-1',
        correlation_id: 'approval-correlation',
        occurred_at: '2026-09-05T11:00:00Z',
      },
    ];
    usePlanData(base);
    getPlan.mockResolvedValue({
      ...detail('APPROVED'),
      plan: {
        ...detail('APPROVED').plan,
        origin_type: 'CANDIDATE_EVALUATION',
        candidate_id: 'candidate-1',
        candidate_evaluation_id: 'evaluation-7',
      },
      latest_version: base,
    });
    renderVersion();
    await screen.findByRole('heading', { name: 'Version 1 · APPROVED' });
    fireEvent.click(screen.getByText('Herkunft und Lifecycle anzeigen'));
    expect(screen.getByText('Kandidatenursprung · gespeicherte Evaluation v7.')).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Approval-Nachweis' })).toBeVisible();
    expect(screen.getByText('Explizite Entscheidung')).toBeVisible();
    expect(screen.getByText('evaluation-7')).not.toBeVisible();
    fireEvent.click(screen.getByText('Technische Provenance anzeigen'));
    expect(screen.getByText('evaluation-7')).toBeVisible();
    expect(screen.getByText(/market · MARKET_ANALYSIS · analysis-4 · v4/)).toBeVisible();
    expect(amend).not.toHaveBeenCalled();
  });

  it('rejects a selected version with a different candidate evaluation', async () => {
    const base = richVersion('PRICE');
    usePlanData(base);
    getPlan.mockResolvedValue({
      ...detail('APPROVED'),
      plan: {
        ...detail('APPROVED').plan,
        origin_type: 'CANDIDATE_EVALUATION',
        candidate_id: 'candidate-1',
        candidate_evaluation_id: 'evaluation-7',
      },
      latest_version: base,
    });
    renderVersion();
    expect(await screen.findByRole('alert')).toHaveTextContent('Kandidatenursprung passt nicht');
    expect(
      screen.queryByRole('button', { name: 'Neue Planversion erstellen' }),
    ).not.toBeInTheDocument();
  });

  it('does not apply a late amendment response to a different plan', async () => {
    const base = richVersion('TRIGGER');
    const pending = deferred<TradePlanVersionResponse>();
    usePlanData(base);
    amend.mockReturnValue(pending.promise);
    const rendered = render(
      <MemoryRouter>
        <ExistingTradePlanPage tradePlanId="plan-1" />
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByRole('button', { name: 'Neue Planversion erstellen' }));
    fireEvent.change(screen.getByLabelText('Änderungsgrund'), { target: { value: 'Grund' } });
    fireEvent.submit(screen.getByRole('form', { name: 'Planversion ändern' }));
    const other = {
      ...version('DRAFT'),
      id: 'other-version',
      trade_plan_id: 'plan-2',
      thesis: 'Anderer Plan',
    };
    getPlan.mockResolvedValue({
      ...detail('DRAFT'),
      plan: { ...detail('DRAFT').plan, id: 'plan-2' },
      latest_version: other,
    });
    getVersions.mockResolvedValue([other]);
    rendered.rerender(
      <MemoryRouter>
        <ExistingTradePlanPage tradePlanId="plan-2" />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Anderer Plan')).toBeInTheDocument();
    await act(async () => {
      pending.resolve(nextVersion(base));
      await pending.promise;
    });
    expect(screen.getByText('Anderer Plan')).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Version 2 · DRAFT' })).not.toBeInTheDocument();
    expect(amend).toHaveBeenCalledTimes(1);
  });
});

describe('ExistingTradePlanPage context revision and origin hints', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    getUnderlying.mockRejectedValue(new Error('labels unavailable'));
  });

  it('accepts a matching legacy underlying hint without replacing the stored identity', async () => {
    usePlanData(richVersion('PRICE'));
    render(
      <MemoryRouter
        initialEntries={[
          '/trade-plans?trade_plan_id=plan-1&trade_plan_version_id=version-1&underlying_id=underlying-1',
        ]}
      >
        <ExistingTradePlanPage tradePlanId="plan-1" />
      </MemoryRouter>,
    );
    expect(
      await screen.findByRole('heading', { name: 'Version 1 · APPROVED' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Produktauswahl starten' })).toHaveAttribute(
      'href',
      '/product-selection?trade_plan_id=plan-1&trade_plan_version_id=version-1',
    );
    expect(amend).not.toHaveBeenCalled();
  });

  it.each([
    'underlying_id=',
    'underlying_id=underlying-1&underlying_id=underlying-1',
    'candidate_id=candidate-1',
    'candidate_evaluation_id=evaluation-1',
    'candidate_id=&candidate_evaluation_id=evaluation-1',
    'candidate_id=candidate-1&candidate_evaluation_id=evaluation-1&candidate_evaluation_id=evaluation-1',
  ])('rejects empty, duplicate or incomplete origin hints before reading (%s)', async (hint) => {
    usePlanData(richVersion('PRICE'));
    render(
      <MemoryRouter
        initialEntries={[
          `/trade-plans?trade_plan_id=plan-1&trade_plan_version_id=version-1&${hint}`,
        ]}
      >
        <ExistingTradePlanPage tradePlanId="plan-1" />
      </MemoryRouter>,
    );
    expect(await screen.findByRole('alert')).toHaveTextContent(
      /Ursprungskontext|Kandidatenkontext/,
    );
    expect(getPlan).not.toHaveBeenCalled();
    expect(
      screen.queryByRole('button', { name: 'Neue Planversion erstellen' }),
    ).not.toBeInTheDocument();
  });

  it.each([
    'underlying_id=foreign-underlying',
    'candidate_id=candidate-1&candidate_evaluation_id=evaluation-1',
  ])('rejects hints inconsistent with the stored manual identity (%s)', async (hint) => {
    usePlanData(richVersion('PRICE'));
    render(
      <MemoryRouter
        initialEntries={[
          `/trade-plans?trade_plan_id=plan-1&trade_plan_version_id=version-1&${hint}`,
        ]}
      >
        <ExistingTradePlanPage tradePlanId="plan-1" />
      </MemoryRouter>,
    );
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'passt nicht zur gespeicherten Planidentität',
    );
    expect(
      screen.queryByRole('button', { name: 'Neue Planversion erstellen' }),
    ).not.toBeInTheDocument();
    expect(amend).not.toHaveBeenCalled();
  });

  it.each([true, false])(
    'validates a supplied candidate pair against the stored evaluation (matching: %s)',
    async (matching) => {
      const base = richVersion('PRICE');
      base.candidate_evaluation = {
        candidate_id: 'candidate-1',
        evaluation_id: 'evaluation-7',
        evaluation_version: 7,
        direction: 'LONG',
        model_id: 'candidate-model',
        model_version: '1.0.0',
        qualification: 'QUALIFIED',
        quality_status: 'VALID',
        evaluated_at: '2026-09-05T08:00:00Z',
        sources: [],
      };
      usePlanData(base);
      getPlan.mockResolvedValue({
        ...detail('APPROVED'),
        plan: {
          ...detail('APPROVED').plan,
          origin_type: 'CANDIDATE_EVALUATION',
          candidate_id: 'candidate-1',
          candidate_evaluation_id: 'evaluation-7',
        },
        latest_version: base,
      });
      render(
        <MemoryRouter
          initialEntries={[
            `/trade-plans?trade_plan_id=plan-1&trade_plan_version_id=version-1&underlying_id=underlying-1&candidate_id=candidate-1&candidate_evaluation_id=${matching ? 'evaluation-7' : 'evaluation-8'}`,
          ]}
        >
          <ExistingTradePlanPage tradePlanId="plan-1" />
        </MemoryRouter>,
      );
      if (matching)
        expect(
          await screen.findByRole('heading', { name: 'Version 1 · APPROVED' }),
        ).toBeInTheDocument();
      else {
        expect(await screen.findByRole('alert')).toHaveTextContent(
          'passt nicht zur gespeicherten Planidentität',
        );
        expect(
          screen.queryByRole('button', { name: 'Neue Planversion erstellen' }),
        ).not.toBeInTheDocument();
      }
      expect(amend).not.toHaveBeenCalled();
    },
  );

  it('immediately removes stale actions when only an origin hint changes for the same plan/version', async () => {
    const base = richVersion('PRICE');
    usePlanData(base);
    const router = createMemoryRouter(
      [{ path: '/trade-plans', element: <ExistingTradePlanPage tradePlanId="plan-1" /> }],
      {
        initialEntries: [
          '/trade-plans?trade_plan_id=plan-1&trade_plan_version_id=version-1&underlying_id=underlying-1',
        ],
      },
    );
    render(<RouterProvider router={router} />);
    await screen.findByRole('heading', { name: 'Version 1 · APPROVED' });
    const pending = deferred<TradePlanDetailResponse>();
    getPlan.mockReturnValueOnce(pending.promise);
    await act(async () => {
      await router.navigate(
        '/trade-plans?trade_plan_id=plan-1&trade_plan_version_id=version-1&underlying_id=foreign-underlying',
      );
    });
    expect(screen.queryByRole('link', { name: 'Produktauswahl starten' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Neue Planversion erstellen' }),
    ).not.toBeInTheDocument();
    await act(async () => {
      pending.resolve({ ...detail('APPROVED'), latest_version: base });
      await pending.promise;
    });
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'passt nicht zur gespeicherten Planidentität',
    );
  });

  it('ignores an old mutation after a context round trip A to B to A', async () => {
    const base = richVersion('PRICE');
    const pending = deferred<TradePlanVersionResponse>();
    usePlanData(base);
    amend.mockReturnValue(pending.promise);
    const rendered = render(
      <MemoryRouter>
        <ExistingTradePlanPage tradePlanId="plan-1" />
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByRole('button', { name: 'Neue Planversion erstellen' }));
    fireEvent.change(screen.getByLabelText('Änderungsgrund'), {
      target: { value: 'Vor Kontextwechsel' },
    });
    fireEvent.submit(screen.getByRole('form', { name: 'Planversion ändern' }));
    const other = {
      ...version('DRAFT'),
      id: 'other-version',
      trade_plan_id: 'plan-2',
      thesis: 'Anderer Plan',
    };
    getPlan.mockResolvedValue({
      ...detail('DRAFT'),
      plan: { ...detail('DRAFT').plan, id: 'plan-2' },
      latest_version: other,
    });
    getVersions.mockResolvedValue([other]);
    rendered.rerender(
      <MemoryRouter>
        <ExistingTradePlanPage tradePlanId="plan-2" />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Anderer Plan')).toBeInTheDocument();
    usePlanData(base);
    rendered.rerender(
      <MemoryRouter>
        <ExistingTradePlanPage tradePlanId="plan-1" />
      </MemoryRouter>,
    );
    await screen.findByRole('heading', { name: 'Version 1 · APPROVED' });
    await act(async () => {
      pending.resolve(nextVersion(base));
      await pending.promise;
    });
    expect(screen.getByRole('heading', { name: 'Version 1 · APPROVED' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Version 2 · DRAFT' })).not.toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(getVersion).not.toHaveBeenCalled();
    expect(amend).toHaveBeenCalledTimes(1);
  });

  it.each(['empty', 'incomplete', 'invalid-provenance', 'invalid-event'] as const)(
    'preserves inputs and explains an unconfirmed malformed amendment response (%s)',
    async (responseKind) => {
      const base = richVersion('TRIGGER');
      usePlanData(base);
      const complete = nextVersion(base);
      const malformed: unknown =
        responseKind === 'empty'
          ? undefined
          : responseKind === 'incomplete'
            ? { ...complete, entry: null }
            : responseKind === 'invalid-provenance'
              ? { ...complete, candidate_evaluation: { id: 'incomplete' } }
              : { ...complete, events: [{ id: 'incomplete' }] };
      amend.mockResolvedValue(malformed as TradePlanVersionResponse);
      renderVersion();
      fireEvent.click(await screen.findByRole('button', { name: 'Neue Planversion erstellen' }));
      fireEvent.change(screen.getByLabelText('Trade Thesis'), { target: { value: 'Behalten' } });
      fireEvent.change(screen.getByLabelText('Änderungsgrund'), { target: { value: 'Grund' } });
      fireEvent.click(screen.getByRole('button', { name: 'Neue DRAFT-Version speichern' }));
      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Der Abschluss der Speicherung ist unklar',
      );
      expect(screen.getByRole('alert')).not.toHaveTextContent('TypeError');
      expect(screen.getByLabelText('Trade Thesis')).toHaveValue('Behalten');
      expect(screen.getByLabelText('Änderungsgrund')).toHaveValue('Grund');
      expect(screen.queryByRole('heading', { name: 'Version 2 · DRAFT' })).not.toBeInTheDocument();
      expect(amend).toHaveBeenCalledTimes(1);
    },
  );
});
