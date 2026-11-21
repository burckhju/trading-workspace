import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { operationalWorkspaceApiClient } from '../services/client';
import type {
  OperationalAction,
  OperationalPositionsResponse,
  OperationalWorkspaceResponse,
} from '../types';
import { position } from '../../../test/positionFixture';
import { TodayPage } from './TodayPage';
import { OperationalWorkspacePage } from './OperationalWorkspacePage';
import { ExecutionWorkspacePage } from './ExecutionWorkspacePage';
import { DataSourcesPage } from './DataSourcesPage';
import { WorkspaceActionLinks } from '../public/WorkspaceActionLinks';

vi.mock('../services/client', () => ({
  operationalWorkspaceApiClient: {
    getActions: vi.fn(),
    getPositions: vi.fn(),
    getPositionAlertProjection: vi.fn(),
  },
}));
vi.mock('./MarketDataRefreshPanel', () => ({
  MarketDataRefreshPanel: () => <div>Datenstand am bestehenden Reader</div>,
}));
const stamp = '2026-11-21T10:00:00Z';
function action(
  action_type: string,
  priority: OperationalAction['priority'] = 'ACTION',
): OperationalAction {
  return {
    id: action_type,
    action_type,
    priority,
    state: priority === 'BLOCKED' ? 'BLOCKED' : 'ACTIONABLE',
    source_feature: 'source-owner',
    title: action_type,
    detail: 'Fachzustand bleibt beim Owner',
    resource_type: 'trade',
    resource_id: 'exact-id',
    next_action: 'Prüfen',
    target: '/product-selection?run_id=exact',
    occurred_at: stamp,
  };
}
const show = (element: React.ReactNode) => render(<MemoryRouter>{element}</MemoryRouter>);
beforeEach(() => {
  sessionStorage.clear();
  vi.mocked(operationalWorkspaceApiClient.getActions).mockResolvedValue({
    generated_at: stamp,
    actions: [],
  });
  vi.mocked(operationalWorkspaceApiClient.getPositions).mockResolvedValue({
    generated_at: stamp,
    positions: [],
  });
  vi.mocked(operationalWorkspaceApiClient.getPositionAlertProjection).mockResolvedValue(
    position().position_signal!,
  );
});

it('groups existing priorities, shows blocked next steps and links the exact purchase run', async () => {
  vi.mocked(operationalWorkspaceApiClient.getActions).mockResolvedValue({
    generated_at: stamp,
    actions: [
      action('INITIAL_PURCHASE'),
      action('EXIT_REVIEW', 'REVIEW'),
      action('CUSTOM', 'BLOCKED'),
    ],
  });
  show(<TodayPage />);
  const current = await screen.findByRole('region', { name: 'Jetzt prüfen · 1' });
  expect(within(current).getByRole('link', { name: 'Prüfen: INITIAL_PURCHASE' })).toHaveAttribute(
    'href',
    '/product-selection?run_id=exact#purchase',
  );
  expect(screen.getByRole('region', { name: 'Nachbereiten · 1' })).toHaveTextContent('EXIT_REVIEW');
  expect(screen.getByRole('region', { name: 'Voraussetzungen klären · 1' })).toHaveTextContent(
    'Voraussetzung offen',
  );
  expect(operationalWorkspaceApiClient.getPositions).not.toHaveBeenCalled();
});

it('retries an action read without requesting positions or presenting an empty list as healthy', async () => {
  vi.mocked(operationalWorkspaceApiClient.getActions).mockRejectedValueOnce(
    new Error('Lesen fehlgeschlagen'),
  );
  show(<TodayPage />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Lesen fehlgeschlagen');
  await userEvent.click(screen.getByRole('button', { name: 'Erneut versuchen' }));
  expect(
    await screen.findByText(/Eine leere Hinweisliste bestätigt keine vollständige Überwachung/),
  ).toBeInTheDocument();
  expect(operationalWorkspaceApiClient.getActions).toHaveBeenCalledTimes(2);
  expect(operationalWorkspaceApiClient.getPositions).not.toHaveBeenCalled();
});

it('aborts a discarded action context so late data does not enter its successor', async () => {
  let resolve!: (value: OperationalWorkspaceResponse) => void;
  vi.mocked(operationalWorkspaceApiClient.getActions).mockReturnValueOnce(
    new Promise((yes) => {
      resolve = yes;
    }),
  );
  const first = show(<TodayPage />);
  const signal = vi.mocked(operationalWorkspaceApiClient.getActions).mock.calls[0][0]!;
  expect(screen.getByRole('status')).toHaveTextContent('geladen');
  first.unmount();
  expect(signal.aborted).toBe(true);
  show(<TodayPage />);
  await screen.findByText('Aktuell keine offenen Hinweise');
  await act(async () => {
    resolve({ generated_at: stamp, actions: [action('OLD_CONTEXT')] });
    await Promise.resolve();
  });
  expect(screen.queryByText('OLD_CONTEXT')).not.toBeInTheDocument();
});

it('loads the depot independently of attention and diagnostic readers', async () => {
  vi.mocked(operationalWorkspaceApiClient.getPositions).mockResolvedValue({
    generated_at: stamp,
    positions: [position()],
  });
  show(<OperationalWorkspacePage />);
  expect(await screen.findByRole('heading', { name: 'Offene Positionen · 1' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Überwachung' })).toHaveAttribute(
    'href',
    '/trade-management?trade_id=trade-1#trade-risk',
  );
  expect(screen.queryByRole('button', { name: 'Details' })).not.toBeInTheDocument();
  expect(screen.queryByText('Datenstand am bestehenden Reader')).not.toBeInTheDocument();
  expect(operationalWorkspaceApiClient.getActions).not.toHaveBeenCalled();
  expect(operationalWorkspaceApiClient.getPositionAlertProjection).toHaveBeenCalledTimes(1);
});

it('retries only the depot projection and aborts it when leaving', async () => {
  vi.mocked(operationalWorkspaceApiClient.getPositions).mockRejectedValueOnce(
    new Error('Depot nicht lesbar'),
  );
  const host = show(<OperationalWorkspacePage />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Depot nicht lesbar');
  let resolve!: (value: OperationalPositionsResponse) => void;
  vi.mocked(operationalWorkspaceApiClient.getPositions).mockReturnValueOnce(
    new Promise((yes) => {
      resolve = yes;
    }),
  );
  await userEvent.click(screen.getByRole('button', { name: 'Erneut versuchen' }));
  const signal = vi.mocked(operationalWorkspaceApiClient.getPositions).mock.calls[1][0]!;
  host.unmount();
  expect(signal.aborted).toBe(true);
  await act(async () => {
    resolve({ generated_at: stamp, positions: [position()] });
    await Promise.resolve();
  });
  expect(operationalWorkspaceApiClient.getPositionAlertProjection).not.toHaveBeenCalled();
  expect(operationalWorkspaceApiClient.getActions).not.toHaveBeenCalled();
});

it('offers existing manual capture paths and pending purchases from the same task projection', async () => {
  vi.mocked(operationalWorkspaceApiClient.getActions).mockResolvedValue({
    generated_at: stamp,
    actions: [action('INITIAL_PURCHASE', 'BLOCKED'), action('EXIT_REVIEW')],
  });
  show(<ExecutionWorkspacePage />);
  expect(await screen.findByText('Voraussetzung offen: Prüfen')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'INITIAL_PURCHASE' })).toHaveAttribute(
    'href',
    '/product-selection?run_id=exact#purchase',
  );
  expect(screen.queryByText('EXIT_REVIEW')).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Manuellen Tradeplan anlegen' })).toHaveAttribute(
    'href',
    '/trade-plans',
  );
  await userEvent.click(screen.getByText('Trade über bekannte Kennung öffnen'));
  await userEvent.type(screen.getByLabelText('Trade-Kennung'), 'known trade');
  expect(screen.getByRole('link', { name: 'Buchungen öffnen' })).toHaveAttribute(
    'href',
    '/trade-management?trade_id=known%20trade#execution-dates',
  );
});

it('does not imply a journal index when surfacing only review actions', async () => {
  vi.mocked(operationalWorkspaceApiClient.getActions).mockResolvedValue({
    generated_at: stamp,
    actions: [action('INITIAL_PURCHASE'), action('EXIT_REVIEW'), action('POST_TRADE_OBSERVATION')],
  });
  show(<WorkspaceActionLinks scope="learning" />);
  expect(await screen.findByRole('link', { name: 'EXIT_REVIEW' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'POST_TRADE_OBSERVATION' })).toBeInTheDocument();
  expect(screen.queryByText('INITIAL_PURCHASE')).not.toBeInTheDocument();
});

it('keeps the data reader behind its explicit diagnostic entry and exposes targeted repair routes', () => {
  show(<DataSourcesPage />);
  expect(screen.getByRole('heading', { name: 'Datenquellen & Diagnose' })).toBeInTheDocument();
  expect(screen.getByText('Datenstand am bestehenden Reader')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /Kursdaten einrichten/ })).toHaveAttribute(
    'href',
    '/chart-setup',
  );
  expect(screen.getByRole('link', { name: /Produktdaten prüfen/ })).toHaveAttribute(
    'href',
    '/warrants-admin',
  );
  expect(operationalWorkspaceApiClient.getActions).not.toHaveBeenCalled();
  expect(operationalWorkspaceApiClient.getPositions).not.toHaveBeenCalled();
});
