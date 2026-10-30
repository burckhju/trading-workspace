import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { cloneElement, type ReactElement } from 'react';
import type { PositionPriceHistoryReport } from '../positionPriceHistory';
import {
  positionPriceHistory,
  positionPriceSeries,
} from '../../../test/positionPriceHistoryFixtures';
import { readPositionPriceHistory } from '../services/positionPriceHistory';
import { PositionPriceHistory } from './PositionPriceHistory';

vi.mock('../services/positionPriceHistory', () => ({ readPositionPriceHistory: vi.fn() }));
vi.mock('recharts', async (original) => ({
  ...(await original<typeof import('recharts')>()),
  ResponsiveContainer: ({
    children,
  }: {
    children: ReactElement<{ width: number; height: number }>;
  }) => cloneElement(children, { width: 640, height: 288 }),
}));

beforeEach(() => {
  vi.mocked(readPositionPriceHistory).mockReset().mockResolvedValue(positionPriceHistory());
});

function show() {
  return render(<PositionPriceHistory tradeId="trade-1" positionId="position-1" />);
}

it('loads existing-position history automatically and draws one original point without a line', async () => {
  const user = userEvent.setup();
  const rendered = show();
  expect(screen.getByText('Gespeicherte Kurse werden geladen …')).toBeInTheDocument();
  await screen.findByText('Handelswährung: EUR');
  expect(readPositionPriceHistory).toHaveBeenCalledWith(
    'trade-1',
    'position-1',
    'all',
    expect.any(AbortSignal),
  );
  expect(screen.getByLabelText('Zeitraum')).toHaveValue('all');
  expect(rendered.container.querySelectorAll('.recharts-scatter-symbol')).toHaveLength(1);
  expect(rendered.container.querySelector('.recharts-scatter-line')).toBeNull();
  expect(screen.getByText(/Zwischen den Punkten ist kein Kursverlauf belegt/)).toBeInTheDocument();
  await user.click(screen.getByText('Kursdaten und Quellen'));
  const table = screen.getByRole('region', { name: 'Historische Kursdaten' });
  expect(within(table).getByText('0,2312345678 EUR')).toBeInTheDocument();
  expect(table.querySelector('time[datetime="2026-09-08T08:00:00Z"]')).toBeInTheDocument();
  expect(table.querySelector('time[datetime="2026-10-29T12:00:00Z"]')).toBeInTheDocument();
  expect(within(table).getByText(/Quellsegment: original-identity/)).toBeInTheDocument();
  expect(within(table).getByText('Zuletzt erfolgreich gespeicherter Kurs')).toBeInTheDocument();
  expect(within(table).getByText('Bei Erfassung veraltet')).toBeInTheDocument();
});

it('separates currencies, provider changes and price kinds without changing values', async () => {
  vi.mocked(readPositionPriceHistory).mockResolvedValue(
    positionPriceHistory({
      series: [
        positionPriceSeries(),
        positionPriceSeries({
          id: 'new-provider',
          provider: 'FRANKFURT_QUOTES',
          identity_key: 'new-route',
          price_kind: 'LAST_TRADE',
          source_mode: null,
        }),
        positionPriceSeries({ id: 'ask', price_kind: 'ASK' }),
        positionPriceSeries({
          id: 'usd',
          currency: 'USD',
          price_kind: 'PREVIOUS_CLOSE',
          points: [{ ...positionPriceSeries().points[0], price: '100.0001' }],
        }),
      ],
    }),
  );
  const rendered = show();
  const eur = await screen.findByRole('region', { name: 'Kursbeobachtungen EUR' });
  const usd = screen.getByRole('region', { name: 'Kursbeobachtungen USD' });
  expect(within(eur).getByText(/FRANKFURT_QUOTES · Letzter Handel/)).toBeInTheDocument();
  expect(within(eur).getByText(/BOERSE_STUTTGART_DELAYED · Briefkurs/)).toBeInTheDocument();
  expect(within(usd).getByText(/Vorheriger Schlusskurs/)).toBeInTheDocument();
  expect(eur.querySelectorAll('.recharts-scatter-symbol')).toHaveLength(3);
  expect(usd.querySelectorAll('.recharts-scatter-symbol')).toHaveLength(1);
  expect(rendered.container.querySelector('.recharts-scatter-line')).toBeNull();
});

it('explains missing timestamp, failed reads and limits without constructing a chart', async () => {
  vi.mocked(readPositionPriceHistory).mockResolvedValue(
    positionPriceHistory({
      isin: null,
      series: [],
      excluded: { TIMESTAMP_UNKNOWN: 3, REQUEST_FAILED: 1, NO_QUOTE: 0 },
      truncated: true,
      samples_considered: 10000,
      samples_available: 12000,
      collection_started_at: '2026-09-01T12:00:00Z',
    }),
  );
  show();
  await screen.findByText('Keine zeitlich und fachlich zuordenbaren Kursdaten vorhanden.');
  expect(screen.queryByTestId('position-price-chart')).not.toBeInTheDocument();
  expect(screen.getByText('Originalkurszeit unbekannt: 3')).toBeInTheDocument();
  expect(screen.getByText(/Abruf oder Validierung fehlgeschlagen: 1/)).toBeInTheDocument();
  expect(screen.queryByText('Kein Kurs gespeichert: 0')).not.toBeInTheDocument();
  expect(screen.getByText(/10000 von 12000/)).toHaveTextContent('Ältere Belege können fehlen');
  await userEvent.click(screen.getByText('Kauf- und Verkaufsereignisse'));
  expect(screen.getByText(/Keine zuordenbaren Kauf-/)).toBeInTheDocument();
});

it('keeps errors distinct from missing data and supports a read-only retry', async () => {
  vi.mocked(readPositionPriceHistory).mockRejectedValueOnce(new Error('offline'));
  show();
  expect(await screen.findByRole('alert')).toHaveTextContent('Kursverlauf konnte nicht geladen');
  expect(screen.queryByText(/Keine zeitlich und fachlich/)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Kursverlauf erneut laden' }));
  await screen.findByText('Handelswährung: EUR');
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(2);
});

it('loads a chosen original-time window automatically and clears the previous points immediately', async () => {
  const rendered = show();
  await screen.findByText('Handelswährung: EUR');
  let finish!: (value: PositionPriceHistoryReport) => void;
  vi.mocked(readPositionPriceHistory).mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  await userEvent.selectOptions(screen.getByLabelText('Zeitraum'), '7');
  expect(rendered.container.querySelectorAll('.recharts-scatter-symbol')).toHaveLength(0);
  expect(readPositionPriceHistory).toHaveBeenLastCalledWith(
    'trade-1',
    'position-1',
    '7',
    expect.any(AbortSignal),
  );
  await act(async () => {
    finish(positionPriceHistory({ window_start: '2026-10-23T12:00:00Z', series: [] }));
    await Promise.resolve();
  });
  expect(screen.getByText(/23.10.2026, 12:00:00 UTC bis/)).toBeInTheDocument();
});

it('aborts old-position reads and ignores their late results when another detail opens', async () => {
  let finish!: (value: PositionPriceHistoryReport) => void;
  vi.mocked(readPositionPriceHistory).mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  const rendered = show();
  const oldSignal = vi.mocked(readPositionPriceHistory).mock.calls[0][3]!;
  vi.mocked(readPositionPriceHistory).mockResolvedValueOnce(
    positionPriceHistory({ trade_id: 'trade-2', position_id: 'position-2', series: [] }),
  );
  rendered.rerender(<PositionPriceHistory tradeId="trade-2" positionId="position-2" />);
  await screen.findByText('Keine zeitlich und fachlich zuordenbaren Kursdaten vorhanden.');
  expect(oldSignal.aborted).toBe(true);
  await act(async () => {
    finish(positionPriceHistory());
    await Promise.resolve();
  });
  expect(screen.queryByTestId('position-price-chart')).not.toBeInTheDocument();
  const activeSignal = vi.mocked(readPositionPriceHistory).mock.calls[1][3]!;
  rendered.unmount();
  expect(activeSignal.aborted).toBe(true);
});

it('plots only qualified executions and lists date-only or unknown-currency history explicitly', async () => {
  vi.mocked(readPositionPriceHistory).mockResolvedValue(
    positionPriceHistory({
      events: [
        {
          id: 'buy-known',
          side: 'BUY',
          occurred_at: '2026-09-09T08:00:00Z',
          executed_on: null,
          execution_timezone: 'Europe/Berlin',
          price: '0.2',
          currency: 'EUR',
          currency_source: 'USER_CONFIRMED',
          quantity: 100,
          plottable: true,
          reason: null,
        },
        {
          id: 'sell-date',
          side: 'SELL',
          occurred_at: null,
          executed_on: '2026-09-11',
          execution_timezone: 'Europe/Berlin',
          price: '0.25',
          currency: 'EUR',
          currency_source: 'USER_CONFIRMED',
          quantity: 20,
          plottable: false,
          reason: 'DATE_ONLY',
        },
        {
          id: 'sell-unknown-currency',
          side: 'SELL',
          occurred_at: '2026-09-12T08:00:00Z',
          executed_on: null,
          execution_timezone: null,
          price: '0.26',
          currency: null,
          currency_source: 'UNKNOWN',
          quantity: 10,
          plottable: false,
          reason: 'CURRENCY_UNKNOWN',
        },
      ],
    }),
  );
  const rendered = show();
  await screen.findByText('Handelswährung: EUR');
  expect(rendered.container.querySelectorAll('.recharts-scatter-symbol')).toHaveLength(2);
  await userEvent.click(screen.getByText('Kauf- und Verkaufsereignisse'));
  expect(screen.getByText(/Ausgeführt am 2026-09-11/)).toHaveTextContent(
    'Uhrzeit unbekannt · Europe/Berlin',
  );
  expect(
    screen.getByText('Kein Diagrammmarker: Nur Ausführungsdatum bekannt.'),
  ).toBeInTheDocument();
  expect(screen.getByText('Kein Diagrammmarker: Währung nicht belegt.')).toBeInTheDocument();
  expect(screen.getByText('Verkauf · 10 Stück · 0,26 Währung unbekannt')).toBeInTheDocument();
  expect(screen.getByText(/Buchung buy-known/)).toHaveTextContent('USER_CONFIRMED');
});

it('paginates full-precision evidence and resets the table when the window changes', async () => {
  const base = positionPriceSeries().points[0];
  const report = positionPriceHistory({
    series: [
      positionPriceSeries({
        points: Array.from({ length: 51 }, (_, index) => ({
          ...base,
          id: `point-${index}`,
          observed_at: new Date(Date.UTC(2026, 8, index + 1)).toISOString(),
          storage: 'SAMPLE',
          captured_at: '2026-10-30T09:00:00Z',
          quote_time_basis: null,
        })),
      }),
    ],
  });
  vi.mocked(readPositionPriceHistory).mockResolvedValue(report);
  show();
  await screen.findByText('Handelswährung: EUR');
  await userEvent.click(screen.getByText('Kursdaten und Quellen'));
  await userEvent.click(screen.getByRole('button', { name: 'Weitere Kurspunkte' }));
  expect(screen.getByText('Seite 2 / 2')).toBeInTheDocument();
  expect(screen.getByText('Gespeicherte Stichprobe')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Vorige Kurspunkte' }));
  expect(screen.getByText('Seite 1 / 2')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Weitere Kurspunkte' }));
  await userEvent.selectOptions(screen.getByLabelText('Zeitraum'), '31');
  await screen.findByText('Handelswährung: EUR');
  await userEvent.click(screen.getByText('Kursdaten und Quellen'));
  expect(screen.getByText('Seite 1 / 2')).toBeInTheDocument();
});
