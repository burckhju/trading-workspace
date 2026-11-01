import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  positionPriceHistory,
  positionPriceSeries,
} from '../../../test/positionPriceHistoryFixtures';
import { readPositionPriceHistory } from '../services/positionPriceHistory';
import { PositionPriceHistory } from './PositionPriceHistory';

const chartState = vi.hoisted(() => ({ fail: true }));

vi.mock('../services/positionPriceHistory', () => ({ readPositionPriceHistory: vi.fn() }));
// The module imports successfully; the renderer fails only after React mounts it.
vi.mock('./PositionPricePlot', () => ({
  PositionPricePlot: ({ currency }: { currency: string }) => {
    if (chartState.fail) throw new Error('Synthetic chart render failure');
    return <p>Diagramm verfügbar: {currency}</p>;
  },
}));

beforeEach(() => {
  chartState.fail = true;
  vi.mocked(readPositionPriceHistory).mockReset().mockResolvedValue(positionPriceHistory());
});

afterEach(() => vi.restoreAllMocks());

it('keeps every original and paginated evidence keyboard accessible after a loaded chart fails to render', async () => {
  const user = userEvent.setup();
  const point = positionPriceSeries().points[0];
  const report = positionPriceHistory({
    series: [
      positionPriceSeries({
        points: Array.from({ length: 51 }, (_, index) => ({
          ...point,
          id: `original-${index}`,
          observed_at: new Date(Date.UTC(2026, 8, 8, 8, index)).toISOString(),
          price: index === 50 ? '0.1234567890123456789' : point.price,
        })),
      }),
      positionPriceSeries({ id: 'usd-source', currency: 'USD' }),
    ],
    events: [
      {
        id: 'date-only-sale',
        side: 'SELL',
        occurred_at: null,
        executed_on: '2026-09-09',
        execution_timezone: 'Europe/Berlin',
        price: '0.123456789012345678',
        currency: null,
        currency_source: 'UNKNOWN',
        quantity: 7,
        plottable: false,
        reason: 'DATE_ONLY',
      },
    ],
  });
  const original = structuredClone(report);
  vi.mocked(readPositionPriceHistory).mockResolvedValue(report);
  const loggedErrors = vi.spyOn(console, 'error').mockImplementation(() => {});
  render(<PositionPriceHistory tradeId="trade-1" positionId="position-1" />);

  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Das Diagramm konnte nicht dargestellt werden',
  );
  expect(screen.getAllByRole('alert')).toHaveLength(1);
  expect(loggedErrors.mock.calls.flat()).toContainEqual(
    expect.objectContaining({ message: 'Synthetic chart render failure' }),
  );
  expect(screen.queryByText('Kursverlauf konnte nicht geladen werden.')).not.toBeInTheDocument();
  expect(screen.queryByText(/Keine zeitlich und fachlich/)).not.toBeInTheDocument();

  // jsdom does not implement the native summary Enter/Space toggle. Browser
  // tests cover that behavior; the pagination below still uses real key events.
  await user.click(screen.getByText('Kursdaten und Quellen'));
  const table = screen.getByRole('region', { name: 'Historische Kursdaten' });
  expect(table).toBeVisible();
  expect(within(table).getByText('0,2312345678 USD')).toBeVisible();
  expect(within(table).getAllByRole('row')).toHaveLength(51);
  table.focus();
  expect(table).toHaveFocus();
  await user.tab();
  expect(screen.getByRole('button', { name: 'Weitere Kurspunkte' })).toHaveFocus();
  await user.keyboard('{Enter}');
  expect(screen.getByText('Seite 2 / 2')).toBeVisible();
  expect(within(table).getByText('0,1234567890123456789 EUR')).toBeVisible();
  expect(within(table).getByText('Punkt-ID: original-50')).toBeVisible();

  await user.click(screen.getByText('Kauf- und Verkaufsereignisse'));
  expect(
    screen.getByText('Verkauf · 7 Stück · 0,123456789012345678 Währung unbekannt'),
  ).toBeVisible();
  expect(screen.getByText(/Ausgeführt am 2026-09-09/)).toHaveTextContent('Europe/Berlin');
  expect(screen.getByText('Kein Diagrammmarker: Nur Ausführungsdatum bekannt.')).toBeVisible();
  await user.click(screen.getByText('Buchungsbeleg und Währungsherkunft'));
  expect(screen.getByText('Buchung date-only-sale · Währungsherkunft: UNKNOWN')).toBeVisible();
  expect(report).toEqual(original);
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(1);
});

it.each([
  { name: 'position identity', tradeId: 'trade-2', positionId: 'position-2', reloadToken: 0 },
  { name: 'owner reload', tradeId: 'trade-1', positionId: 'position-1', reloadToken: 1 },
])('resets a chart render failure only with a new $name context', async (next) => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
  const view = render(<PositionPriceHistory tradeId="trade-1" positionId="position-1" />);
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Das Diagramm konnte nicht dargestellt werden',
  );
  chartState.fail = false;
  view.rerender(<PositionPriceHistory tradeId="trade-1" positionId="position-1" />);
  expect(screen.getByRole('alert')).toBeInTheDocument();
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(1);

  vi.mocked(readPositionPriceHistory).mockResolvedValue(
    positionPriceHistory({ trade_id: next.tradeId, position_id: next.positionId }),
  );
  view.rerender(
    <PositionPriceHistory
      tradeId={next.tradeId}
      positionId={next.positionId}
      reloadToken={next.reloadToken}
    />,
  );
  expect(await screen.findByText('Diagramm verfügbar: EUR')).toBeVisible();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(2);
  expect(readPositionPriceHistory).toHaveBeenLastCalledWith(
    next.tradeId,
    next.positionId,
    'all',
    expect.any(AbortSignal),
  );
});
