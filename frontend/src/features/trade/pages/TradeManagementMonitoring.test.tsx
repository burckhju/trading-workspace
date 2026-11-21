import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';

import type { HebeltraderTargetsReport } from '../../operational_workspace/hebeltraderTargets';
import { operationalWorkspaceApiClient } from '../../operational_workspace/services/client';
import {
  readQualificationPreview,
  readTargetRequest,
} from '../../operational_workspace/services/hebeltraderQualification';
import {
  assessHebeltraderTargets,
  readHebeltraderTargets,
} from '../../operational_workspace/services/hebeltraderTargets';
import { qualificationPreview } from '../../operational_workspace/test/hebeltraderQualificationFixture';
import { targetReport } from '../../operational_workspace/test/hebeltraderTargetsFixture';
import { warrantApiClient } from '../../product/services/client';
import { tradeManagementApiClient } from '../services/client';
import { TradeManagementPage } from './TradeManagementPage';

// Keep the real canonical host, adapter, shared guard and qualification command owner.
// Other evidence readers retain their independent contract suites.
vi.mock('../../operational_workspace/services/client', () => ({
  operationalWorkspaceApiClient: { getPositions: vi.fn() },
}));
vi.mock('../../operational_workspace/services/hebeltraderTargets', async (original) => ({
  ...(await original<typeof import('../../operational_workspace/services/hebeltraderTargets')>()),
  readHebeltraderTargets: vi.fn(),
  assessHebeltraderTargets: vi.fn(),
}));
vi.mock('../../operational_workspace/services/hebeltraderQualification', () => ({
  readQualificationPreview: vi.fn(),
  readTargetRequest: vi.fn(),
}));
vi.mock('../../operational_workspace/components/PositionPriceHistory', () => ({
  PositionPriceHistory: () => <div>Preisverlauf des bestehenden Readers</div>,
}));
vi.mock('../../operational_workspace/components/HebeltraderEvidenceCoverage', () => ({
  HebeltraderEvidenceCoverage: () => <div>Belegabdeckung</div>,
}));
vi.mock('../../operational_workspace/components/HebeltraderSessions', () => ({
  HebeltraderSessions: () => <div>Sitzungsnachweise</div>,
}));
vi.mock('../../operational_workspace/components/HebeltraderOriginalBid', () => ({
  HebeltraderOriginalBid: () => <div>Originaler Bid</div>,
}));
vi.mock('../../operational_workspace/components/HebeltraderLoss', () => ({
  HebeltraderLoss: () => <div>Verlustprüfung</div>,
}));
vi.mock('../../operational_workspace/components/IndicativeEntryObservation', () => ({
  IndicativeEntryObservation: () => <div>Indikative Einstiegsbeobachtung</div>,
}));
vi.mock('../../alert/components/PositionRiskPanel', () => ({
  PositionRiskPanel: () => <div>Risikosignale und Warnregeln</div>,
}));
vi.mock('../../alert/components/TradeAlertsPanel', () => ({
  TradeAlertsPanel: () => <div>Überwachungszustand und Positionshinweise</div>,
}));
vi.mock('../components/ProductValuationPanel', () => ({
  ProductValuationPanel: () => <div>Qualifizierte Produktbewertung</div>,
}));
vi.mock('../components/AdditionalPurchasePanel', () => ({ AdditionalPurchasePanel: () => null }));
vi.mock('../components/TradeCancellationPanel', () => ({ TradeCancellationPanel: () => null }));
vi.mock('../components/ExecutionDatesPanel', () => ({
  ExecutionDatesPanel: () => (
    <section id="execution-dates" tabIndex={-1}>
      Buchungen
    </section>
  ),
}));
vi.mock('../components/TradeSourcesView', () => ({
  TradeSourcesView: () => <h1>Historische Quellen</h1>,
}));
vi.mock('../../product/services/client', () => ({ warrantApiClient: { get: vi.fn() } }));
vi.mock('../services/client', () => ({
  tradeTimelineChangedEvent: 'trade-timeline-changed',
  tradeManagementApiClient: {
    trade: vi.fn(),
    position: vi.fn(),
    managementState: vi.fn(),
    executionCurrencyPreview: vi.fn(),
    sell: vi.fn(),
    changeStop: vi.fn(),
    changeTarget: vi.fn(),
    updateThesis: vi.fn(),
    addNote: vi.fn(),
  },
}));

const api = vi.mocked(tradeManagementApiClient);
const userQuery =
  'trade_id=trade-1&review_version_id=review-exact&journal_version_id=journal-exact';
const referenceName =
  'Konkreter Nachweis für historische Listingzuordnung und gemeinsamen Originalmaßstab';
const reference = () => screen.getByRole('textbox', { name: referenceName });
const confirm = () =>
  screen.getByRole('button', {
    name: 'Historische Zuordnung und Originalmaßstab bestätigen und prüfen',
  });

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

function show(hash = '#trade-risk') {
  const router = createMemoryRouter(
    [
      { path: '/trade-management', element: <TradeManagementPage /> },
      { path: '/workspace', element: <h1>Positionsübersicht</h1> },
      { path: '/warrants-admin', element: <h1>Produktdaten</h1> },
    ],
    { initialEntries: [`/trade-management?${userQuery}${hash}`] },
  );
  const result = render(<RouterProvider router={router} />);
  return { router, ...result };
}

async function openEvidence(user: ReturnType<typeof userEvent.setup>) {
  await screen.findByRole('heading', { name: /Test-Optionsschein trade-/ });
  const summary = screen.getByText('Hebeltrader: Quellen, Voraussetzungen und Prüfungen');
  if (!summary.closest('details')!.open) await user.click(summary);
  const button = await screen.findByRole('button', {
    name: /Historische Vergleichsbelege ansehen|Vergleichsbelege schließen/,
  });
  if (button.textContent === 'Historische Vergleichsbelege ansehen') await user.click(button);
  await screen.findByRole('textbox', { name: referenceName });
}

function openLookup() {
  const summary = screen.getByText('Trade über Kennung öffnen oder Stand neu laden');
  if (!summary.closest('details')!.open) fireEvent.click(summary);
}

beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
  localStorage.clear();
  api.trade.mockImplementation((id) =>
    Promise.resolve({
      id,
      product_id: `product-${id}`,
      origin: 'EXTERNAL',
      trade_plan_id: null,
      trade_plan_version_id: null,
      product_selection_id: null,
      product_evaluation_id: null,
      created_at: '2026-11-14T08:00:00Z',
    }),
  );
  api.position.mockImplementation((id) =>
    Promise.resolve({
      id: id.replace('trade-', 'position-'),
      trade_id: id,
      product_id: `product-${id}`,
      open_quantity: 10,
      cost_basis: '20',
      average_entry_price: '2',
      realized_gross_pnl: '0',
      opened_at: '2026-11-14T08:00:00Z',
      last_execution_at: '2026-11-14T08:00:00Z',
      closed_at: null,
      is_closed: false,
    }),
  );
  api.managementState.mockImplementation((id) =>
    Promise.resolve({
      trade_id: id,
      stop_price: null,
      target_price: null,
      thesis: '',
      notes: [],
      last_event_at: null,
    }),
  );
  api.executionCurrencyPreview.mockResolvedValue({
    currency_code: 'EUR',
    source: 'PRIOR_BUYS',
    source_execution_ids: ['buy'],
    confirmation_ids: [],
  });
  vi.mocked(warrantApiClient.get).mockImplementation((id) =>
    Promise.resolve({
      id,
      workspace_id: 'workspace',
      issuer_id: 'issuer',
      underlying_id: 'underlying',
      product_family: 'WARRANT',
      display_name: `Test-Optionsschein ${id.replace('product-', '')}`,
      isin: null,
      wkn: null,
      lifecycle_status: 'ACTIVE',
      version: 1,
      created_at: '2026-11-14T08:00:00Z',
      updated_at: '2026-11-14T08:00:00Z',
    }),
  );
  vi.mocked(readHebeltraderTargets).mockImplementation((tradeId, positionId) =>
    Promise.resolve({
      ...qualificationPreview().report,
      trade_id: tradeId,
      position_id: positionId,
    }),
  );
  vi.mocked(readQualificationPreview).mockImplementation((tradeId, positionId) => {
    const preview = qualificationPreview();
    preview.report = { ...preview.report, trade_id: tradeId, position_id: positionId };
    return Promise.resolve(preview);
  });
  vi.mocked(assessHebeltraderTargets).mockResolvedValue(targetReport());
});

it('keeps every monitoring owner reachable once and links product maintenance to the exact product and return context', async () => {
  const user = userEvent.setup();
  show();
  await openEvidence(user);
  for (const label of [
    'Überwachungszustand und Positionshinweise',
    'Indikative Einstiegsbeobachtung',
    'Belegabdeckung',
    'Sitzungsnachweise',
    'Originaler Bid',
    'Verlustprüfung',
  ])
    expect(screen.getAllByText(label)).toHaveLength(1);
  expect(screen.getByText('Belegabdeckung')).toBeVisible();
  await user.click(screen.getByText('Risiko- und Trendsignale sowie Warnregeln'));
  expect(screen.getByText('Risikosignale und Warnregeln')).toBeVisible();
  const href = screen
    .getByRole('link', {
      name: 'Produkttermine und Handelsplatz am Optionsschein prüfen',
    })
    .getAttribute('href')!;
  const target = new URL(href, 'http://workspace.test');
  expect(target.pathname).toBe('/warrants-admin');
  expect(target.searchParams.get('product_id')).toBe('product-trade-1');
  expect(target.searchParams.get('trade_return_view')).toBe('monitoring');
  expect(target.searchParams.get('review_version_id')).toBe('review-exact');
  expect(target.searchParams.get('journal_version_id')).toBe('journal-exact');
  expect(screen.getByRole('link', { name: 'Basiswertdiagramm' })).toHaveAttribute(
    'href',
    '/market-charts?underlying=underlying',
  );
  expect(operationalWorkspaceApiClient.getPositions).not.toHaveBeenCalled();
  expect(assessHebeltraderTargets).not.toHaveBeenCalled();
});

it('shows one area at a time while retaining manual and qualification drafts and every read owner across hash navigation', async () => {
  const user = userEvent.setup();
  const { router } = show();
  await openEvidence(user);
  const input = reference();
  await user.type(input, 'A: eigener Originalbeleg');
  const previewSignal = vi.mocked(readQualificationPreview).mock.calls[0][2];
  await user.click(screen.getByRole('link', { name: 'Buchungen' }));
  expect(input).not.toBeVisible();
  const quantity = screen.getByLabelText('Verkaufsmenge');
  fireEvent.change(quantity, { target: { value: '3' } });
  fireEvent.change(screen.getByLabelText('Verkaufspreis'), { target: { value: '2.75' } });
  await user.click(screen.getByRole('link', { name: 'Bearbeiten' }));
  expect(screen.queryByRole('form', { name: 'Verkauf erfassen' })).not.toBeInTheDocument();
  const note = screen.getByLabelText('Neue Management-Notiz');
  await user.type(note, 'Parallel erhaltener Entwurf');
  await user.click(screen.getByRole('link', { name: 'Kursverlauf' }));
  expect(screen.getByText('Preisverlauf des bestehenden Readers')).toBeVisible();
  expect(note).not.toBeVisible();
  await user.click(screen.getByRole('link', { name: 'Überblick' }));
  expect(screen.getByText('Qualifizierte Produktbewertung')).toBeVisible();
  expect(screen.getByText('Preisverlauf des bestehenden Readers')).not.toBeVisible();
  await user.click(screen.getByRole('link', { name: 'Überwachung' }));
  expect(reference()).toBe(input);
  expect(reference()).toHaveValue('A: eigener Originalbeleg');
  expect(screen.getByLabelText('Verkaufsmenge')).toBe(quantity);
  expect(quantity).toHaveValue(3);
  expect(screen.getByLabelText('Neue Management-Notiz')).toBe(note);
  expect(note).toHaveValue('Parallel erhaltener Entwurf');
  expect(router.state.location.search).toBe(`?${userQuery}`);
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  expect(api.trade).toHaveBeenCalledOnce();
  expect(api.position).toHaveBeenCalledOnce();
  expect(readHebeltraderTargets).toHaveBeenCalledOnce();
  expect(readQualificationPreview).toHaveBeenCalledOnce();
  expect(previewSignal?.aborted).toBe(false);
  expect(assessHebeltraderTargets).not.toHaveBeenCalled();
  expect(api.sell).not.toHaveBeenCalled();
});

it('uses one shared navigation guard for a qualification draft and clears it only after explicit departure', async () => {
  const user = userEvent.setup();
  const { router } = show();
  await openEvidence(user);
  await user.type(reference(), 'Privater Beleg für A');
  await user.click(
    screen.getByRole('link', {
      name: 'Produkttermine und Handelsplatz am Optionsschein prüfen',
    }),
  );
  expect(screen.getAllByRole('alertdialog')).toHaveLength(1);
  await user.click(screen.getByRole('button', { name: 'Hier bleiben' }));
  expect(reference()).toHaveValue('Privater Beleg für A');
  const unload = new Event('beforeunload', { cancelable: true });
  window.dispatchEvent(unload);
  expect(unload.defaultPrevented).toBe(true);
  await act(() => router.navigate('/trade-management?trade_id=trade-2#trade-risk'));
  expect(screen.getAllByRole('alertdialog')).toHaveLength(1);
  await user.click(screen.getByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
  await openEvidence(user);
  expect(reference()).toHaveValue('');
  expect(JSON.stringify(sessionStorage)).not.toContain('Privater Beleg');
  expect(JSON.stringify(localStorage)).not.toContain('Privater Beleg');
  expect(screen.getByText(/Beim Verlassen dieser Position oder Neuladen im Browser/)).toBeVisible();
  expect(assessHebeltraderTargets).not.toHaveBeenCalled();
});

it('keeps an in-flight qualification mounted, blocks competing writes and prevents discard navigation', async () => {
  const user = userEvent.setup();
  const write = deferred<HebeltraderTargetsReport>();
  vi.mocked(assessHebeltraderTargets).mockReturnValueOnce(write.promise);
  show();
  await openEvidence(user);
  await user.type(reference(), 'Beleg für den laufenden Prüfauftrag');
  await user.click(confirm());
  const signal = vi.mocked(assessHebeltraderTargets).mock.calls[0][2];
  expect(confirm()).toBeDisabled();
  await user.click(screen.getByRole('link', { name: 'Buchungen' }));
  expect(screen.getByLabelText('Verkaufspreis')).toBeDisabled();
  fireEvent.submit(screen.getByRole('form', { name: 'Verkauf erfassen' }));
  expect(api.sell).not.toHaveBeenCalled();
  await user.click(screen.getByRole('link', { name: 'Bearbeiten' }));
  expect(screen.getByRole('button', { name: 'Stop speichern' })).toBeDisabled();
  await user.click(screen.getByRole('link', { name: 'Zur Positionsübersicht' }));
  expect(screen.getAllByRole('alertdialog')).toHaveLength(1);
  expect(screen.getByRole('heading', { name: 'Speicherung läuft' })).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Eingaben verwerfen und wechseln' })).toBeNull();
  await user.click(screen.getByRole('button', { name: 'Hier bleiben' }));
  await user.click(screen.getByRole('link', { name: 'Überwachung' }));
  expect(signal?.aborted).toBe(false);
  await act(async () => {
    write.resolve(targetReport());
    await write.promise;
  });
  await screen.findByText(/Die ausdrückliche Prüfung wurde bestätigt/);
  expect(assessHebeltraderTargets).toHaveBeenCalledOnce();
  await user.click(screen.getByRole('link', { name: 'Zur Positionsübersicht' }));
  expect(await screen.findByRole('heading', { name: 'Positionsübersicht' })).toBeVisible();
  expect(screen.queryByRole('alertdialog')).toBeNull();
});

it('retains an unknown frozen request through a failed and successful same-trade reload without reissuing it', async () => {
  const user = userEvent.setup();
  vi.mocked(assessHebeltraderTargets).mockRejectedValueOnce(
    new Error('Unbestätigter Schreibausgang'),
  );
  show();
  await openEvidence(user);
  await user.type(reference(), 'Erhaltener Beleg bei Aktualisierung');
  await user.click(confirm());
  await screen.findByText('Unbestätigter Schreibausgang');
  const original = vi.mocked(assessHebeltraderTargets).mock.calls[0][1];
  openLookup();
  api.position.mockRejectedValueOnce(new Error('Positionslesen fehlgeschlagen'));
  await user.click(screen.getByRole('button', { name: 'Laden' }));
  await screen.findByText('Positionslesen fehlgeschlagen');
  expect(reference()).toHaveValue('Erhaltener Beleg bei Aktualisierung');
  await user.click(screen.getByRole('button', { name: 'Laden' }));
  await waitFor(() => expect(readQualificationPreview).toHaveBeenCalledTimes(2));
  await screen.findByRole('textbox', { name: referenceName });
  expect(reference()).toHaveValue('Erhaltener Beleg bei Aktualisierung');
  expect(confirm()).toBeDisabled();
  expect(screen.getByRole('region', { name: 'Unbestätigter Prüfauftrag' })).toBeVisible();
  expect(screen.getByText(new RegExp(original.request_id))).toBeVisible();
  expect(screen.getByText(/Eingefrorene Belegreferenz: Erhaltener Beleg/)).toBeVisible();
  expect(vi.mocked(readQualificationPreview).mock.calls[0][2]?.aborted).toBe(true);
  expect(assessHebeltraderTargets).toHaveBeenCalledOnce();
  expect(readTargetRequest).not.toHaveBeenCalled();
});

it('blocks monitoring commands while a sale owns the shared write lock', async () => {
  const user = userEvent.setup();
  const sale = deferred<Awaited<ReturnType<typeof api.sell>>>();
  api.sell.mockReturnValueOnce(sale.promise);
  show();
  await openEvidence(user);
  await user.type(reference(), 'Geprüfte historische Referenz');
  await user.click(screen.getByRole('link', { name: 'Buchungen' }));
  fireEvent.change(screen.getByLabelText('Verkaufsmenge'), { target: { value: '3' } });
  fireEvent.change(screen.getByLabelText('Verkaufspreis'), { target: { value: '2.75' } });
  await user.click(screen.getByRole('button', { name: 'Teilverkauf erfassen' }));
  expect(api.sell).toHaveBeenCalledOnce();
  await user.click(screen.getByRole('link', { name: 'Überwachung' }));
  expect(confirm()).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Gespeicherte Belege prüfen' })).toBeDisabled();
  await user.click(confirm());
  expect(assessHebeltraderTargets).not.toHaveBeenCalled();
  await act(async () => {
    sale.resolve({} as never);
    await sale.promise;
  });
  await waitFor(() => expect(api.position).toHaveBeenCalledTimes(2));
  expect(await screen.findByRole('textbox', { name: referenceName })).toHaveValue(
    'Geprüfte historische Referenz',
  );
});
