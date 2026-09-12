import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { tradePlanApiClient } from '../services/client';
import { previewHebeltrader } from '../services/hebeltraderClient';
import type { HebeltraderPreview } from '../services/hebeltraderClient';
import type { TradePlanDetailResponse } from '../types/api';
import { HebeltraderPanel } from './HebeltraderPanel';

vi.mock('../services/client', () => ({ tradePlanApiClient: { create: vi.fn() } }));
vi.mock('../services/hebeltraderClient', () => ({ previewHebeltrader: vi.fn() }));

const result: HebeltraderPreview = {
  policy_id: 'HEBELTRADER_RECONSTRUCTED_V1',
  execution_enabled: false,
  input_digest: 'fixture-digest',
  mode: 'RECONSTRUCTED_BANDS',
  levels: { entry: '101', stop: '95', target1: '125', target2: '155' },
  assessment: {
    eligible: true,
    reasons: [],
    reward_risk: '6.5',
    allocation_fraction: '1',
    stock_stop_distance: '0.05',
    late_entry: false,
  },
  warnings: ['RECONSTRUCTION_NOT_PUBLISHER_FORMULA'],
  trade_plan_content: {
    thesis: 'Synthetic fixture',
    entry: { type: 'PRICE', currency: 'EUR', price: '101' },
    invalidation: { stop_price: '95' },
    targets: [{ sequence: 1, price: '125' }, { sequence: 2, price: '155' }],
    risk_assumptions: { thesis_risk: 'Reconstruction, not publisher formula' },
  },
};

function enterSnapshot() {
  screen.getByText('Hebeltrader-Regelvorschau').closest('details')?.setAttribute('open', '');
  const fields: Record<string, string> = {
    'Geldkurs Aktie': '100',
    'Briefkurs Aktie': '101',
    GD200: '95',
    'Explizite Bandbreite B': '30',
    'Kurszeit mit Zeitzone (ISO 8601)': new Date().toISOString(),
    'Analysedatum (YYYY-MM-DD)': new Date().toISOString().slice(0, 10),
    'Quellennachweis und Begründung für B': 'Synthetic source',
  };
  for (const [label, value] of Object.entries(fields)) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.click(screen.getByLabelText('Fundamentale These separat geprüft'));
  fireEvent.click(screen.getByRole('button', { name: 'Regelvorschau berechnen' }));
}

describe('HebeltraderPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(previewHebeltrader).mockResolvedValue(result);
    vi.mocked(tradePlanApiClient.create).mockResolvedValue({
      plan: { id: 'created-plan' },
    } as TradePlanDetailResponse);
  });

  it('requires a separate review before creating a manual draft', async () => {
    const onCreated = vi.fn();
    render(<HebeltraderPanel underlyingId="selected-underlying" onCreated={onCreated} />);
    enterSnapshot();
    const create = await screen.findByRole('button', { name: 'Geprüften Entwurf anlegen' });
    expect(create).toBeDisabled();
    expect(tradePlanApiClient.create).not.toHaveBeenCalled();
    fireEvent.click(screen.getByLabelText(/Rekonstruktion, Annahmen und Marken geprüft/));
    fireEvent.click(create);
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith('created-plan'));
    expect(tradePlanApiClient.create).toHaveBeenCalledWith({
      ...result.trade_plan_content,
      origin_type: 'MANUAL',
      underlying_id: 'selected-underlying',
    });
  });

  it('invalidates a reviewed preview after an input change', async () => {
    render(<HebeltraderPanel underlyingId="selected-underlying" onCreated={vi.fn()} />);
    enterSnapshot();
    await screen.findByRole('button', { name: 'Geprüften Entwurf anlegen' });
    fireEvent.click(screen.getByLabelText(/Rekonstruktion, Annahmen und Marken geprüft/));
    fireEvent.change(screen.getByLabelText('Briefkurs Aktie'), { target: { value: '102' } });
    expect(screen.queryByRole('button', { name: 'Geprüften Entwurf anlegen' })).toBeNull();
    expect(tradePlanApiClient.create).not.toHaveBeenCalled();
  });

  it('does not offer draft creation for rejected entry conditions', async () => {
    vi.mocked(previewHebeltrader).mockResolvedValue({
      ...result,
      assessment: { ...result.assessment, eligible: false, reasons: ['QUOTE_STALE_OR_FUTURE'] },
      trade_plan_content: null,
    });
    render(<HebeltraderPanel underlyingId="selected-underlying" onCreated={vi.fn()} />);
    enterSnapshot();
    expect(await screen.findByRole('alert')).toHaveTextContent('QUOTE_STALE_OR_FUTURE');
    expect(screen.queryByRole('button', { name: 'Geprüften Entwurf anlegen' })).toBeNull();
  });

  it('shows calculation errors without creating a draft', async () => {
    vi.mocked(previewHebeltrader).mockRejectedValue(new Error('Snapshot unavailable'));
    render(<HebeltraderPanel underlyingId="selected-underlying" onCreated={vi.fn()} />);
    enterSnapshot();
    expect(await screen.findByRole('alert')).toHaveTextContent('Snapshot unavailable');
    expect(tradePlanApiClient.create).not.toHaveBeenCalled();
  });
});
