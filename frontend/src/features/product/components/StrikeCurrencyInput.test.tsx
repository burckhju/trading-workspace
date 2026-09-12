import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { beforeEach, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import type { CurrencyListResponse } from '../../market/types/api';
import { StrikeCurrencyInput } from './StrikeCurrencyInput';

vi.mock('../../market/services/client', () => ({
  marketApiClient: { listCurrencies: vi.fn() },
}));

const listCurrencies = vi.mocked(marketApiClient.listCurrencies);
const submitted = vi.fn();
const references: CurrencyListResponse = {
  items: [
    { code: 'CHF', name: 'Swiss Franc', minor_unit: 2, reference_version: 'test' },
    { code: 'EUR', name: 'Euro', minor_unit: 2, reference_version: 'test' },
    { code: 'USD', name: 'US Dollar', minor_unit: 2, reference_version: 'test' },
  ],
};

function Form({ initial = '' }: { initial?: string }) {
  const [value, setValue] = useState(initial);
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submitted(value || null);
      }}
    >
      <StrikeCurrencyInput label="Strike-Währung" value={value} onChange={setValue} />
      <button type="submit">Speichern</button>
    </form>
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  listCurrencies.mockResolvedValue(references);
});

it('loads active references without automatically choosing a currency', async () => {
  render(<Form />);
  const selector = screen.getByRole('combobox', { name: 'Strike-Währung' });
  expect(selector).toHaveAttribute('aria-busy', 'true');
  await screen.findByRole('option', { name: 'CHF – Swiss Franc' });
  expect(selector).toHaveValue('');
  expect(screen.getAllByRole('option')).toHaveLength(4);
  expect(listCurrencies).toHaveBeenCalledWith(expect.any(AbortSignal));
  fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));
  expect(submitted).toHaveBeenCalledWith(null);
});

it.each(['USD', 'CHF'])('submits the explicitly selected %s', async (code) => {
  render(<Form />);
  await screen.findByRole('option', { name: new RegExp(`^${code}`) });
  fireEvent.change(screen.getByRole('combobox'), { target: { value: code } });
  fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));
  expect(submitted).toHaveBeenCalledWith(code);
});

it('does not invent missing currencies when the endpoint returns no references', async () => {
  listCurrencies.mockResolvedValue({ items: [] });
  render(<Form />);
  await screen.findByText(/Keine aktiven Währungen verfügbar/);
  expect(screen.getAllByRole('option')).toHaveLength(1);
  expect(screen.queryByRole('option', { name: /^USD/ })).not.toBeInTheDocument();
  expect(screen.queryByRole('option', { name: /^CHF/ })).not.toBeInTheDocument();
  expect(screen.getByRole('combobox')).toHaveValue('');
});

it('preserves a selection on load failure and recovers only after a successful retry', async () => {
  listCurrencies.mockRejectedValueOnce(new Error('network failure'));
  render(<Form initial="CHF" />);
  await screen.findByRole('alert');
  const selector = screen.getByRole('combobox');
  expect(selector).toHaveValue('CHF');
  expect(selector).toBeInvalid();
  fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));
  expect(submitted).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole('button', { name: 'Währungen neu laden' }));
  await screen.findByRole('option', { name: 'CHF – Swiss Franc' });
  await waitFor(() => expect(selector).toBeValid());
  expect(selector).toHaveValue('CHF');
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));
  expect(submitted).toHaveBeenCalledWith('CHF');
});

it('blocks a no-longer-active code without silently replacing it with EUR', async () => {
  listCurrencies.mockResolvedValue({ items: references.items.filter((item) => item.code === 'EUR') });
  render(<Form initial="CHF" />);
  await screen.findByRole('option', { name: 'EUR – Euro' });
  const selector = screen.getByRole('combobox');
  expect(selector).toHaveValue('CHF');
  expect(selector).toBeInvalid();
  expect(screen.getByRole('option', { name: /^CHF/ })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));
  expect(submitted).not.toHaveBeenCalled();
  fireEvent.change(selector, { target: { value: '' } });
  await waitFor(() => expect(selector).toBeValid());
  fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));
  expect(submitted).toHaveBeenCalledWith(null);
});

it('aborts reference loading when unmounted and ignores late responses', async () => {
  let resolve: ((response: CurrencyListResponse) => void) | undefined;
  listCurrencies.mockImplementation(
    () => new Promise<CurrencyListResponse>((done) => (resolve = done)),
  );
  const { unmount } = render(<Form />);
  const signal = listCurrencies.mock.calls[0][0];
  unmount();
  expect(signal?.aborted).toBe(true);
  await act(async () => resolve?.(references));
  expect(submitted).not.toHaveBeenCalled();
});
