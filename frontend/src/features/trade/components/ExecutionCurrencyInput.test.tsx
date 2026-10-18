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

it('does not turn a suggested or typed code into a fact and resets the affirmation when its evidence changes', () => {
  const submit = vi.fn();
  render(<Capture submit={submit} />);
  expect(screen.getByRole('checkbox')).not.toBeChecked();
  expect(screen.getByRole('checkbox')).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Ausführungswährung (Code)'), {
    target: { value: 'eur' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));
  expect(submit).toHaveBeenLastCalledWith({});
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));
  expect(submit).toHaveBeenLastCalledWith({
    currency_confirmation: { currency_code: 'EUR', source: 'USER_CONFIRMED', note: null },
  });
  fireEvent.change(screen.getByLabelText('Beleg / Erläuterung (optional)'), {
    target: { value: 'Abrechnung geprüft' },
  });
  expect(screen.getByRole('checkbox')).not.toBeChecked();
  expect(screen.getByLabelText('Beleg / Erläuterung (optional)')).toHaveAttribute(
    'maxlength',
    '1000',
  );
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.change(screen.getByLabelText('Ausführungswährung (Code)'), {
    target: { value: 'USD' },
  });
  expect(screen.getByRole('checkbox')).not.toBeChecked();
  fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));
  expect(submit).toHaveBeenLastCalledWith({});
});

it('rejects invalid affirmed codes, preserves no confirmation on legacy requests, and describes replacement identity', () => {
  expect(executionCurrencyDeclaration(emptyExecutionCurrency())).toEqual({});
  expect(() => executionCurrencyDeclaration({ code: 'EU', note: '', confirmed: true })).toThrow(
    'dreistelligen Währungscode',
  );
  expect(
    executionCurrencyDeclaration({ code: ' usd ', note: '  Abrechnung  ', confirmed: true }),
  ).toEqual({
    currency_confirmation: { currency_code: 'USD', source: 'USER_CONFIRMED', note: 'Abrechnung' },
  });
  render(
    <ExecutionCurrencyInput value={emptyExecutionCurrency()} onChange={vi.fn()} replacement />,
  );
  expect(screen.getByText(/Ersatzbuchung braucht eine eigene Währungsbestätigung/)).toBeVisible();
  expect(screen.getByRole('checkbox')).not.toBeChecked();
});
