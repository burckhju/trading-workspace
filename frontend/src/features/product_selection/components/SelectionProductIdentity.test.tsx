import { render, screen } from '@testing-library/react';
import { SelectionProductIdentity } from './SelectionProductIdentity';
import type { WarrantResponse } from '../../product/types/api';
const product = {
  id: 'one',
  display_name: 'Exact product',
  wkn: 'ABC123',
  isin: 'DE000ABC1234',
} as WarrantResponse;
it('names only the exact selected product while keeping technical identity accessible', () => {
  render(<SelectionProductIdentity productId="one" product={product} loading={false} heading />);
  expect(screen.getByRole('heading', { name: 'Exact product' })).toBeInTheDocument();
  expect(screen.getByText(/WKN ABC123/)).toHaveTextContent('DE000ABC1234');
  expect(screen.getByText('Technische Produkt-ID')).toBeInTheDocument();
});
it('rejects another product as a label fallback and distinguishes loading from unavailable', () => {
  const { rerender } = render(
    <SelectionProductIdentity productId="other" product={product} loading={true} />,
  );
  expect(screen.getByText('Produktname wird geladen …')).toBeInTheDocument();
  rerender(<SelectionProductIdentity productId="other" product={product} loading={false} />);
  expect(screen.getByText('Produktname nicht verfügbar')).toBeInTheDocument();
  expect(screen.queryByText('Exact product')).not.toBeInTheDocument();
});
