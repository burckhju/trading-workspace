import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { cloneElement, type ReactElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { positionPriceHistory } from '../../../test/positionPriceHistoryFixtures';
import { readPositionPriceHistory } from '../../operational_workspace/services/positionPriceHistory';
import { warrantApiClient } from '../../product/services/client';
import { tradeManagementApiClient } from '../services/client';
import { TradeManagementPage } from './TradeManagementPage';

vi.mock('../../operational_workspace/services/positionPriceHistory', () => ({
  readPositionPriceHistory: vi.fn(),
}));
vi.mock('../../product/services/client', () => ({ warrantApiClient: { get: vi.fn() } }));
vi.mock('../services/client', () => ({
  tradeManagementApiClient: { trade: vi.fn(), position: vi.fn(), managementState: vi.fn() },
}));
vi.mock('../../alert/components/PositionRiskPanel', () => ({ PositionRiskPanel: () => null }));
vi.mock('../../alert/components/TradeAlertsPanel', () => ({ TradeAlertsPanel: () => null }));
vi.mock('../components/TradeCancellationPanel', () => ({ TradeCancellationPanel: () => null }));
vi.mock('../components/AdditionalPurchasePanel', () => ({ AdditionalPurchasePanel: () => null }));
vi.mock('../components/ExecutionDatesPanel', () => ({
  ExecutionDatesPanel: ({
    onChanged,
    reloadToken,
  }: {
    onChanged: () => Promise<void>;
    reloadToken: number;
  }) => (
    <>
      <button
        onClick={() => {
          void onChanged().catch(() => undefined);
        }}
      >
        Read corrected execution
      </button>
      <output aria-label="Booking source reload">{reloadToken}</output>
    </>
  ),
}));
vi.mock('recharts', async (original) => ({
  ...(await original<typeof import('recharts')>()),
  ResponsiveContainer: ({
    children,
  }: {
    children: ReactElement<{ width: number; height: number }>;
  }) => cloneElement(children, { width: 640, height: 288 }),
}));

const trade = {
  id: 'trade-1',
  product_id: 'warrant-1',
  origin: 'EXTERNAL' as const,
  trade_plan_id: null,
  trade_plan_version_id: null,
  product_selection_id: null,
  product_evaluation_id: null,
  created_at: '2026-09-08T08:00:00Z',
};
const position = {
  id: 'position-1',
  trade_id: trade.id,
  product_id: trade.product_id,
  open_quantity: 0,
  cost_basis: '0',
  average_entry_price: '0',
  realized_gross_pnl: '5.00',
  opened_at: trade.created_at,
  last_execution_at: '2026-10-10T08:00:00Z',
  closed_at: '2026-10-10T08:00:00Z',
  is_closed: true,
};
const api = vi.mocked(tradeManagementApiClient);
const history = vi.mocked(readPositionPriceHistory);

beforeEach(() => {
  vi.resetAllMocks();
  api.trade.mockResolvedValue(trade);
  api.position.mockResolvedValue(position);
  api.managementState.mockResolvedValue({
    trade_id: trade.id,
    stop_price: null,
    target_price: null,
    thesis: null,
    notes: [],
    last_event_at: null,
  });
  vi.mocked(warrantApiClient.get).mockResolvedValue({
    id: trade.product_id,
    workspace_id: 'workspace-1',
    issuer_id: 'issuer-1',
    underlying_id: 'underlying-1',
    product_family: 'WARRANT',
    display_name: 'Historische Testposition',
    isin: 'DE000TEST1234',
    wkn: 'TEST12',
    lifecycle_status: 'ACTIVE',
    version: 1,
    created_at: trade.created_at,
    updated_at: trade.created_at,
  });
  history.mockResolvedValue(positionPriceHistory());
});

function show() {
  return render(
    <MemoryRouter initialEntries={['/trade-management?trade_id=trade-1']}>
      <TradeManagementPage />
    </MemoryRouter>,
  );
}

it.each([true, false])(
  'loads the same history component automatically inside an existing closed=%s position',
  async (closed) => {
    api.position.mockResolvedValue({
      ...position,
      is_closed: closed,
      closed_at: closed ? position.closed_at : null,
      open_quantity: closed ? 0 : 10,
    });
    show();
    await screen.findByRole('heading', { name: closed ? 'CLOSED' : 'OPEN' });
    const details = screen.getByRole('region', { name: 'Trade und Position' });
    const chart = within(details).getByRole('region', { name: 'Positionskursverlauf' });
    await within(chart).findByText('Handelswährung: EUR');
    expect(chart.querySelectorAll('.recharts-scatter-symbol')).toHaveLength(1);
    expect(history).toHaveBeenCalledExactlyOnceWith(
      'trade-1',
      'position-1',
      'all',
      expect.any(AbortSignal),
    );
  },
);

it('does not request history for a cancelled position', async () => {
  api.trade.mockResolvedValue({ ...trade, cancelled_at: '2026-10-20T08:00:00Z' });
  show();
  await screen.findByRole('heading', { name: 'CANCELLED' });
  expect(screen.queryByRole('region', { name: 'Positionskursverlauf' })).not.toBeInTheDocument();
  expect(history).not.toHaveBeenCalled();
});

it('refreshes history after execution readback without restarting the booking editor’s concurrent read', async () => {
  show();
  await screen.findByText('Handelswährung: EUR');
  expect(screen.getByLabelText('Booking source reload')).toHaveTextContent('0');
  const originalSignal = history.mock.calls[0][3]!;
  history.mockResolvedValueOnce(positionPriceHistory({ series: [] }));
  fireEvent.click(screen.getByRole('button', { name: 'Read corrected execution' }));
  await screen.findByText('Keine zeitlich und fachlich zuordenbaren Kursdaten vorhanden.');
  expect(originalSignal.aborted).toBe(true);
  expect(history).toHaveBeenCalledTimes(2);
  expect(screen.getByLabelText('Booking source reload')).toHaveTextContent('0');
  expect(screen.queryByTestId('position-price-chart')).not.toBeInTheDocument();
});

it('preserves explicit booking reload while only invalidating history after a successful readback', async () => {
  show();
  await screen.findByText('Handelswährung: EUR');
  api.position.mockRejectedValueOnce(new Error('Storage unavailable'));
  fireEvent.click(screen.getByRole('button', { name: 'Laden' }));
  await screen.findByText('Storage unavailable');
  expect(history).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText('Booking source reload')).toHaveTextContent('1');
  history.mockResolvedValueOnce(positionPriceHistory({ series: [] }));
  fireEvent.click(screen.getByRole('button', { name: 'Laden' }));
  await screen.findByText('Keine zeitlich und fachlich zuordenbaren Kursdaten vorhanden.');
  expect(history).toHaveBeenCalledTimes(2);
  expect(screen.getByLabelText('Booking source reload')).toHaveTextContent('2');
});

it('does not let a pre-correction in-flight price response replace the refreshed history', async () => {
  let finish!: (value: ReturnType<typeof positionPriceHistory>) => void;
  history.mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  show();
  await waitFor(() => expect(history).toHaveBeenCalledTimes(1));
  const originalSignal = history.mock.calls[0][3]!;
  history.mockResolvedValueOnce(positionPriceHistory({ series: [] }));
  fireEvent.click(screen.getByRole('button', { name: 'Read corrected execution' }));
  await screen.findByText('Keine zeitlich und fachlich zuordenbaren Kursdaten vorhanden.');
  expect(originalSignal.aborted).toBe(true);
  await act(async () => {
    finish(positionPriceHistory());
    await Promise.resolve();
  });
  expect(screen.queryByTestId('position-price-chart')).not.toBeInTheDocument();
});
