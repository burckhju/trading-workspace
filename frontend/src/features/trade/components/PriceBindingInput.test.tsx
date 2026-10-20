import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { PriceBinding } from '../types/api';
import { PriceBindingInput } from './PriceBindingInput';

function Form() {
  const [value, setValue] = useState<PriceBinding | null>(null);
  return (
    <>
      <PriceBindingInput
        label="Stop"
        value={value}
        warrantId="warrant-1"
        underlyingId="stock-1"
        onChange={setValue}
      />
      <output>{JSON.stringify(value)}</output>
    </>
  );
}

describe('explicit management price basis', () => {
  it('keeps legacy values unconfirmed and binds the chosen instrument and currency', async () => {
    const user = userEvent.setup();
    render(<Form />);
    expect(screen.getByText(/Kursbezug ungeklärt/)).toBeInTheDocument();
    expect(screen.getByLabelText('Währung für Stop')).toBeDisabled();
    await user.selectOptions(screen.getByLabelText('Instrument für Stop'), 'WARRANT');
    await user.type(screen.getByLabelText('Währung für Stop'), 'eur');
    expect(screen.getByRole('status')).toHaveTextContent('"instrument_id":"warrant-1"');
    expect(screen.getByRole('status')).toHaveTextContent('"currency":"EUR"');
    await user.selectOptions(screen.getByLabelText('Instrument für Stop'), 'UNDERLYING');
    expect(screen.getByRole('status')).toHaveTextContent('"instrument_id":"stock-1"');
    await user.selectOptions(screen.getByLabelText('Instrument für Stop'), '');
    expect(screen.getByRole('status')).toHaveTextContent('null');
    expect(screen.getByText(/Kursbezug ungeklärt/)).toBeInTheDocument();
  });
});
