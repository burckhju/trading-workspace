import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { PositionValuationBasis } from '../types/api';
import { PositionValuationBasisDetails } from './PositionValuationBasisDetails';

const basis: PositionValuationBasis = {
  definition_version: 'position-unrealized-gross-v1',
  basis_id: 'exact-basis-id',
  position: {
    id: 'position-1',
    trade_id: 'trade-1',
    product_id: 'product-1',
    open_quantity: 10,
    cost_basis: '20',
    average_entry_price: '2',
    realized_gross_pnl: '0',
    opened_at: '2026-10-27T10:00:00Z',
    last_execution_at: '2026-10-27T10:00:00Z',
    closed_at: null,
  },
  cost_basis_currency: 'USD',
  currency_status: 'KNOWN',
  effective_execution_ids: ['effective-buy', 'effective-sale'],
  buy_currency_evidence: [
    {
      execution_id: 'effective-buy',
      currency_code: 'USD',
      source: 'REPLACED_EXECUTION',
      source_execution_ids: ['original-buy'],
      confirmation_ids: ['exact-confirmation'],
    },
  ],
};

it('exposes the exact backend basis, execution and confirmation references without a quote currency substitution', async () => {
  render(<PositionValuationBasisDetails basis={basis} />);
  await userEvent.click(screen.getByText('Kostenbasis und Währungsnachweise'));
  expect(screen.getByText('Kostenbasiswährung: USD')).toBeVisible();
  expect(screen.getByText(/Bewertungsdefinition:/)).toHaveTextContent(
    'position-unrealized-gross-v1 · Lesebasis: exact-basis-id',
  );
  expect(screen.getByText(/Wirksame Ausführungen:/)).toHaveTextContent(
    'effective-buy, effective-sale',
  );
  expect(screen.getByRole('listitem')).toHaveTextContent('Kauf effective-buy: USD');
  expect(screen.getByRole('listitem')).toHaveTextContent('Aus der korrigierten Ausführung belegt');
  expect(screen.getByRole('listitem')).toHaveTextContent('Quellausführungen: original-buy');
  expect(screen.getByRole('listitem')).toHaveTextContent('Bestätigungen: exact-confirmation');
});

it.each([
  ['UNKNOWN', 'Nicht vollständig belegt'],
  ['MIXED', 'Unterschiedliche Kaufwährungen'],
] as const)('keeps the %s basis visibly unqualified', async (currency_status, label) => {
  render(
    <PositionValuationBasisDetails
      basis={{
        ...basis,
        currency_status,
        cost_basis_currency: null,
        buy_currency_evidence: [
          {
            execution_id: 'effective-buy',
            currency_code: null,
            source: currency_status,
            source_execution_ids: [],
            confirmation_ids: [],
          },
        ],
      }}
    />,
  );
  await userEvent.click(screen.getByText('Kostenbasis und Währungsnachweise'));
  expect(screen.getByText(`Kostenbasiswährung: ${label}`)).toBeVisible();
  expect(screen.getByRole('listitem')).toHaveTextContent('Währung nicht belegt');
  expect(screen.getByRole('listitem')).toHaveTextContent('Bestätigungen: Keine');
});

it('does not invent basis references when the backend could not provide them', () => {
  const { container } = render(<PositionValuationBasisDetails basis={null} />);
  expect(container).toBeEmptyDOMElement();
});
