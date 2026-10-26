import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  createMemoryRouter,
  MemoryRouter,
  RouterProvider,
  useLocation,
  useNavigate,
} from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { MarketApiError } from '../../market/services/http';
import { tradeManagementApiClient } from '../../trade/services/client';
import { tradePlanApiClient } from '../../trade_plan/services/client';
import { productSelectionApiClient } from '../services/client';
import { selectionPlanFixture } from '../test/planContextFixtures';
import type { ProductSelectionRunDetailResponse } from '../types/api';
import { ProductSelectionPage } from './ProductSelectionPage';

vi.mock('../services/useSelectionReferenceData', () => ({
  useSelectionReferenceData: () => ({
    products: {},
    plans: {},
    loading: false,
    errors: [],
    reload: vi.fn(),
  }),
}));

const plan = selectionPlanFixture;
const version = plan.latest_version;
const planRoute = `/product-selection?trade_plan_id=${plan.plan.id}&trade_plan_version_id=${version.id}`;
const run: ProductSelectionRunDetailResponse = {
  run: {
    id: '00000000-0000-4000-8000-000000000101',
    trade_plan_id: plan.plan.id,
    trade_plan_version_id: version.id,
    trade_plan_version_status: 'APPROVED',
    underlying_id: plan.plan.underlying_id,
    evaluated_at: '2026-10-25T12:00:00Z',
    created_at: '2026-10-25T12:00:00Z',
    created_by: 'actor',
    universe_model: { model_id: 'u', model_version: '1' },
    eligibility_model: { model_id: 'e', model_version: '1' },
    evaluation_model: { model_id: 'm', model_version: '1' },
  },
  evaluations: [
    {
      id: 'evaluation',
      run_id: '00000000-0000-4000-8000-000000000101',
      warrant_id: 'warrant',
      warrant_terms_version_id: 'terms-v1',
      warrant_listing_id: 'listing',
      evaluated_at: '2026-10-25T12:00:00Z',
      eligibility_model: { model_id: 'e', model_version: '1' },
      evaluation_model: { model_id: 'm', model_version: '1' },
      inputs: [],
      criteria: [],
      metrics: [],
      eligibility_status: 'NOT_EVALUABLE',
      reasons: ['Quote missing'],
    },
  ],
  universe_omissions: [],
  selection: null,
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

beforeEach(() => {
  vi.spyOn(tradePlanApiClient, 'get').mockResolvedValue(plan);
  vi.spyOn(tradePlanApiClient, 'version').mockResolvedValue(version);
  vi.spyOn(productSelectionApiClient, 'get').mockResolvedValue(run);
  vi.spyOn(productSelectionApiClient, 'listForTradePlanVersion').mockResolvedValue([]);
  vi.spyOn(productSelectionApiClient, 'start').mockResolvedValue(run);
  vi.spyOn(productSelectionApiClient, 'select').mockResolvedValue(run);
});
afterEach(() => vi.restoreAllMocks());

function CurrentRoute() {
  const location = useLocation();
  return <div data-testid="current-route">{location.search}</div>;
}

function renderContext(url = planRoute) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <CurrentRoute />
      <ProductSelectionPage />
    </MemoryRouter>,
  );
}
async function ready() {
  const start = screen.getByRole('button', { name: 'Produkte neu bewerten' });
  await waitFor(() => expect(start).toBeEnabled());
  return start;
}

describe('bound product-selection context', () => {
  it.each([
    '?trade_plan_id=plan',
    '?trade_plan_version_id=version',
    '?run_id=',
    '?trade_plan_id=one&trade_plan_id=two&trade_plan_version_id=version',
    '?run_id=run&trade_plan_id=plan',
  ])('rejects incomplete or ambiguous context %s without a fallback read', async (query) => {
    renderContext(`/product-selection${query}`);
    expect(await screen.findByRole('alert')).toHaveTextContent(
      /unvollständig oder widersprüchlich/,
    );
    expect(screen.getByRole('button', { name: 'Produkte neu bewerten' })).toBeDisabled();
    expect(tradePlanApiClient.get).not.toHaveBeenCalled();
    expect(productSelectionApiClient.get).not.toHaveBeenCalled();
    expect(productSelectionApiClient.start).not.toHaveBeenCalled();
  });

  it('binds the exact APPROVED version although the latest version is a newer DRAFT', async () => {
    vi.mocked(tradePlanApiClient.get).mockResolvedValue({
      ...plan,
      latest_version: { ...version, id: 'new-draft', version: 4, status: 'DRAFT' },
    });
    const user = userEvent.setup();
    renderContext();
    await ready();
    expect(screen.getByText('Version 3 · APPROVED')).toBeInTheDocument();
    expect(screen.queryByLabelText('TradePlan-ID')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('TradePlanVersion-ID')).not.toBeInTheDocument();
    expect(productSelectionApiClient.start).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Produkte neu bewerten' }));
    expect(productSelectionApiClient.start).toHaveBeenCalledWith({
      trade_plan_id: plan.plan.id,
      trade_plan_version_id: version.id,
    });
  });

  it.each(['DRAFT', 'SUPERSEDED'] as const)(
    'does not start new evaluations for a %s version',
    async (status) => {
      vi.mocked(tradePlanApiClient.version).mockResolvedValue({ ...version, status });
      renderContext();
      expect(await screen.findByText(`Version 3 · ${status}`)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Produkte neu bewerten' })).toBeDisabled();
      expect(productSelectionApiClient.start).not.toHaveBeenCalled();
    },
  );

  it('does not substitute latest when the requested version is missing', async () => {
    vi.mocked(tradePlanApiClient.version).mockRejectedValue(
      new Error('Angeforderte Version nicht gefunden'),
    );
    renderContext();
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Angeforderte Version nicht gefunden',
    );
    expect(screen.getByRole('button', { name: 'Produkte neu bewerten' })).toBeDisabled();
    expect(productSelectionApiClient.listForTradePlanVersion).not.toHaveBeenCalled();
  });

  it('rejects a version loaded for another plan', async () => {
    vi.mocked(tradePlanApiClient.version).mockResolvedValue({
      ...version,
      trade_plan_id: 'another-plan',
    });
    renderContext();
    expect(await screen.findByRole('alert')).toHaveTextContent(
      /gehören nicht zum übergebenen Kontext/,
    );
    expect(screen.getByRole('button', { name: 'Produkte neu bewerten' })).toBeDisabled();
  });

  it('keeps a historical run on its original superseded version after another version was approved', async () => {
    vi.mocked(tradePlanApiClient.get).mockResolvedValue({
      ...plan,
      latest_version: { ...version, id: 'new-approved', version: 4 },
    });
    vi.mocked(tradePlanApiClient.version).mockResolvedValue({ ...version, status: 'SUPERSEDED' });
    renderContext(`/product-selection?run_id=${run.run.id}`);
    expect(await screen.findByText('Version 3 · SUPERSEDED')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ursprüngliche Planversion ansehen' })).toHaveAttribute(
      'href',
      `/trade-plans?trade_plan_id=${plan.plan.id}&trade_plan_version_id=${version.id}`,
    );
    expect(tradePlanApiClient.version).toHaveBeenCalledWith(
      plan.plan.id,
      version.id,
      expect.any(AbortSignal),
    );
    expect(screen.getByRole('button', { name: 'Produkte neu bewerten' })).toBeDisabled();
    expect(productSelectionApiClient.start).not.toHaveBeenCalled();
    expect(productSelectionApiClient.select).not.toHaveBeenCalled();
  });

  it('rejects inconsistent additional plan references on a saved-run link', async () => {
    renderContext(
      `${planRoute}&run_id=${run.run.id}&unused=x`.replace(
        `trade_plan_version_id=${version.id}`,
        'trade_plan_version_id=other-version',
      ),
    );
    expect(await screen.findByRole('alert')).toHaveTextContent(/Run passt nicht/);
    expect(screen.queryByText('Produktvergleich')).not.toBeInTheDocument();
    expect(tradePlanApiClient.get).not.toHaveBeenCalled();
  });

  it('starts exactly one run on double submit and distinguishes saved run from failed history refresh', async () => {
    const pending = deferred<ProductSelectionRunDetailResponse>();
    vi.mocked(productSelectionApiClient.start).mockReturnValue(pending.promise);
    vi.mocked(productSelectionApiClient.listForTradePlanVersion)
      .mockResolvedValueOnce([])
      .mockRejectedValue(new Error('History offline'));
    renderContext();
    const button = await ready();
    const form = button.closest('form');
    if (!form) throw new Error('Expected start form');
    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(productSelectionApiClient.start).toHaveBeenCalledTimes(1);
    expect(button).toBeDisabled();
    await act(async () => {
      pending.resolve(run);
      await pending.promise;
    });
    expect(
      await screen.findByText(/Selection Run wurde gespeichert.*History offline/),
    ).toBeInTheDocument();
    expect(screen.getByText('Produktvergleich')).toBeInTheDocument();
    expect(screen.getByTestId('current-route')).toHaveTextContent(`?run_id=${run.run.id}`);
    expect(productSelectionApiClient.get).not.toHaveBeenCalled();
    expect(productSelectionApiClient.start).toHaveBeenCalledTimes(1);
  });

  it('preserves a rationale after a selection conflict and sends only one concurrent confirmation', async () => {
    const pending = deferred<ProductSelectionRunDetailResponse>();
    vi.mocked(productSelectionApiClient.select).mockReturnValue(pending.promise);
    const user = userEvent.setup();
    renderContext(`/product-selection?run_id=${run.run.id}`);
    await ready();
    await user.click(screen.getByRole('button', { name: 'Dieses Produkt auswählen' }));
    await user.type(
      screen.getByLabelText('Begründung (erforderlich bei nicht bewertbar)'),
      'Bewusst geprüft',
    );
    const confirm = screen.getByRole('button', { name: 'Auswahl dokumentieren' });
    fireEvent.click(confirm);
    fireEvent.click(confirm);
    expect(productSelectionApiClient.select).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Begründung (erforderlich bei nicht bewertbar)')).toBeDisabled();
    await act(async () => {
      pending.resolve({ ...run, run: { ...run.run, id: 'wrong-run' } });
      await pending.promise;
    });
    expect(await within(screen.getByRole('dialog')).findByRole('alert')).toHaveTextContent(
      /Run passt nicht/,
    );
    expect(screen.getByLabelText('Begründung (erforderlich bei nicht bewertbar)')).toHaveValue(
      'Bewusst geprüft',
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Abbrechen' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('requires an explicit decision before discarding selection inputs for another plan', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    const user = userEvent.setup();
    renderContext(`/product-selection?run_id=${run.run.id}`);
    await ready();
    await user.click(screen.getByRole('button', { name: 'Dieses Produkt auswählen' }));
    await user.type(
      screen.getByLabelText('Begründung (erforderlich bei nicht bewertbar)'),
      'Eingabe behalten',
    );
    await user.click(screen.getByRole('button', { name: 'Anderen Plan auswählen' }));
    expect(confirm).toHaveBeenCalledOnce();
    expect(screen.getByLabelText('Begründung (erforderlich bei nicht bewertbar)')).toHaveValue(
      'Eingabe behalten',
    );
    expect(productSelectionApiClient.select).not.toHaveBeenCalled();
  });

  it('ignores a late saved-run response after a route context switch', async () => {
    const old = deferred<ProductSelectionRunDetailResponse>();
    vi.mocked(productSelectionApiClient.get).mockReturnValue(old.promise);
    function Harness() {
      const navigate = useNavigate();
      return (
        <>
          <button
            onClick={() => {
              void navigate(planRoute);
            }}
          >
            Change route
          </button>
          <ProductSelectionPage />
        </>
      );
    }
    render(
      <MemoryRouter initialEntries={['/product-selection?run_id=old-run']}>
        <Harness />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Change route' }));
    await ready();
    await act(async () => {
      old.resolve({ ...run, run: { ...run.run, id: 'old-run' } });
      await old.promise;
    });
    expect(screen.getByText('Version 3 · APPROVED')).toBeInTheDocument();
    expect(screen.queryByText('Produktvergleich')).not.toBeInTheDocument();
    expect(productSelectionApiClient.start).not.toHaveBeenCalled();
  });
});

it('blocks router Back with pending inputs until an explicit discard, preserving them when staying', async () => {
  const user = userEvent.setup();
  const router = createMemoryRouter(
    [
      { path: '/product-selection', element: <ProductSelectionPage /> },
      { path: '/before', element: <h1>Vorherige Seite</h1> },
    ],
    { initialEntries: ['/before', `/product-selection?run_id=${run.run.id}`], initialIndex: 1 },
  );
  render(<RouterProvider router={router} />);
  await ready();
  await user.click(screen.getByRole('button', { name: 'Dieses Produkt auswählen' }));
  await user.type(
    screen.getByLabelText('Begründung (erforderlich bei nicht bewertbar)'),
    'Nicht verwerfen',
  );
  await act(async () => {
    await router.navigate(-1);
  });
  expect(await screen.findByRole('alertdialog')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Hier bleiben' }));
  expect(screen.getByLabelText('Begründung (erforderlich bei nicht bewertbar)')).toHaveValue(
    'Nicht verwerfen',
  );
  await act(async () => {
    await router.navigate(-1);
  });
  await user.click(screen.getByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
  expect(await screen.findByRole('heading', { name: 'Vorherige Seite' })).toBeInTheDocument();
  expect(productSelectionApiClient.select).not.toHaveBeenCalled();
});

it('retains purchase inputs and OPEN_TRADE_EXISTS handoff while preventing concurrent BUY submission', async () => {
  let rejectPurchase!: (reason: Error) => void;
  const purchaseRequest = new Promise<never>((_resolve, reject) => {
    rejectPurchase = reject;
  });
  const purchase = vi
    .spyOn(tradeManagementApiClient, 'purchaseFromSelection')
    .mockReturnValue(purchaseRequest);
  vi.mocked(productSelectionApiClient.get).mockResolvedValue({
    ...run,
    selection: {
      id: 'selection',
      run_id: run.run.id,
      product_evaluation_id: run.evaluations[0].id,
      selected_at: run.run.evaluated_at,
      selected_by: 'actor',
      rationale: 'Explicit choice',
    },
  });
  const user = userEvent.setup();
  renderContext(`/product-selection?run_id=${run.run.id}`);
  await ready();
  expect(screen.getByLabelText('Kaufmenge')).toHaveValue(null);
  expect(screen.getByLabelText('Kaufpreis')).toHaveValue('');
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('');
  await user.type(screen.getByLabelText('Kaufmenge'), '12');
  await user.type(screen.getByLabelText('Kaufpreis'), '2,35001');
  await user.type(screen.getByLabelText('Ausführungswährung (Code)'), 'EUR');
  const form = screen
    .getByRole('button', { name: 'BUY erfassen und Position eröffnen' })
    .closest('form');
  if (!form) throw new Error('Expected capture form');
  fireEvent.submit(form);
  fireEvent.submit(form);
  expect(purchase).toHaveBeenCalledOnce();
  expect(screen.getByLabelText('Kaufmenge')).toBeDisabled();
  expect(screen.getByLabelText('Kaufdatum')).toBeDisabled();
  await act(async () => {
    rejectPurchase(
      new MarketApiError(409, {
        code: 'OPEN_TRADE_EXISTS',
        message: 'Offener Trade vorhanden',
        timestamp: '2026-10-25T12:00:00Z',
        details: [
          {
            field: 'trade',
            message: 'Already open',
            context: { existing_trade_id: 'existing-trade' },
          },
        ],
      }),
    );
    await purchaseRequest.catch(() => undefined);
  });
  expect(
    await screen.findByRole('link', { name: 'Bestehenden Trade öffnen und Nachkauf erfassen' }),
  ).toHaveAttribute('href', '/trade-management?trade_id=existing-trade');
  expect(screen.getByLabelText('Kaufmenge')).toHaveValue(12);
  expect(screen.getByLabelText('Kaufpreis')).toHaveValue('2,35001');
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('EUR');
  expect(purchase).toHaveBeenCalledOnce();
});

it('supports keyboard confirmation and cancellation without escaping the selection dialog', async () => {
  const user = userEvent.setup();
  renderContext(`/product-selection?run_id=${run.run.id}`);
  await ready();
  await user.click(screen.getByRole('button', { name: 'Dieses Produkt auswählen' }));
  const reason = screen.getByLabelText('Begründung (erforderlich bei nicht bewertbar)');
  expect(reason).toHaveFocus();
  await user.keyboard('Bewusst geprüft');
  await user.tab();
  expect(screen.getByRole('button', { name: 'Abbrechen' })).toHaveFocus();
  await user.tab();
  expect(screen.getByRole('button', { name: 'Auswahl dokumentieren' })).toHaveFocus();
  await user.tab();
  expect(reason).toHaveFocus();
  await user.keyboard('{Escape}');
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(productSelectionApiClient.select).not.toHaveBeenCalled();
});

it('ignores a late mutation even after returning to the same URL through a different context', async () => {
  const pending = deferred<ProductSelectionRunDetailResponse>();
  vi.mocked(productSelectionApiClient.start).mockReturnValue(pending.promise);
  function Harness() {
    const navigate = useNavigate();
    return (
      <>
        <button
          onClick={() => {
            void navigate('/product-selection?trade_plan_id=incomplete');
          }}
        >
          Different context
        </button>
        <button
          onClick={() => {
            void navigate(planRoute);
          }}
        >
          Original context
        </button>
        <ProductSelectionPage />
      </>
    );
  }
  render(
    <MemoryRouter initialEntries={[planRoute]}>
      <Harness />
    </MemoryRouter>,
  );
  fireEvent.submit((await ready()).closest('form')!);
  expect(productSelectionApiClient.start).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole('button', { name: 'Different context' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('unvollständig');
  fireEvent.click(screen.getByRole('button', { name: 'Original context' }));
  await ready();
  await act(async () => {
    pending.resolve(run);
    await pending.promise;
  });
  expect(screen.queryByText('Produktvergleich')).not.toBeInTheDocument();
  expect(
    screen.queryByText(/als neuer historischer Selection Run durchgeführt/),
  ).not.toBeInTheDocument();
  expect(productSelectionApiClient.start).toHaveBeenCalledOnce();
});

it('rejects detail responses whose latest version belongs to another plan', async () => {
  vi.mocked(tradePlanApiClient.get).mockResolvedValue({
    ...plan,
    latest_version: { ...version, trade_plan_id: 'foreign-plan' },
  });
  renderContext();
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'gehören nicht zum übergebenen Kontext',
  );
  expect(screen.getByRole('button', { name: 'Produkte neu bewerten' })).toBeDisabled();
  expect(productSelectionApiClient.start).not.toHaveBeenCalled();
});

it('discards the old purchase date explicitly when evaluating a new run and routes to that saved run', async () => {
  const originalSelection = {
    id: 'old-selection',
    run_id: run.run.id,
    product_evaluation_id: run.evaluations[0].id,
    selected_at: run.run.evaluated_at,
    selected_by: 'actor',
    rationale: 'Explicit choice',
  };
  const nextRun: ProductSelectionRunDetailResponse = {
    ...run,
    run: { ...run.run, id: 'new-saved-run' },
    evaluations: run.evaluations.map((evaluation) => ({ ...evaluation, run_id: 'new-saved-run' })),
  };
  vi.mocked(productSelectionApiClient.get).mockResolvedValue({
    ...run,
    selection: originalSelection,
  });
  vi.mocked(productSelectionApiClient.start).mockResolvedValue(nextRun);
  vi.mocked(productSelectionApiClient.select).mockResolvedValue({
    ...nextRun,
    selection: {
      ...originalSelection,
      id: 'new-selection',
      run_id: nextRun.run.id,
    },
  });
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
  const user = userEvent.setup();
  renderContext(`/product-selection?run_id=${run.run.id}`);
  await ready();
  const initialDate = screen.getByLabelText<HTMLInputElement>('Kaufdatum').value;
  fireEvent.change(screen.getByLabelText('Kaufdatum'), { target: { value: '2026-08-15' } });
  await user.click(screen.getByRole('button', { name: 'Produkte neu bewerten' }));
  await screen.findByText('new-saved-run');
  await ready();
  expect(confirm).toHaveBeenCalledOnce();
  expect(screen.getByTestId('current-route')).toHaveTextContent('?run_id=new-saved-run');
  await user.click(screen.getByRole('button', { name: 'Dieses Produkt auswählen' }));
  await user.type(
    screen.getByLabelText('Begründung (erforderlich bei nicht bewertbar)'),
    'Neu geprüft',
  );
  await user.click(screen.getByRole('button', { name: 'Auswahl dokumentieren' }));
  expect(await screen.findByLabelText('Kaufdatum')).toHaveValue(initialDate);
  expect(screen.getByLabelText('Kaufpreis')).toHaveValue('');
  expect(screen.getByLabelText('Kaufmenge')).toHaveValue(null);
  expect(productSelectionApiClient.start).toHaveBeenCalledOnce();
  expect(productSelectionApiClient.get).toHaveBeenCalledOnce();
});

it('explicitly rereads the current canonical run to reveal a selection saved elsewhere without writing', async () => {
  const selectedElsewhere: ProductSelectionRunDetailResponse = {
    ...run,
    selection: {
      id: 'saved-elsewhere',
      run_id: run.run.id,
      product_evaluation_id: run.evaluations[0].id,
      selected_at: run.run.evaluated_at,
      selected_by: 'actor',
      rationale: 'In anderem Fenster gespeichert',
    },
  };
  vi.mocked(productSelectionApiClient.get)
    .mockResolvedValueOnce(run)
    .mockResolvedValueOnce(selectedElsewhere);
  vi.mocked(productSelectionApiClient.listForTradePlanVersion).mockResolvedValue([run.run]);
  const user = userEvent.setup();
  renderContext(`/product-selection?run_id=${run.run.id}`);
  await ready();
  await user.click(screen.getByRole('button', { name: new RegExp(run.run.id) }));
  expect(await screen.findByText('In anderem Fenster gespeichert')).toBeInTheDocument();
  expect(productSelectionApiClient.get).toHaveBeenCalledTimes(2);
  expect(productSelectionApiClient.get).toHaveBeenLastCalledWith(
    run.run.id,
    expect.any(AbortSignal),
  );
  expect(screen.getByTestId('current-route')).toHaveTextContent(`?run_id=${run.run.id}`);
  expect(productSelectionApiClient.start).not.toHaveBeenCalled();
  expect(productSelectionApiClient.select).not.toHaveBeenCalled();
});

it('retains pending input when rereading the same run is cancelled', async () => {
  vi.mocked(productSelectionApiClient.listForTradePlanVersion).mockResolvedValue([run.run]);
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
  const user = userEvent.setup();
  renderContext(`/product-selection?run_id=${run.run.id}`);
  await ready();
  await user.click(screen.getByRole('button', { name: 'Dieses Produkt auswählen' }));
  await user.type(
    screen.getByLabelText('Begründung (erforderlich bei nicht bewertbar)'),
    'Nicht verwerfen',
  );
  await user.click(screen.getByRole('button', { name: new RegExp(run.run.id) }));
  expect(confirm).toHaveBeenCalledOnce();
  expect(screen.getByLabelText('Begründung (erforderlich bei nicht bewertbar)')).toHaveValue(
    'Nicht verwerfen',
  );
  expect(productSelectionApiClient.get).toHaveBeenCalledOnce();
  expect(productSelectionApiClient.start).not.toHaveBeenCalled();
  expect(productSelectionApiClient.select).not.toHaveBeenCalled();
});
