import { useState } from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, expectTypeOf, it, vi } from 'vitest';

import * as tradePublic from '..';
import { InitialPurchaseCurrencyPreview, type InitialPurchaseCurrencyPreviewProps } from '..';
import { tradeManagementApiClient } from '../services/client';
import { emptyExecutionCurrency, type ExecutionCurrencyDraft } from '../services/executionCurrency';
import type { ExecutionCurrencyResolution } from '../types/api';

vi.mock('../services/client', () => ({
  tradeManagementApiClient: {
    executionCurrencyPreview: vi.fn(),
    purchaseFromSelection: vi.fn(),
  },
}));

const read = vi.mocked(tradeManagementApiClient.executionCurrencyPreview);
const historical: ExecutionCurrencyResolution = {
  currency_code: 'EUR',
  source: 'HISTORICAL_LISTINGS',
  source_execution_ids: [],
  confirmation_ids: [],
  evidence_ids: ['synthetic-source'],
};

function props(): InitialPurchaseCurrencyPreviewProps {
  return {
    productId: 'synthetic-product-a',
    date: '2026-08-20',
    time: '',
    value: emptyExecutionCurrency(),
    onChange: vi.fn(),
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

function Form({
  onEdit,
  disabled = false,
}: {
  onEdit: (value: ExecutionCurrencyDraft) => void;
  disabled?: boolean;
}) {
  const [value, setValue] = useState(emptyExecutionCurrency);
  return (
    <InitialPurchaseCurrencyPreview
      productId="synthetic-product-a"
      date="2026-08-20"
      time=""
      value={value}
      onChange={(next) => {
        setValue(next);
        onEdit(next);
      }}
      disabled={disabled}
    />
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  read.mockResolvedValue(historical);
});

it('exports only the initial-purchase adapter with the existing controlled draft contract', () => {
  expect(Object.keys(tradePublic)).toEqual(['InitialPurchaseCurrencyPreview']);
  expectTypeOf<keyof InitialPurchaseCurrencyPreviewProps>().toEqualTypeOf<
    'productId' | 'date' | 'time' | 'value' | 'onChange' | 'disabled'
  >();
  expectTypeOf<
    InitialPurchaseCurrencyPreviewProps['value']
  >().toEqualTypeOf<ExecutionCurrencyDraft>();
  expectTypeOf<InitialPurchaseCurrencyPreviewProps['onChange']>().toEqualTypeOf<
    (value: ExecutionCurrencyDraft) => void
  >();
});

it('binds the owner read to the product and BUY without passing extra capabilities or writing a draft', async () => {
  const input = props();
  const extraProps = {
    ...input,
    side: 'SELL',
    tradeId: 'synthetic-other-trade',
    context: { tradeId: 'synthetic-other-trade', side: 'SELL' },
    price: '99.99',
    quantity: 100,
    onRead: vi.fn(),
    onWrite: vi.fn(),
  };
  render(<InitialPurchaseCurrencyPreview {...extraProps} />);

  await screen.findByText(/Vorhandene Währung: EUR/);
  expect(read).toHaveBeenCalledExactlyOnceWith(
    { productId: input.productId, side: 'BUY' },
    {
      executed_on: input.date,
      execution_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    },
    expect.any(AbortSignal),
  );
  expect(input.onChange).not.toHaveBeenCalled();
  expect(input.value).toEqual({ code: '', note: '' });
  expect(extraProps.onRead).not.toHaveBeenCalled();
  expect(extraProps.onWrite).not.toHaveBeenCalled();
  expect(tradeManagementApiClient.purchaseFromSelection).not.toHaveBeenCalled();
  expect(screen.queryByLabelText('Ausführungswährung (Code)')).not.toBeInTheDocument();
});

it('keeps user edits controlled when the read completes and forwards the busy state', async () => {
  const pending = deferred<ExecutionCurrencyResolution>();
  read.mockReturnValue(pending.promise);
  const onEdit = vi.fn();
  const view = render(<Form onEdit={onEdit} />);
  fireEvent.change(screen.getByLabelText('Ausführungswährung (Code)'), {
    target: { value: 'CHF' },
  });
  fireEvent.change(screen.getByLabelText('Beleg / Erläuterung (optional)'), {
    target: { value: 'Eigene Abrechnung geprüft' },
  });
  expect(onEdit).toHaveBeenLastCalledWith({ code: 'CHF', note: 'Eigene Abrechnung geprüft' });

  await act(async () => {
    pending.resolve(historical);
    await pending.promise;
  });
  await screen.findByText(/Vorhandene Währung: EUR/);
  expect(onEdit).toHaveBeenCalledTimes(2);
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('CHF');
  expect(screen.getByLabelText('Beleg / Erläuterung (optional)')).toHaveValue(
    'Eigene Abrechnung geprüft',
  );

  view.rerender(<Form onEdit={onEdit} disabled />);
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toBeDisabled();
  expect(screen.getByLabelText('Beleg / Erläuterung (optional)')).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Abweichende Währung verwerfen' })).toBeDisabled();
  expect(read).toHaveBeenCalledOnce();
});

it.each(['success', 'failure'] as const)(
  'ignores a late %s and the intermediate product after an A–B–A product change',
  async (outcome) => {
    const firstA = deferred<ExecutionCurrencyResolution>();
    const productB = deferred<ExecutionCurrencyResolution>();
    const secondA = deferred<ExecutionCurrencyResolution>();
    read
      .mockReturnValueOnce(firstA.promise)
      .mockReturnValueOnce(productB.promise)
      .mockReturnValueOnce(secondA.promise);
    const input = props();
    const view = render(<InitialPurchaseCurrencyPreview {...input} />);
    const firstSignal = read.mock.calls[0][2];
    view.rerender(<InitialPurchaseCurrencyPreview {...input} productId="synthetic-product-b" />);
    const secondSignal = read.mock.calls[1][2];
    view.rerender(<InitialPurchaseCurrencyPreview {...input} />);
    expect(firstSignal?.aborted).toBe(true);
    expect(secondSignal?.aborted).toBe(true);
    expect(read.mock.calls.map(([context]) => context)).toEqual([
      { productId: 'synthetic-product-a', side: 'BUY' },
      { productId: 'synthetic-product-b', side: 'BUY' },
      { productId: 'synthetic-product-a', side: 'BUY' },
    ]);

    await act(async () => {
      secondA.resolve({ ...historical, currency_code: 'CHF' });
      await secondA.promise;
    });
    await screen.findByText(/Vorhandene Währung: CHF/);
    await act(async () => {
      if (outcome === 'success') firstA.resolve(historical);
      else firstA.reject(new Error('Verspäteter Fehler des alten Produktkontexts'));
      productB.resolve({ ...historical, currency_code: 'USD' });
      await Promise.allSettled([firstA.promise, productB.promise]);
    });
    expect(screen.getByText(/Vorhandene Währung: CHF/)).toBeVisible();
    expect(
      screen.queryByText(/Vorhandene Währung: EUR|Vorhandene Währung: USD/),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Verspäteter Fehler/)).not.toBeInTheDocument();
    expect(input.onChange).not.toHaveBeenCalled();
  },
);

it('keeps a failed read and its retry read-only while preserving manual currency and note', async () => {
  read.mockRejectedValueOnce(new Error('Historische Quelle nicht erreichbar'));
  const onEdit = vi.fn();
  render(<Form onEdit={onEdit} />);
  await screen.findByText(/Historische Quelle nicht erreichbar/);
  expect(onEdit).not.toHaveBeenCalled();
  expect(screen.queryByText(/Vorhandene Währung/)).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Ausführungswährung (Code)'), {
    target: { value: 'CHF' },
  });
  fireEvent.change(screen.getByLabelText('Beleg / Erläuterung (optional)'), {
    target: { value: 'Manuelle Belegangabe' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Währungsherkunft erneut prüfen' }));

  await screen.findByText(/Vorhandene Währung: EUR/);
  expect(read).toHaveBeenCalledTimes(2);
  expect(onEdit).toHaveBeenCalledTimes(2);
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('CHF');
  expect(screen.getByLabelText('Beleg / Erläuterung (optional)')).toHaveValue(
    'Manuelle Belegangabe',
  );
  expect(tradeManagementApiClient.purchaseFromSelection).not.toHaveBeenCalled();
});

it('aborts the owner read on unmount without turning its late result into a draft change', async () => {
  const pending = deferred<ExecutionCurrencyResolution>();
  read.mockReturnValue(pending.promise);
  const input = props();
  const view = render(<InitialPurchaseCurrencyPreview {...input} />);
  const signal = read.mock.calls[0][2];
  view.unmount();
  expect(signal?.aborted).toBe(true);

  await act(async () => {
    pending.resolve(historical);
    await pending.promise;
  });
  expect(input.onChange).not.toHaveBeenCalled();
});
