import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { expect, it, vi } from 'vitest';

import {
  emptyExecutionCurrency,
  executionCurrencyDeclaration,
} from '../services/executionCurrency';
import { ExecutionCurrencyInput } from './ExecutionCurrencyInput';

function Capture({ submit }: { submit: (value: unknown) => void }) {
  const [value, setValue] = useState(emptyExecutionCurrency);
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit(executionCurrencyDeclaration(value));
      }}
    >
      <ExecutionCurrencyInput value={value} onChange={setValue} />
      <button>Speichern</button>
    </form>
  );
}

it('confirms the entered actual currency only through the explicit save action without another checkbox', () => {
  const submit = vi.fn();
  render(<Capture submit={submit} />);
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('');
  fireEvent.change(screen.getByLabelText('Ausführungswährung (Code)'), {
    target: { value: 'eur' },
  });
  expect(submit).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));
  expect(submit).toHaveBeenLastCalledWith({
    currency_confirmation: { currency_code: 'EUR', source: 'USER_CONFIRMED', note: null },
  });
  fireEvent.change(screen.getByLabelText('Beleg / Erläuterung (optional)'), {
    target: { value: 'Abrechnung geprüft' },
  });
  expect(screen.getByLabelText('Beleg / Erläuterung (optional)')).toHaveAttribute(
    'maxlength',
    '1000',
  );
  fireEvent.change(screen.getByLabelText('Ausführungswährung (Code)'), {
    target: { value: 'USD' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));
  expect(submit).toHaveBeenLastCalledWith({
    currency_confirmation: {
      currency_code: 'USD',
      source: 'USER_CONFIRMED',
      note: 'Abrechnung geprüft',
    },
  });
});

it('rejects a nonempty invalid currency instead of silently dropping it and keeps an omitted declaration absent', () => {
  expect(executionCurrencyDeclaration(emptyExecutionCurrency())).toEqual({});
  expect(() => executionCurrencyDeclaration({ code: 'EU', note: '' })).toThrow(
    'dreistelligen Währungscode',
  );
  expect(() => executionCurrencyDeclaration({ code: '', note: 'Abrechnung' })).toThrow(
    'dreistelligen Währungscode',
  );
  expect(executionCurrencyDeclaration({ code: ' usd ', note: '  Abrechnung  ' })).toEqual({
    currency_confirmation: { currency_code: 'USD', source: 'USER_CONFIRMED', note: 'Abrechnung' },
  });
  render(<ExecutionCurrencyInput value={emptyExecutionCurrency()} onChange={vi.fn()} />);
  expect(screen.getByText(/Mit dem Speichern bestätigen Sie diese Angabe/)).toBeVisible();
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
});
