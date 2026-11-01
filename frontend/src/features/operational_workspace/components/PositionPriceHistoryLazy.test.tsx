import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { positionPriceHistory } from '../../../test/positionPriceHistoryFixtures';
import { readPositionPriceHistory } from '../services/positionPriceHistory';
import { PositionPriceHistory } from './PositionPriceHistory';

vi.mock('../services/positionPriceHistory', () => ({ readPositionPriceHistory: vi.fn() }));
vi.mock('./PositionPricePlot', () => {
  throw new Error('Synthetic unavailable chart chunk');
});

it('keeps complete original evidence and event reasons accessible when the optional chart cannot load', async () => {
  const user = userEvent.setup();
  vi.mocked(readPositionPriceHistory).mockResolvedValue(
    positionPriceHistory({
      events: [
        {
          id: 'date-only-sale',
          side: 'SELL',
          occurred_at: null,
          executed_on: '2026-09-09',
          execution_timezone: 'Europe/Berlin',
          price: '0.123456789012345678',
          currency: 'EUR',
          currency_source: 'USER_CONFIRMED',
          quantity: 7,
          plottable: false,
          reason: 'DATE_ONLY',
        },
      ],
    }),
  );
  render(<PositionPriceHistory tradeId="trade-1" positionId="position-1" />);
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Das Diagramm konnte nicht geladen werden',
  );
  expect(screen.queryByText('Kursverlauf konnte nicht geladen werden.')).not.toBeInTheDocument();
  await user.click(screen.getByText('Kursdaten und Quellen'));
  expect(
    within(screen.getByRole('region', { name: 'Historische Kursdaten' })).getByText(
      '0,2312345678 EUR',
    ),
  ).toBeInTheDocument();
  await user.click(screen.getByText('Kauf- und Verkaufsereignisse'));
  expect(screen.getByText('Verkauf · 7 Stück · 0,123456789012345678 EUR')).toBeInTheDocument();
  expect(screen.getByText(/Ausgeführt am 2026-09-09/)).toHaveTextContent('Europe/Berlin');
  expect(
    screen.getByText('Kein Diagrammmarker: Nur Ausführungsdatum bekannt.'),
  ).toBeInTheDocument();
  expect(readPositionPriceHistory).toHaveBeenCalledTimes(1);
});
