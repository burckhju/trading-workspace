import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { cloneElement, type ReactElement } from 'react';
import type { PositionPriceEvent, PositionPriceHistoryReport } from '../positionPriceHistory';
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
  expect(rendered.container.querySelector('.recharts-yAxis')).not.toHaveTextContent('EUR');
  expect(screen.getByText(/Zwischen den Punkten ist kein Kursverlauf belegt/)).toBeInTheDocument();
  await user.click(screen.getByText('Kursdaten und Quellen'));
  const table = screen.getByRole('region', { name: 'Historische Kursdaten' });
  expect(within(table).getByText('0,2312345678 EUR')).toBeInTheDocument();
  expect(table.querySelector('time[datetime="2026-09-08T08:00:00Z"]')).toBeInTheDocument();
  expect(table.querySelector('time[datetime="2026-10-29T12:00:00Z"]')).toBeInTheDocument();
  expect(within(table).getByText(/Quellsegment: original-identity/)).toBeInTheDocument();
  expect(within(table).getByText(/Handelsplatz: XSTU \(MIC\)/)).toHaveTextContent(
    'Providersegment: _STU',
  );
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
  expect(
    within(within(usd).getByRole('list', { name: 'Kursquellen USD' })).getByText(
      /Vorheriger Schlusskurs/,
    ),
  ).toBeInTheDocument();
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
  vi.mocked(readPositionPriceHistory).mockResolvedValueOnce(
    positionPriceHistory({
      series: [
        positionPriceSeries({
          points: [{ ...positionPriceSeries().points[0], observed_at: '2026-10-29T08:00:00Z' }],
        }),
      ],
    }),
  );
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

it('only offers short windows containing proven original prices, including old closed-position evidence', async () => {
  show();
  await screen.findByText('Handelswährung: EUR');
  expect(screen.getByRole('option', { name: 'Alle gespeicherten Kurse' })).toBeEnabled();
  expect(screen.getByRole('option', { name: '7 Tage' })).toBeDisabled();
  expect(screen.getByRole('option', { name: '31 Tage' })).toBeDisabled();
  expect(screen.getByRole('option', { name: '90 Tage' })).toBeEnabled();
  await userEvent.selectOptions(screen.getByLabelText('Zeitraum'), '7');
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText('Zeitraum')).toHaveValue('all');
});

it('does not offer any short window for empty history or while the initial read is pending', async () => {
  let finish!: (value: PositionPriceHistoryReport) => void;
  vi.mocked(readPositionPriceHistory).mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  show();
  for (const name of ['7 Tage', '31 Tage', '90 Tage'])
    expect(screen.getByRole('option', { name })).toBeDisabled();
  await act(async () => {
    finish(positionPriceHistory({ series: [] }));
    await Promise.resolve();
  });
  for (const name of ['7 Tage', '31 Tage', '90 Tage'])
    expect(screen.getByRole('option', { name })).toBeDisabled();
});

it('retains known available windows across a narrow response and ignores its late result after refresh', async () => {
  vi.mocked(readPositionPriceHistory).mockResolvedValueOnce(
    positionPriceHistory({
      series: [
        positionPriceSeries({
          points: [{ ...positionPriceSeries().points[0], observed_at: '2026-10-29T08:00:00Z' }],
        }),
      ],
    }),
  );
  const rendered = show();
  await screen.findByText('Handelswährung: EUR');
  let finish!: (value: PositionPriceHistoryReport) => void;
  vi.mocked(readPositionPriceHistory).mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  await userEvent.selectOptions(screen.getByLabelText('Zeitraum'), '7');
  const narrowSignal = vi.mocked(readPositionPriceHistory).mock.calls[1][3]!;
  expect(screen.getByRole('option', { name: '31 Tage' })).toBeEnabled();
  vi.mocked(readPositionPriceHistory).mockResolvedValueOnce(positionPriceHistory({ series: [] }));
  rendered.rerender(
    <PositionPriceHistory tradeId="trade-1" positionId="position-1" reloadToken={1} />,
  );
  await screen.findByText('Keine zeitlich und fachlich zuordenbaren Kursdaten vorhanden.');
  expect(narrowSignal.aborted).toBe(true);
  expect(screen.getByLabelText('Zeitraum')).toHaveValue('all');
  expect(screen.getByRole('option', { name: '31 Tage' })).toBeDisabled();
  await act(async () => {
    finish(positionPriceHistory());
    await Promise.resolve();
  });
  expect(screen.queryByTestId('position-price-chart')).not.toBeInTheDocument();
});

it('labels original venues and unknown or issuer-only identities without inventing an exchange', async () => {
  vi.mocked(readPositionPriceHistory).mockResolvedValueOnce(
    positionPriceHistory({
      series: [
        positionPriceSeries(),
        positionPriceSeries({ id: 'frankfurt', venue_mic: 'XFRA', provider_exchange_code: '_FRA' }),
        positionPriceSeries({ id: 'issuer', venue_mic: null, provider_exchange_code: 'ISSUER' }),
        positionPriceSeries({ id: 'unknown', venue_mic: null, provider_exchange_code: null }),
      ],
    }),
  );
  show();
  const plot = await screen.findByRole('region', { name: 'Kursbeobachtungen EUR' });
  expect(
    within(plot).getByText('Handelsplatz: XSTU (MIC) · Providersegment: _STU'),
  ).toBeInTheDocument();
  expect(
    within(plot).getByText('Handelsplatz: XFRA (MIC) · Providersegment: _FRA'),
  ).toBeInTheDocument();
  expect(
    within(plot).getByText('Emittentenquelle · kein Börsenhandelsplatz · Providersegment: ISSUER'),
  ).toBeInTheDocument();
  expect(within(plot).getByText('Handelsplatz nicht belegt')).toBeInTheDocument();
  expect(within(plot).queryByText('Handelsplatz: ISSUER (MIC)')).not.toBeInTheDocument();
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

it('reserves the buy triangle and sell cross for executions even with five market series', async () => {
  const point = positionPriceSeries().points[0];
  vi.mocked(readPositionPriceHistory).mockResolvedValueOnce(
    positionPriceHistory({
      series: Array.from({ length: 5 }, (_, index) =>
        positionPriceSeries({ id: `market-${index}` }),
      ),
      events: (['BUY', 'SELL'] as const).map((side) => ({
        id: side,
        side,
        occurred_at: point.observed_at,
        executed_on: null,
        execution_timezone: 'UTC',
        price: point.price,
        currency: 'EUR',
        currency_source: 'USER_CONFIRMED',
        quantity: 1,
        plottable: true,
        reason: null,
      })),
    }),
  );
  const rendered = show();
  await screen.findByText('Handelswährung: EUR');
  const paths = [...rendered.container.querySelectorAll('.recharts-scatter-symbol path')];
  expect(paths).toHaveLength(7);
  for (const marketPoint of paths.slice(0, 5)) {
    expect(marketPoint.getAttribute('d')).not.toBe(paths[5].getAttribute('d'));
    expect(marketPoint.getAttribute('d')).not.toBe(paths[6].getAttribute('d'));
  }
  expect(screen.getByText(/Dreieck grün: Kauf. Kreuz rosa: Verkauf./)).toBeInTheDocument();
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

it('filters only the displayed series by exact historical ID and keeps original evidence', async () => {
  const user = userEvent.setup();
  vi.mocked(readPositionPriceHistory).mockResolvedValue(
    positionPriceHistory({
      series: [
        positionPriceSeries({ id: 'source-a', identity_key: 'route-a' }),
        positionPriceSeries({ id: 'source-b', identity_key: 'route-b', price_kind: 'ASK' }),
      ],
    }),
  );
  const rendered = show();
  await screen.findByRole('group', { name: 'Kursquellen EUR auswählen' });
  expect(rendered.container.querySelectorAll('.recharts-scatter-symbol')).toHaveLength(2);
  await user.click(screen.getByRole('checkbox', { name: /Quelle 1:/ }));
  expect(rendered.container.querySelectorAll('.recharts-scatter-symbol')).toHaveLength(1);
  expect(screen.getByText(/1 von 2 gelieferten Marktkurspunkten/)).toBeInTheDocument();
  await user.click(screen.getByRole('checkbox', { name: /Quelle 2:/ }));
  expect(screen.getByRole('status')).toHaveTextContent('Alle Kursquellen');
  expect(screen.queryByTestId('position-price-chart')).not.toBeInTheDocument();
  await user.click(screen.getByText('Kursdaten und Quellen'));
  const table = screen.getByRole('region', { name: 'Historische Kursdaten' });
  expect(within(table).getByText(/Quellsegment: route-a/)).toBeInTheDocument();
  expect(within(table).getByText(/Quellsegment: route-b/)).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Alle Kursquellen anzeigen' }));
  expect(rendered.container.querySelectorAll('.recharts-scatter-symbol')).toHaveLength(2);
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(1);
});

it('does not transfer hidden sources to another position or reload identity', async () => {
  const user = userEvent.setup();
  vi.mocked(readPositionPriceHistory).mockResolvedValue(
    positionPriceHistory({
      series: [
        positionPriceSeries({ id: 'source-a', identity_key: 'route-a' }),
        positionPriceSeries({ id: 'source-b', identity_key: 'route-b' }),
      ],
    }),
  );
  const rendered = show();
  await screen.findByRole('group', { name: 'Kursquellen EUR auswählen' });
  await user.click(screen.getByRole('checkbox', { name: /Quelle 1:/ }));
  expect(screen.getByRole('checkbox', { name: /Quelle 1:/ })).not.toBeChecked();
  rendered.rerender(<PositionPriceHistory tradeId="trade-2" positionId="position-2" />);
  await screen.findByRole('group', { name: 'Kursquellen EUR auswählen' });
  expect(screen.getByRole('checkbox', { name: /Quelle 1:/ })).toBeChecked();
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(2);
  await user.click(screen.getByRole('checkbox', { name: /Quelle 1:/ }));
  rendered.rerender(
    <PositionPriceHistory tradeId="trade-2" positionId="position-2" reloadToken={1} />,
  );
  await screen.findByRole('group', { name: 'Kursquellen EUR auswählen' });
  expect(screen.getByRole('checkbox', { name: /Quelle 1:/ })).toBeChecked();
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(3);
});

function execution(overrides: Partial<PositionPriceEvent> = {}): PositionPriceEvent {
  return {
    id: 'buy-evidence',
    side: 'BUY',
    occurred_at: positionPriceSeries().points[0].observed_at,
    executed_on: null,
    execution_timezone: 'Europe/Berlin',
    price: '0.231234567800000001',
    currency: 'EUR',
    currency_source: 'USER_CONFIRMED',
    quantity: 10,
    plottable: true,
    reason: null,
    ...overrides,
  };
}

it('keeps qualified execution markers and unfiltered evidence when every source is hidden', async () => {
  const user = userEvent.setup();
  const report = positionPriceHistory({
    series: [positionPriceSeries(), positionPriceSeries({ id: 'dollars', currency: 'USD' })],
    events: [
      execution(),
      execution({ id: 'usd-sale', side: 'SELL', currency: 'USD' }),
      execution({
        id: 'date-only',
        side: 'SELL',
        occurred_at: null,
        executed_on: '2026-09-09',
        plottable: false,
        reason: 'DATE_ONLY',
      }),
    ],
  });
  const original = structuredClone(report);
  vi.mocked(readPositionPriceHistory).mockResolvedValue(report);
  show();
  const euros = await screen.findByRole('region', { name: 'Kursbeobachtungen EUR' });
  const dollars = screen.getByRole('region', { name: 'Kursbeobachtungen USD' });
  await user.click(within(euros).getByRole('checkbox'));
  await user.click(within(dollars).getByRole('checkbox'));
  expect(screen.getByRole('status')).toHaveTextContent('Alle Kursquellen');
  expect(screen.getByText(/0 von 2 gelieferten Marktkurspunkten/)).toBeInTheDocument();
  expect(euros.querySelectorAll('.recharts-scatter-symbol')).toHaveLength(1);
  expect(dollars.querySelectorAll('.recharts-scatter-symbol')).toHaveLength(1);
  expect(screen.queryByText(/Keine zeitlich und fachlich/)).not.toBeInTheDocument();
  await user.click(screen.getByText('Kauf- und Verkaufsereignisse'));
  expect(screen.getByText('Kauf · 10 Stück · 0,231234567800000001 EUR')).toBeInTheDocument();
  expect(screen.getByText('Verkauf · 10 Stück · 0,231234567800000001 USD')).toBeInTheDocument();
  expect(
    screen.getByText('Kein Diagrammmarker: Nur Ausführungsdatum bekannt.'),
  ).toBeInTheDocument();
  await user.click(screen.getByText('Kursdaten und Quellen'));
  expect(screen.getByRole('table')).toHaveTextContent('0,2312345678 EUR');
  expect(screen.getByRole('table')).toHaveTextContent('0,2312345678 USD');
  await user.click(screen.getByRole('button', { name: 'Alle Kursquellen anzeigen' }));
  expect(euros.querySelectorAll('.recharts-scatter-symbol')).toHaveLength(2);
  expect(dollars.querySelectorAll('.recharts-scatter-symbol')).toHaveLength(2);
  expect(report).toEqual(original);
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(1);
});

it('can restore the sole remaining source after a window change without another read', async () => {
  const user = userEvent.setup();
  const recent = positionPriceSeries({
    points: [{ ...positionPriceSeries().points[0], observed_at: '2026-10-29T08:00:00Z' }],
  });
  vi.mocked(readPositionPriceHistory)
    .mockResolvedValueOnce(
      positionPriceHistory({ series: [recent, positionPriceSeries({ id: 'older' })] }),
    )
    .mockResolvedValueOnce(positionPriceHistory({ series: [recent] }));
  show();
  await screen.findByRole('group', { name: 'Kursquellen EUR auswählen' });
  await user.click(screen.getByRole('checkbox', { name: /Quelle 1:/ }));
  await user.selectOptions(screen.getByLabelText('Zeitraum'), '7');
  await screen.findByRole('status');
  const restore = screen.getByRole('button', { name: 'Alle Kursquellen anzeigen' });
  expect(restore).toBeEnabled();
  restore.focus();
  await user.keyboard('{Enter}');
  expect(restore).toHaveFocus();
  expect(screen.getByRole('checkbox', { name: /Quelle 1:/ })).toBeChecked();
  expect(screen.getByText(/1 von 1 gelieferten Marktkurspunkten/)).toBeInTheDocument();
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(2);
});

it('isolates A to B to A including stale success and failure after the current response', async () => {
  const resolvers: Array<{
    resolve: (report: PositionPriceHistoryReport) => void;
    reject: (error: Error) => void;
  }> = [];
  vi.mocked(readPositionPriceHistory).mockImplementation(
    () =>
      new Promise((resolve, reject) => {
        resolvers.push({ resolve, reject });
      }),
  );
  const rendered = show();
  rendered.rerender(<PositionPriceHistory tradeId="trade-b" positionId="position-b" />);
  rendered.rerender(<PositionPriceHistory tradeId="trade-1" positionId="position-1" />);
  await act(async () => {
    resolvers[2].resolve(
      positionPriceHistory({
        series: [positionPriceSeries({ provider: 'CURRENT_A' })],
        events: [execution({ id: 'current-a-event' })],
      }),
    );
    await Promise.resolve();
  });
  await screen.findByRole('checkbox', { name: /CURRENT_A/ });
  await act(async () => {
    resolvers[0].resolve(
      positionPriceHistory({
        series: [positionPriceSeries({ provider: 'OBSOLETE_A' })],
        events: [execution({ id: 'obsolete-a-event' })],
      }),
    );
    resolvers[1].reject(new Error('obsolete B failure'));
    await Promise.resolve();
  });
  expect(screen.queryByText(/OBSOLETE_A/)).not.toBeInTheDocument();
  expect(screen.queryByText(/obsolete-a-event/)).not.toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(screen.getByRole('checkbox', { name: /CURRENT_A/ })).toBeChecked();
  expect(vi.mocked(readPositionPriceHistory).mock.calls[0][3]?.aborted).toBe(true);
  expect(vi.mocked(readPositionPriceHistory).mock.calls[1][3]?.aborted).toBe(true);
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(3);
});

it('keeps fourteen exact source identities and their shapes stable while reserving execution symbols', async () => {
  const user = userEvent.setup();
  vi.mocked(readPositionPriceHistory).mockResolvedValue(
    positionPriceHistory({
      series: Array.from({ length: 14 }, (_, index) =>
        positionPriceSeries({
          id: `exact-source-${index}`,
          identity_key: `historical-route-${index}`,
          source_mode: index % 2 ? 'OFFICIAL_ISSUER_INDICATION' : 'DELAYED',
          price_kind: (['BID', 'ASK', 'LAST_TRADE', 'PREVIOUS_CLOSE'] as const)[index % 4],
          venue_mic: index % 3 ? null : 'XSTU',
          provider_exchange_code: index % 3 === 1 ? 'ISSUER' : null,
        }),
      ),
      events: [execution(), execution({ id: 'sale', side: 'SELL' })],
    }),
  );
  const rendered = show();
  await screen.findByText('Handelswährung: EUR');
  expect(screen.getAllByRole('checkbox')[0]).not.toBeVisible();
  const toggle = screen.getByText('Kursquellen EUR ein-/ausblenden (14)');
  toggle.focus();
  await user.keyboard('{Enter}');
  expect(screen.getAllByRole('checkbox')).toHaveLength(14);
  const geometry = () =>
    [...rendered.container.querySelectorAll('.recharts-scatter-symbol path')].map((path) => ({
      fill: path.getAttribute('fill'),
      shape: path.getAttribute('d'),
    }));
  const before = geometry();
  expect(before).toHaveLength(16);
  for (const mark of before.slice(0, 14)) {
    expect(mark.shape).not.toBe(before[14].shape);
    expect(mark.shape).not.toBe(before[15].shape);
  }
  const first = screen.getByRole('checkbox', { name: /Quelle 1:/ });
  first.focus();
  await user.keyboard(' ');
  expect(first).not.toBeChecked();
  expect(geometry()).toEqual(before.slice(1));
  expect(screen.getByRole('checkbox', { name: /Quelle 14:/ })).toBeChecked();
  expect(screen.getByText(/13 von 14 gelieferten Marktkurspunkten/)).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Alle Kursquellen anzeigen' }));
  // Recharts may append a remounted series in its SVG paint order. Its actual
  // color/shape and every other original symbol must nevertheless be preserved.
  expect(
    geometry()
      .map((mark) => JSON.stringify(mark))
      .sort(),
  ).toEqual(before.map((mark) => JSON.stringify(mark)).sort());
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(1);
});

it('opens each overlapping market and execution original by exact identity, even when plot decimals coincide', async () => {
  const user = userEvent.setup();
  const point = positionPriceSeries().points[0];
  const report = positionPriceHistory({
    series: [
      positionPriceSeries({
        id: 'a:b',
        points: [{ ...point, id: 'c', price: '0.231234567800000001' }],
      }),
      positionPriceSeries({
        id: 'a',
        points: [{ ...point, id: 'b:c', price: '0.231234567800000002' }],
      }),
    ],
    events: [execution(), execution({ id: 'sell-evidence', side: 'SELL', quantity: 3 })],
  });
  const original = structuredClone(report);
  vi.mocked(readPositionPriceHistory).mockResolvedValue(report);
  const rendered = show();
  const plot = await screen.findByRole('region', { name: 'Kursbeobachtungen EUR' });
  expect(plot.querySelectorAll('.recharts-scatter-symbol')).toHaveLength(4);
  fireEvent.click(plot.querySelectorAll('.recharts-scatter-symbol')[3]);
  const overlap = await screen.findByRole('heading', { name: 'Belege an diesem Diagrammpunkt: 4' });
  expect(overlap).toHaveFocus();
  const chooser = screen.getByRole('list', { name: 'Einzelbelege EUR' });
  expect(within(chooser).getAllByRole('button')).toHaveLength(4);
  await user.click(within(chooser).getByRole('button', { name: /Quelle 2, Kurspunkt 1:/ }));
  const card = screen.getByRole('region', { name: 'Ausgewählter Originalkursbeleg' });
  await waitFor(() => expect(card).toHaveFocus());
  expect(card).toHaveTextContent('0,231234567800000002 EUR');
  await user.click(within(card).getByText('Technische Angaben zum ausgewählten Kursbeleg'));
  expect(within(card).getByText('Serien-ID: a')).toBeInTheDocument();
  expect(within(card).getByText('Punkt-ID: b:c')).toBeInTheDocument();
  await user.click(within(chooser).getByRole('button', { name: /Quelle 1, Kurspunkt 1:/ }));
  const firstCard = screen.getByRole('region', { name: 'Ausgewählter Originalkursbeleg' });
  expect(firstCard).toHaveFocus();
  expect(firstCard).toHaveTextContent('0,231234567800000001 EUR');
  await user.click(within(firstCard).getByText('Technische Angaben zum ausgewählten Kursbeleg'));
  expect(within(firstCard).getByText('Serien-ID: a:b')).toBeVisible();
  expect(within(firstCard).getByText('Punkt-ID: c')).toBeVisible();
  await user.click(within(chooser).getByRole('button', { name: /Verkauf, Buchung 2/ }));
  const event = screen.getByText('Verkauf · 3 Stück · 0,231234567800000001 EUR').closest('li');
  expect(event).toHaveFocus();
  expect(event).toHaveTextContent('Buchung sell-evidence');
  expect(event).toHaveTextContent('Währungsherkunft: USER_CONFIRMED');
  expect(event).toHaveTextContent('Zeitzone des Belegs: Europe/Berlin');
  await user.click(screen.getByRole('button', { name: 'Alle angezeigten Punkte auswählen' }));
  expect(screen.getByRole('heading', { name: 'Angezeigte Punkte und Buchungen: 4' })).toHaveFocus();
  expect(rendered.container.querySelectorAll('.recharts-scatter-symbol')).toHaveLength(4);
  expect(report).toEqual(original);
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(1);
});

it('opens the exact original on the second evidence page and can reopen the same target by keyboard', async () => {
  const user = userEvent.setup();
  const base = positionPriceSeries().points[0];
  vi.mocked(readPositionPriceHistory).mockResolvedValue(
    positionPriceHistory({
      series: [
        positionPriceSeries({
          points: Array.from({ length: 51 }, (_, index) => ({
            ...base,
            id: `original-${index}`,
            observed_at: new Date(Date.UTC(2026, 8, 8, 8, index)).toISOString(),
            price: index === 50 ? '0.1234567890123456789' : base.price,
          })),
        }),
      ],
    }),
  );
  show();
  await screen.findByText('Handelswährung: EUR');
  const summary = screen.getByText('Punkte und Buchungen auswählen (EUR)');
  summary.focus();
  await user.keyboard(' ');
  await user.click(screen.getByRole('button', { name: 'Weitere Einzelbelege' }));
  await user.click(screen.getByRole('button', { name: 'Weitere Einzelbelege' }));
  const target = screen.getByRole('button', { name: /Quelle 1, Kurspunkt 51:/ });
  target.focus();
  await user.keyboard('{Enter}');
  const card = screen.getByRole('region', { name: 'Ausgewählter Originalkursbeleg' });
  expect(card).toHaveFocus();
  expect(card).toHaveTextContent('0,1234567890123456789 EUR');
  const table = screen.getByRole('region', { name: 'Historische Kursdaten' });
  expect(within(table).getAllByRole('row')).toHaveLength(2);
  expect(table).toHaveTextContent('Punkt-ID: original-50');
  expect(screen.getByText('Seite 2 / 2')).toBeInTheDocument();
  await user.click(screen.getByText('Kursdaten und Quellen'));
  expect(screen.getByRole('region', { name: 'Ausgewählter Originalkursbeleg' })).not.toBeVisible();
  target.focus();
  await user.keyboard(' ');
  expect(screen.getByRole('region', { name: 'Ausgewählter Originalkursbeleg' })).toHaveFocus();
  expect(screen.getByText('Seite 2 / 2')).toBeInTheDocument();
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(1);
});

it('retains date-only events when no market point is available and cannot enable a recent window from them', async () => {
  vi.mocked(readPositionPriceHistory).mockResolvedValue(
    positionPriceHistory({
      series: [],
      events: [
        execution({
          occurred_at: null,
          executed_on: '2026-10-29',
          plottable: false,
          reason: 'DATE_ONLY',
        }),
      ],
    }),
  );
  show();
  await screen.findByText('Keine zeitlich und fachlich zuordenbaren Kursdaten vorhanden.');
  expect(screen.queryByTestId('position-price-chart')).not.toBeInTheDocument();
  expect(screen.getByRole('option', { name: '7 Tage' })).toBeDisabled();
  await userEvent.click(screen.getByText('Kauf- und Verkaufsereignisse'));
  expect(screen.getByText(/Ausgeführt am 2026-10-29/)).toBeInTheDocument();
  expect(screen.getByText('Präzision: Datum ohne Uhrzeit')).toBeInTheDocument();
  expect(
    screen.getByText('Kein Diagrammmarker: Nur Ausführungsdatum bekannt.'),
  ).toBeInTheDocument();
});

it('preserves an original decimal outside finite plotting range and explains the drawing limit', async () => {
  const price = '9'.repeat(400);
  vi.mocked(readPositionPriceHistory).mockResolvedValue(
    positionPriceHistory({
      series: [positionPriceSeries({ points: [{ ...positionPriceSeries().points[0], price }] })],
    }),
  );
  show();
  await screen.findByText('Handelswährung: EUR');
  expect(
    screen.getByText(/1 ausgewählte Belege lassen sich nicht als endliche/),
  ).toBeInTheDocument();
  expect(screen.queryByTestId('position-price-chart')).not.toBeInTheDocument();
  await userEvent.click(screen.getByText('Kursdaten und Quellen'));
  expect(screen.getByRole('table')).toHaveTextContent(`${price} EUR`);
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(1);
});

it('starts a newly selected overlap group on its first page after clearing an earlier group', async () => {
  const user = userEvent.setup();
  vi.mocked(readPositionPriceHistory).mockResolvedValue(
    positionPriceHistory({
      series: Array.from({ length: 21 }, (_, index) =>
        positionPriceSeries({ id: `source-${index}` }),
      ),
    }),
  );
  const rendered = show();
  await screen.findByText('Handelswährung: EUR');
  const point = rendered.container.querySelector('.recharts-scatter-symbol')!;
  fireEvent.click(point);
  await screen.findByRole('heading', { name: 'Belege an diesem Diagrammpunkt: 21' });
  await user.click(screen.getByRole('button', { name: 'Weitere Einzelbelege' }));
  expect(screen.getByText('Auswahlseite 2 / 2')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Alle angezeigten Punkte auswählen' }));
  fireEvent.click(point);
  expect(screen.getByText('Auswahlseite 1 / 2')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Quelle 1, Kurspunkt 1:/ })).toBeVisible();
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(1);
});
