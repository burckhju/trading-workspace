import { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { TradePlanContentRequest, TradePlanVersionResponse } from '../types/api';
import { createEmptyTradePlanContent, tradePlanContentFromVersion } from './content';
import { TradePlanContentForm } from './TradePlanContentForm';

function renderContent(initial = createEmptyTradePlanContent(), disabled = false) {
  const change = vi.fn<(content: TradePlanContentRequest) => void>();
  function Editor() {
    const [value, setValue] = useState(initial);
    return (
      <TradePlanContentForm
        value={value}
        disabled={disabled}
        onChange={(next) => {
          change(next);
          setValue(next);
        }}
      />
    );
  }
  render(<Editor />);
  return change;
}

describe('TradePlanContentForm', () => {
  it('starts without a hidden currency and captures precise prices, all targets and optional contents', () => {
    const change = renderContent();
    expect(screen.getByLabelText('Währung')).toHaveValue('');
    const input = (label: string, value: string) =>
      fireEvent.change(screen.getByLabelText(label), { target: { value } });
    input('Trade Thesis', 'Trendfortsetzung');
    input('Währung', 'USD');
    input('Entry-Preis', '100.123456789123456789');
    input('Technischer Stop', '90.987654321987654321');
    input('Invalidierungsregel', 'Trend gebrochen');
    input('Invalidierungsbegründung', 'Neues Tief');
    input('Target 1', '110.123456789123456789');
    input('Target-Begründung 1', 'Erster Widerstand');
    fireEvent.click(screen.getByRole('button', { name: 'Target hinzufügen' }));
    input('Target 2', '120.123456789123456789');
    input('Target-Begründung 2', 'Zweiter Widerstand');
    fireEvent.click(screen.getByText('Weitere Entry-Angaben'));
    input('Referenzpreis', '100.123456789123456789');
    input('Gültig bis (ISO 8601 mit Zeitzone)', '2026-12-31T12:34:56.123456+01:00');
    input('Entry-Begründung', 'Bestätigung');
    input('Plan-Risiko / Annahme', 'Fehlausbruch');
    fireEvent.click(screen.getByText('Weitere Risikoangaben'));
    input('Max-Loss-Annahme (optional)', 'Verlustannahme');
    input('Risk Notes', 'Ereignisrisiko');
    expect(change).toHaveBeenLastCalledWith({
      thesis: 'Trendfortsetzung',
      entry: {
        type: 'PRICE',
        currency: 'USD',
        price: '100.123456789123456789',
        reference_price: '100.123456789123456789',
        valid_until: '2026-12-31T12:34:56.123456+01:00',
        rationale: 'Bestätigung',
      },
      invalidation: {
        stop_price: '90.987654321987654321',
        invalidation_rule: 'Trend gebrochen',
        rationale: 'Neues Tief',
      },
      targets: [
        { sequence: 1, price: '110.123456789123456789', rationale: 'Erster Widerstand' },
        { sequence: 2, price: '120.123456789123456789', rationale: 'Zweiter Widerstand' },
      ],
      risk_assumptions: {
        thesis_risk: 'Fehlausbruch',
        max_loss_assumption: 'Verlustannahme',
        notes: 'Ereignisrisiko',
      },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Target 1 entfernen' }));
    expect(screen.getByLabelText('Target 1')).toHaveValue('120.123456789123456789');
    expect(screen.getByLabelText('Target-Begründung 1')).toHaveValue('Zweiter Widerstand');
    expect(screen.queryByRole('button', { name: 'Target 1 entfernen' })).not.toBeInTheDocument();
  });

  it('switches entry variants explicitly while retaining independent optional values', () => {
    const initial = createEmptyTradePlanContent();
    initial.entry = {
      type: 'PRICE',
      currency: 'EUR',
      price: '100',
      reference_price: '99.123456789',
      rationale: 'Begründung',
      valid_until: '2026-12-31T12:00:00Z',
    };
    const change = renderContent(initial);
    fireEvent.change(screen.getByLabelText('Entry-Art'), { target: { value: 'PRICE_RANGE' } });
    fireEvent.change(screen.getByLabelText('Preis von'), { target: { value: '100.1' } });
    fireEvent.change(screen.getByLabelText('Preis bis'), { target: { value: '101.1' } });
    expect(change.mock.lastCall?.[0].entry).toMatchObject({
      type: 'PRICE_RANGE',
      price: null,
      price_from: '100.1',
      price_to: '101.1',
      trigger: null,
      reference_price: '99.123456789',
    });
    fireEvent.change(screen.getByLabelText('Entry-Art'), { target: { value: 'TRIGGER' } });
    fireEvent.change(screen.getByLabelText('Trigger'), { target: { value: 'Ausbruch bestätigt' } });
    expect(change).toHaveBeenLastCalledWith(
      expect.objectContaining({
        entry: {
          type: 'TRIGGER',
          currency: 'EUR',
          price: null,
          price_from: null,
          price_to: null,
          trigger: 'Ausbruch bestätigt',
          reference_price: '99.123456789',
          rationale: 'Begründung',
          valid_until: '2026-12-31T12:00:00Z',
        },
      }),
    );
    fireEvent.change(screen.getByLabelText('Entry-Art'), { target: { value: 'PRICE' } });
    expect(screen.getByLabelText('Entry-Preis')).toHaveValue('');
    expect(screen.getByLabelText('Referenzpreis')).toHaveValue('99.123456789');
  });

  it('disables every editable field and target action during a mutation', () => {
    renderContent(createEmptyTradePlanContent(), true);
    for (const textbox of screen.getAllByRole('textbox', { hidden: true }))
      expect(textbox).toBeDisabled();
    expect(screen.getByRole('combobox')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Target hinzufügen' })).toBeDisabled();
  });

  it('copies all editable snapshot content without changing nulls or mutating the source', () => {
    const content: TradePlanContentRequest = {
      thesis: 'These',
      entry: {
        type: 'TRIGGER',
        currency: 'USD',
        price: null,
        price_from: null,
        price_to: null,
        trigger: 'Trigger',
        reference_price: '100.123456789123456789',
        valid_until: '2026-12-31T12:00:00.123456Z',
        rationale: 'Entry rationale',
      },
      invalidation: {
        stop_price: null,
        invalidation_rule: 'Trendbruch',
        rationale: 'Rule rationale',
      },
      targets: [{ sequence: 1, price: '120.123456789123456789', rationale: null }],
      risk_assumptions: {
        thesis_risk: 'Fehlausbruch',
        max_loss_assumption: null,
        notes: 'Notizen',
      },
    };
    const source: TradePlanVersionResponse = {
      id: 'v1',
      trade_plan_id: 'p1',
      version: 1,
      direction: 'LONG',
      status: 'APPROVED',
      created_at: '2026-10-25T12:00:00Z',
      created_by: 'actor',
      previous_version_id: null,
      change_reason: null,
      candidate_evaluation: null,
      approval: null,
      events: [],
      thesis: content.thesis,
      entry: {
        type: 'TRIGGER',
        currency: 'USD',
        price: null,
        price_from: null,
        price_to: null,
        trigger: 'Trigger',
        reference_price: '100.123456789123456789',
        valid_until: '2026-12-31T12:00:00.123456Z',
        rationale: 'Entry rationale',
      },
      invalidation: {
        stop_price: null,
        invalidation_rule: 'Trendbruch',
        rationale: 'Rule rationale',
      },
      targets: [{ sequence: 1, price: '120.123456789123456789', rationale: null }],
      risk_assumptions: {
        thesis_risk: 'Fehlausbruch',
        max_loss_assumption: null,
        notes: 'Notizen',
      },
    };
    const editable = tradePlanContentFromVersion(source);
    expect(editable).toEqual(content);
    editable.entry.reference_price = '101';
    editable.targets[0].price = '121';
    expect(source.entry.reference_price).toBe('100.123456789123456789');
    expect(source.targets[0].price).toBe('120.123456789123456789');
  });
});
