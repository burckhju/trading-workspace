import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { tradePlanApiClient } from '../services/client';
import {
  loadHebeltraderSources,
  reviewHebeltraderSource,
} from '../services/hebeltraderSourcesClient';
import type { HebeltraderSource } from '../services/hebeltraderSourcesClient';
import { HebeltraderPanel } from './HebeltraderPanel';

vi.mock('../services/client', () => ({ tradePlanApiClient: { create: vi.fn() } }));
vi.mock('../services/hebeltraderSourcesClient', () => ({
  loadHebeltraderSources: vi.fn(),
  reviewHebeltraderSource: vi.fn(),
}));

const source: HebeltraderSource = {
  version_id: 'source-1',
  underlying_id: 'stock-1',
  label: 'Beispielaktie · Hebeltrader 1/2026',
  issue_date: '2026-09-11',
  filename: 'example.pdf',
  content_hash: 'test-hash',
  scope: 'PUBLISHED_SNAPSHOT_NOT_LIVE',
  source_issues: [],
  stock: {
    currency: 'USD',
    values: { entry: '100', stop: '90', target1: '120', target2: '145', gd200: '95' },
    reward_risk: '3.25',
    band_deviation: '0',
    issues: [],
  },
  warrant: {
    currency: 'EUR',
    values: { entry: '0.16', stop: '0.07', target1: '0.71', target2: '2.12' },
    reward_risk: '13.94',
    band_deviation: null,
    issues: [],
  },
};

function openDetails(container: HTMLElement) {
  container.querySelectorAll('details').forEach((element) => {
    element.open = true;
  });
}

describe('Hebeltrader source-first input policy', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(loadHebeltraderSources).mockResolvedValue({
      items: [source],
      has_more: false,
      next_offset: null,
    });
    vi.mocked(reviewHebeltraderSource).mockResolvedValue({
      source,
      current_preview: null,
      execution_enabled: false,
      missing_data: ['Kein aktueller Geld-/Briefkurs: nur Quellenszenario.'],
    });
  });

  it('loads visible source facts and requests no model parameters', async () => {
    const { container } = render(<HebeltraderPanel underlyingId="stock-1" onCreated={vi.fn()} />);
    await screen.findByText(/example.pdf/);
    openDetails(container);
    expect(loadHebeltraderSources).toHaveBeenCalledWith('stock-1', 0, expect.any(AbortSignal));
    expect(screen.getByText('100 USD')).toBeInTheDocument();
    expect(screen.getByText('0.16 EUR')).toBeInTheDocument();
    expect(container.querySelectorAll('input[required]')).toHaveLength(0);
    expect(screen.queryByLabelText('Explizite Bandbreite B')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Tickgröße')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('GD200')).not.toBeInTheDocument();
    expect(tradePlanApiClient.create).not.toHaveBeenCalled();
  });

  it('reviews only existing data when no current quote can be read', async () => {
    const { container } = render(<HebeltraderPanel underlyingId="stock-1" onCreated={vi.fn()} />);
    await screen.findByText(/example.pdf/);
    openDetails(container);
    fireEvent.click(screen.getByRole('button', { name: 'Vorhandene Daten prüfen' }));
    expect(await screen.findByText(/Kein aktueller Geld-\/Briefkurs/)).toBeInTheDocument();
    expect(reviewHebeltraderSource).toHaveBeenCalledWith({
      underlying_id: 'stock-1',
      source_version_id: 'source-1',
      fundamental_ok: false,
      target_history: 'UNKNOWN',
    });
    expect(
      screen.queryByRole('button', { name: 'Geprüften Entwurf anlegen' }),
    ).not.toBeInTheDocument();
  });

  it('reports missing imports without opening a manual-parameter form', async () => {
    vi.mocked(loadHebeltraderSources).mockResolvedValue({
      items: [],
      has_more: false,
      next_offset: null,
    });
    const { container } = render(<HebeltraderPanel underlyingId="stock-1" onCreated={vi.fn()} />);
    expect(await screen.findByText(/Keine bestätigte Hebeltrader-Empfehlung/)).toBeInTheDocument();
    expect(container.querySelectorAll('input')).toHaveLength(0);
  });

  it('does not invent missing components of a partially entered quote', async () => {
    const { container } = render(<HebeltraderPanel underlyingId="stock-1" onCreated={vi.fn()} />);
    await screen.findByText(/example.pdf/);
    openDetails(container);
    fireEvent.change(screen.getByLabelText('Briefkurs Aktie'), { target: { value: '101' } });
    fireEvent.click(screen.getByRole('button', { name: 'Vorhandene Daten prüfen' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/vollständig übernehmen/);
    expect(reviewHebeltraderSource).not.toHaveBeenCalled();
  });

  it('clears observable quote entries on source change', async () => {
    vi.mocked(loadHebeltraderSources).mockResolvedValue({
      items: [source, { ...source, version_id: 'source-2', label: 'Andere Ausgabe' }],
      has_more: false,
      next_offset: null,
    });
    const { container } = render(<HebeltraderPanel underlyingId="stock-1" onCreated={vi.fn()} />);
    await screen.findByText(/example.pdf/);
    openDetails(container);
    fireEvent.change(screen.getByLabelText('Briefkurs Aktie'), { target: { value: '101' } });
    fireEvent.change(screen.getByLabelText('Importierte Empfehlung'), {
      target: { value: 'source-2' },
    });
    expect(screen.getByLabelText('Briefkurs Aktie')).toHaveValue('');
  });

  it('ignores a late source response after changing the underlying', async () => {
    let complete:
      | ((result: { items: HebeltraderSource[]; has_more: boolean; next_offset: null }) => void)
      | undefined;
    vi.mocked(loadHebeltraderSources).mockReturnValueOnce(
      new Promise((resolve) => {
        complete = resolve;
      }),
    );
    const { rerender } = render(<HebeltraderPanel underlyingId="stock-1" onCreated={vi.fn()} />);
    vi.mocked(loadHebeltraderSources).mockResolvedValue({
      items: [],
      has_more: false,
      next_offset: null,
    });
    rerender(<HebeltraderPanel underlyingId="stock-2" onCreated={vi.fn()} />);
    await screen.findByText(/Keine bestätigte Hebeltrader-Empfehlung/);
    complete?.({ items: [source], has_more: false, next_offset: null });
    await waitFor(() => expect(screen.queryByText(/example.pdf/)).not.toBeInTheDocument());
  });

  it('requires review before saving a source-based current draft', async () => {
    const onCreated = vi.fn();
    vi.mocked(reviewHebeltraderSource).mockResolvedValue({
      source,
      missing_data: [],
      execution_enabled: false,
      current_preview: {
        policy_id: 'HEBELTRADER_RECONSTRUCTED_V1',
        mode: 'PUBLISHED_LEVELS_REVIEW',
        execution_enabled: false,
        input_digest: 'digest',
        levels: { entry: '100', stop: '90', target1: '120', target2: '145' },
        assessment: {
          eligible: true,
          reasons: [],
          reward_risk: '2.86',
          allocation_fraction: '1',
          stock_stop_distance: '0.1',
          late_entry: false,
        },
        warnings: [],
        trade_plan_content: {
          thesis: 'Source reviewed',
          entry: { type: 'PRICE', price: '101', currency: 'USD' },
          invalidation: { stop_price: '90' },
          targets: [
            { sequence: 1, price: '120' },
            { sequence: 2, price: '145' },
          ],
          risk_assumptions: { thesis_risk: 'Scenario, no guarantee' },
        },
      },
    });
    vi.mocked(tradePlanApiClient.create).mockResolvedValue({
      plan: { id: 'new-plan' },
    } as Awaited<ReturnType<typeof tradePlanApiClient.create>>);
    const { container } = render(<HebeltraderPanel underlyingId="stock-1" onCreated={onCreated} />);
    await screen.findByText(/example.pdf/);
    openDetails(container);
    for (const [label, value] of [
      ['Geldkurs Aktie', '100'],
      ['Briefkurs Aktie', '101'],
      ['Angezeigte Kurszeit', '2026-09-12T12:00:00'],
      ['Angezeigter Handelsplatz / Kursanbieter', 'Bank quote'],
      ['Zielhistorie laut sichtbarem Kursverlauf', 'NOT_REACHED'],
    ]) {
      fireEvent.change(screen.getByLabelText(label), { target: { value } });
    }
    fireEvent.click(screen.getByLabelText('Fundamentale These separat geprüft'));
    fireEvent.click(screen.getByRole('button', { name: 'Vorhandene Daten prüfen' }));
    const save = await screen.findByRole('button', { name: 'Geprüften Entwurf anlegen' });
    expect(save).toBeDisabled();
    expect(reviewHebeltraderSource).toHaveBeenCalledWith({
      underlying_id: 'stock-1',
      source_version_id: 'source-1',
      fundamental_ok: true,
      target_history: 'NOT_REACHED',
      quote: {
        bid: '100',
        ask: '101',
        source: 'Bank quote',
        currency: 'USD',
        observed_at: expect.any(String),
      },
    });
    fireEvent.click(
      screen.getByLabelText('Quelle, Marken und aktuelle Einstiegsbedingungen geprüft'),
    );
    fireEvent.click(save);
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith('new-plan'));
    expect(tradePlanApiClient.create).toHaveBeenCalledTimes(1);
  });
});
