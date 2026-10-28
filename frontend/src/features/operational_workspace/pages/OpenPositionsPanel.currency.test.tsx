import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { position } from '../../../test/positionFixture';
import { OpenPositionsPanel } from './OpenPositionsPanel';

beforeEach(() => sessionStorage.clear());

it('shows qualified coverage and missing-currency reasons in rows and details without gain colors', async () => {
  render(
    <MemoryRouter>
      <OpenPositionsPanel
        positions={[
          {
            ...position({ product_name: 'Unbekannte Kaufwährung' }),
            unrealized_pnl_usable: false,
            unrealized_pnl_reason: 'COST_BASIS_CURRENCY_UNKNOWN',
          },
          {
            ...position({ position_id: 'qualified', product_name: 'Belegter Kauf' }),
            unrealized_pnl_usable: true,
            unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
          },
        ]}
      />
    </MemoryRouter>,
  );
  const row = screen.getByRole('row', { name: /Unbekannte Kaufwährung/ });
  expect(within(row).getByText('25,00 EUR')).toBeInTheDocument();
  expect(within(row).queryByText('+5,00 EUR')).not.toBeInTheDocument();
  expect(within(row).getByText('—').closest('td')).toHaveClass('text-slate-300');
  expect(within(row).getByText(/Kaufwährung.*nicht.*belegt/i)).toBeInTheDocument();
  await userEvent.click(screen.getByText(/Bewertungssummen je Währung/));
  expect(screen.getByText('Marktwert: 50,00 EUR · 2/2 bewertet')).toBeInTheDocument();
  expect(
    screen.getByText('Nicht realisierter Brutto-G/V: +5,00 EUR · 1/2 verfügbar'),
  ).toBeInTheDocument();
  await userEvent.click(within(row).getByRole('button', { name: 'Details' }));
  const details = screen.getByRole('region', { name: 'Details Unbekannte Kaufwährung' });
  expect(within(details).getByText(/Kaufwährung.*nicht.*belegt/i)).toBeInTheDocument();
  expect(within(details).getByText('25,00 EUR')).toBeInTheDocument();
  expect(within(details).getByText(/Quelle: TEST_PROVIDER/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Gewinn' }));
  expect(screen.queryByRole('row', { name: /Unbekannte Kaufwährung/ })).not.toBeInTheDocument();
  expect(screen.getByRole('row', { name: /Belegter Kauf/ })).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Verlust' }));
  expect(screen.getByText(/Keine Position entspricht/)).toBeInTheDocument();
});
