import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { analysisApiClient } from '../services/client';
import { MarketAnalysisDetailPage } from './MarketAnalysisDetailPage';

vi.mock('../services/client', () => ({
  analysisApiClient: {
    get: vi.fn(),
    run: vi.fn(),
    getRun: vi.fn(),
    getSnapshot: vi.fn(),
    events: vi.fn(),
    verify: vi.fn(),
    retry: vi.fn(),
    supersede: vi.fn(),
  },
}));

const analysisId = '33333333-3333-4333-8333-333333333333';
const analysis = {
  id: analysisId,
  underlying_id: '11111111-1111-4111-8111-111111111111',
  listing_id: '22222222-2222-4222-8222-222222222222',
  created_at: '2026-08-06T10:00:00Z',
  created_by: 'Tester',
};
const run1 = {
  version: 1,
  status: 'NOT_EVALUABLE',
  quality_status: 'INSUFFICIENT',
  model_id: 'EOD_TREND_MOMENTUM',
  model_version: '1.0.0',
  observation_count: 20,
  analysis_time: '2026-08-06T11:00:00Z',
  input_hash: 'abc123',
};
const run2 = {
  ...run1,
  version: 2,
  status: 'COMPLETED',
  quality_status: 'GOOD',
  observation_count: 250,
  analysis_time: '2026-08-06T12:00:00Z',
  input_hash: 'def456',
};
const event = {
  id: '44444444-4444-4444-8444-444444444444',
  version: 1,
  event_type: 'SUPERSEDED',
  from_status: 'NOT_EVALUABLE',
  to_status: 'SUPERSEDED',
  source_version: 1,
  replacement_version: 2,
  reason: 'Retry erfolgreich',
  correlation_id: null,
  occurred_at: '2026-08-06T12:01:00Z',
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(analysisApiClient.get).mockResolvedValue({ analysis, runs: [run1, run2] });
  vi.mocked(analysisApiClient.events).mockResolvedValue([event]);
  vi.mocked(analysisApiClient.run).mockResolvedValue({ ...run2, version: 3 });
  vi.mocked(analysisApiClient.getRun).mockImplementation((_id, version) =>
    Promise.resolve({
      analysis,
      run: version === 1 ? run1 : run2,
      parameters: { short_window: 20 },
      metrics: { sma_short: '101.25' },
      notes: version === 1 ? ['Zu wenig Beobachtungen'] : [],
      data_sources: ['EODHD'],
      criteria: [
        {
          code: 'TREND_ALIGNMENT',
          classification: 'POSITIVE',
          value: '1',
          explanation: 'Short average exceeds long average.',
        },
      ],
      snapshot: [],
    }),
  );
  vi.mocked(analysisApiClient.getSnapshot).mockResolvedValue({
    items: [
      {
        trading_date: '2026-08-05',
        open: '100',
        high: '103',
        low: '99',
        close: '102',
        adjusted_close: '102',
        volume: '1000',
        currency: 'EUR',
        provider: 'EODHD',
        provider_symbol: 'SIE.XETRA',
        quality_status: 'GOOD',
        warnings: [],
      },
    ],
    total: 1,
    offset: 0,
    limit: 50,
  });
  vi.mocked(analysisApiClient.verify).mockResolvedValue({
    verified: true,
    model_available: true,
    input_hash_matches: true,
    metrics_match: true,
    criteria_match: true,
    quality_status_match: true,
    notes_match: true,
  });
  vi.mocked(analysisApiClient.retry).mockResolvedValue({ ...run2, version: 3 });
  vi.mocked(analysisApiClient.supersede).mockResolvedValue(event);
});

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[`/market-analyses/${analysisId}`]}>
      <Routes>
        <Route path="/market-analyses/:analysisId" element={<MarketAnalysisDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('MarketAnalysisDetailPage', () => {
  it('renders version history, lifecycle events and superseded state', async () => {
    renderPage();
    expect(await screen.findByText('TREND_ALIGNMENT', {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByText('Ersetzt durch Version 2')).toBeInTheDocument();
    expect(screen.getByText('Grund: Retry erfolgreich')).toBeInTheDocument();
  });

  it('verifies reproducibility for the selected version', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText('TREND_ALIGNMENT', {}, { timeout: 5000 });
    await user.click(screen.getByRole('button', { name: 'Reproduzierbarkeit prüfen' }));
    await waitFor(() => expect(analysisApiClient.verify).toHaveBeenCalledWith(analysisId, 2));
    expect(await screen.findByText('Reproduktion bestätigt')).toBeInTheDocument();
  });

  it('retries a retryable historical version using an optional reason', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText('TREND_ALIGNMENT', {}, { timeout: 5000 });
    await user.selectOptions(screen.getByRole('combobox', { name: 'Analyseversion' }), '1');
    await screen.findByText('Zu wenig Beobachtungen');
    // Version 1 is already superseded in the fixture, so the action must not be offered.
    expect(screen.queryByRole('button', { name: 'Retry aus Snapshot' })).not.toBeInTheDocument();
  });

  it('submits explicit parameters for a new version', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText('TREND_ALIGNMENT', {}, { timeout: 5000 });
    await user.clear(screen.getByRole('spinbutton', { name: 'Kurzfristiges Fenster' }));
    await user.type(screen.getByRole('spinbutton', { name: 'Kurzfristiges Fenster' }), '15');
    await user.click(screen.getByRole('button', { name: 'Analyse ausführen' }));
    await waitFor(() => expect(analysisApiClient.run).toHaveBeenCalled());

    const lastCall = vi.mocked(analysisApiClient.run).mock.calls.at(-1);
    expect(lastCall).toBeDefined();

    const [calledAnalysisId, request] = lastCall!;
    expect(calledAnalysisId).toBe(analysisId);
    expect(request.parameters.short_window).toBe(15);
  });

  it('loads the persisted snapshot on demand', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText('TREND_ALIGNMENT', {}, { timeout: 5000 });
    await user.click(screen.getByRole('button', { name: 'Snapshot anzeigen (250)' }));
    expect(await screen.findByText('EODHD · SIE.XETRA')).toBeInTheDocument();
  });

  it('retries an eligible historical version with a reason', async () => {
    const user = userEvent.setup();

    vi.mocked(analysisApiClient.events).mockResolvedValue([]);

    renderPage();
    await screen.findByText('TREND_ALIGNMENT', {}, { timeout: 5000 });

    await user.selectOptions(screen.getByRole('combobox', { name: 'Analyseversion' }), '1');
    await screen.findByText('Zu wenig Beobachtungen');

    await user.type(screen.getByRole('textbox', { name: 'Begründung' }), 'Neue Datenlage');

    await user.click(screen.getByRole('button', { name: 'Retry aus Snapshot' }));

    await waitFor(() =>
      expect(analysisApiClient.retry).toHaveBeenCalledWith(analysisId, 1, 'Neue Datenlage'),
    );
  });

  it('supersedes an eligible historical version explicitly', async () => {
    const user = userEvent.setup();

    vi.mocked(analysisApiClient.events).mockResolvedValue([]);

    renderPage();
    await screen.findByText('TREND_ALIGNMENT', {}, { timeout: 5000 });

    await user.selectOptions(screen.getByRole('combobox', { name: 'Analyseversion' }), '1');
    await screen.findByText('Zu wenig Beobachtungen');

    await user.type(screen.getByRole('textbox', { name: 'Begründung' }), 'Durch Version 2 ersetzt');

    await user.selectOptions(screen.getByRole('combobox', { name: 'Ersatzversion' }), '2');

    await user.click(screen.getByRole('button', { name: 'Als ersetzt markieren' }));

    await waitFor(() =>
      expect(analysisApiClient.supersede).toHaveBeenCalledWith(
        analysisId,
        1,
        2,
        'Durch Version 2 ersetzt',
      ),
    );
  });
});
