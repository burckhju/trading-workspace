import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { OperationalPosition } from '../types';
import { position } from '../../../test/positionFixture';
import { OpenPositionsPanel } from './OpenPositionsPanel';

function show(positions: OperationalPosition[]) {
  return render(
    <MemoryRouter>
      <OpenPositionsPanel positions={positions} />
    </MemoryRouter>,
  );
}
beforeEach(() => sessionStorage.clear());

it('shows readable identifiers, separate colored P/L and explicit status', () => {
  show([position()]);
  expect(screen.getByText('Test Warrant')).toBeInTheDocument();
  expect(screen.getByText(/WKN TEST12/)).toHaveTextContent('DE000TEST1234');
  expect(screen.getByText('✓ Unauffällig')).toHaveClass('text-emerald-200');
  expect(screen.getByText('+5,00 EUR')).toHaveClass('text-emerald-300');
  expect(screen.getByRole('link', { name: 'Verkauf erfassen' })).toHaveAttribute(
    'href',
    '/trade-management?trade_id=trade-1#sale-capture',
  );
  expect(screen.getByRole('link', { name: 'Trade verwalten' })).toHaveAttribute(
    'href',
    '/trade-management?trade_id=trade-1',
  );
});
it('keeps stale price and missing P/L distinct from zero and permits explicit capture', async () => {
  show([position({ valuation_status: 'STALE', market_value: null, unrealized_gross_pnl: null })]);
  expect(screen.getByText('? Daten prüfen')).toBeInTheDocument();
  expect(screen.getByText('Produktkurs: Veraltet')).toBeInTheDocument();
  expect(within(screen.getByRole('table')).getAllByText('—')).toHaveLength(2);
  await userEvent.click(screen.getByRole('button', { name: 'Details' }));
  expect(screen.getByText(/Kursdaten veraltet:/)).toHaveTextContent('Keine Orderfreigabe');
  expect(screen.getByText(/Quelle: TEST_PROVIDER/)).toBeInTheDocument();
  expect(screen.getByText('Monitoring: Aktuell')).toBeInTheDocument();
  expect(
    screen.getByText('Positionssignal: keine besondere Aufmerksamkeit nötig'),
  ).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Details schließen' }));
  expect(screen.queryByRole('region', { name: 'Details Test Warrant' })).not.toBeInTheDocument();
});
it('marks confirmed stop alerts in red even with missing signals and data problems', async () => {
  show([
    position({
      open_alert_count: 1,
      open_alert_types: ['STOP_REACHED'],
      position_signal: null,
      valuation_status: 'MISSING',
    }),
  ]);
  expect(screen.getByText('! Kritischer Hinweis')).toHaveClass('text-rose-200');
  await userEvent.click(screen.getByRole('button', { name: 'Datenprobleme' }));
  expect(
    screen.getByText('1 Treffer von 1 offenen Positionen · Seite 1 von 1'),
  ).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Fachliche Hinweise' }));
  expect(screen.getByRole('table')).toBeInTheDocument();
});
it('warns in blue for indicative quotes and retains negative P/L separately', async () => {
  show([
    position({
      valuation_status: 'INDICATIVE',
      unrealized_gross_pnl: '-558',
      quote_source: 'FRANKFURT_QUOTES',
      analysis_warning: 'INDICATIVE',
    }),
  ]);
  expect(screen.getByText('Produktkurs: Indikativer Referenzkurs')).toHaveClass('text-sky-200');
  expect(screen.getByText('−558,00 EUR')).toHaveClass('text-rose-300');
  await userEvent.click(screen.getByRole('button', { name: 'Details' }));
  expect(screen.getByText(/Indikative Bewertung mit/)).toHaveTextContent('Keine Orderfreigabe');
  expect(screen.getByText(/Quelle: FRANKFURT_QUOTES/)).toBeInTheDocument();
});
it('searches all 100 positions before pagination and keeps the same underlying products distinct', async () => {
  const user = userEvent.setup();
  show(
    Array.from({ length: 100 }, (_, i) =>
      position({
        trade_id: `t-${i}`,
        position_id: `p-${i}`,
        product_name: `Warrant ${String(i).padStart(3, '0')}`,
        product_wkn: `W${i}`,
        product_isin: `ISIN-${i}`,
      }),
    ),
  );
  expect(screen.getByRole('table').querySelectorAll('tbody tr')).toHaveLength(25);
  await user.click(screen.getByRole('button', { name: 'Nächste Seite' }));
  expect(screen.getByText('Warrant 025')).toBeInTheDocument();
  await user.type(screen.getByRole('searchbox'), 'ISIN-99');
  expect(screen.getByText('Warrant 099')).toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent('1 Treffer von 100');
  await user.clear(screen.getByRole('searchbox'));
  await user.type(screen.getByRole('searchbox'), 'Test Underlying W99');
  expect(screen.getByText('Warrant 099')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Ansicht zurücksetzen' }));
  await user.selectOptions(screen.getByLabelText('Zeilen pro Seite'), '100');
  expect(screen.getByRole('table').querySelectorAll('tbody tr')).toHaveLength(100);
});
it('preserves query and sort after returning and resets or clamps stale pages', async () => {
  const user = userEvent.setup();
  const items = [
    position(),
    position({ position_id: 'p2', product_name: 'Another', open_quantity: 20 }),
  ];
  const first = show(items);
  await user.type(screen.getByRole('searchbox'), 'Test');
  await user.selectOptions(screen.getByLabelText('Sortierung'), 'quantity');
  first.unmount();
  const second = show(items);
  expect(screen.getByRole('searchbox')).toHaveValue('Test');
  expect(screen.getByLabelText('Sortierung')).toHaveValue('quantity');
  second.unmount();
});
it('sorts using native accessible headers, filters P/L without turning missing into a loss', async () => {
  const user = userEvent.setup();
  show([
    position(),
    position({ position_id: 'p2', product_name: 'Loss', unrealized_gross_pnl: '-2' }),
    position({ position_id: 'p3', product_name: 'Missing', unrealized_gross_pnl: null }),
  ]);
  await user.click(screen.getByRole('button', { name: /^Nicht realisierter G\/V/ }));
  expect(screen.getByRole('columnheader', { name: /Nicht realisierter G\/V/ })).toHaveAttribute(
    'aria-sort',
    'ascending',
  );
  await user.click(screen.getByRole('button', { name: /^Nicht realisierter G\/V/ }));
  expect(screen.getByRole('columnheader', { name: /Nicht realisierter G\/V/ })).toHaveAttribute(
    'aria-sort',
    'descending',
  );
  await user.click(screen.getByRole('button', { name: 'Verlust' }));
  expect(screen.getByText('Loss')).toBeInTheDocument();
  expect(screen.queryByText('Missing')).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Gewinn' }));
  expect(screen.getByText('Test Warrant')).toBeInTheDocument();
  expect(screen.queryByText('Loss')).not.toBeInTheDocument();
});
it('shows currency-specific covered totals and unknown values honestly', async () => {
  show([
    position({ market_value: '0.1' }),
    position({ position_id: 'p2', market_value: '0.2', valuation_status: 'INDICATIVE' }),
    position({ position_id: 'p3', valuation_currency: 'CHF', market_value: '100' }),
    position({ position_id: 'p4', market_value: null, unrealized_gross_pnl: null }),
    position({ position_id: 'p5', valuation_currency: null }),
  ]);
  await userEvent.click(screen.getByText(/Bewertungssummen je Währung/));
  expect(screen.getByText('Marktwert: 0,30 EUR · 2/3 bewertet')).toBeInTheDocument();
  expect(screen.getByText('Marktwert: 100,00 CHF · 1/1 bewertet')).toBeInTheDocument();
  expect(screen.getByText('Marktwert: — · 0/1 bewertet')).toBeInTheDocument();
});
it('handles empty results and no positions', async () => {
  const first = show([]);
  expect(screen.getByText('Keine offenen Positionen vorhanden.')).toBeInTheDocument();
  first.unmount();
  show([position()]);
  await userEvent.type(screen.getByRole('searchbox'), 'not-found');
  expect(
    screen.getByText('Keine Position entspricht der Suche und dem Filter.'),
  ).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Nächste Seite' })).toBeDisabled();
});
