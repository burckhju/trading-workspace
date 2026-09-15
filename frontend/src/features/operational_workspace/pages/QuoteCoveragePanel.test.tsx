import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

import { requestJson } from '../../market/services/http';
import { QuoteCoveragePanel } from './QuoteCoveragePanel';

vi.mock('../../market/services/http', () => ({ requestJson: vi.fn() }));
const request = vi.mocked(requestJson);
const route = {
  provider: 'VONTOBEL_MARKETS',
  listing_id: 'listing',
  mic: 'XSTU',
  currency: 'EUR',
  mapping_status: 'ACTIVE',
  provider_identity: 'DE000ZZ00001',
  provider_exchange_code: 'ISSUER',
  validated_at: '2026-09-15T10:00:00Z',
  configured: true,
  route_reason: 'ROUTE_IDENTITY_VERIFIED',
  observation_status: 'OLDER_BID',
  bid: '1.01',
  ask: null,
  reference_price: null,
  reference_price_type: null,
  observed_at: '2026-09-14T10:00:00Z',
  retrieved_at: '2026-09-14T10:01:00Z',
  age_seconds: 86400,
  feed_delay_seconds: null,
  trading_status: 'UNKNOWN',
  refresh_error: 'VONTOBEL_QUOTE_TIMEOUT',
};
const item = {
  warrant_id: 'warrant',
  name: 'Synthetic old bid',
  isin: 'DE000ZZ00001',
  wkn: null,
  issuer: 'VONT FINL.',
  issuer_probe_eligible: true,
  coverage: 'HISTORICAL_BID_ONLY',
  routes: [route],
  refresh_status: 'ERROR',
  refresh_reason: 'QUOTE_REFRESH_FAILED',
  checked_at: null,
  next_run_at: null,
  discovery_reasons: [],
};
const report = {
  assessed_at: '2026-09-15T10:00:00Z',
  scheduler_enabled: true,
  scheduler_leader: true,
  source_order: ['VONTOBEL_MARKETS', 'GETTEX_DELAYED'],
  configured_sources: ['VONTOBEL_MARKETS'],
  items: [item],
};
beforeEach(() => vi.resetAllMocks());

it('loads stored coverage only on request and preserves original time and quote kind', async () => {
  request.mockResolvedValue(report);
  render(<QuoteCoveragePanel />);
  expect(request).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Kursquellen im Depot prüfen' }));
  expect(await screen.findByText('Synthetic old bid')).toBeInTheDocument();
  expect(screen.getByText('Nur historischer Geldkurs')).toBeInTheDocument();
  fireEvent.click(screen.getByText('Kurswege (1)'));
  expect(screen.getByText(/Emittentenindikation · EUR/)).toBeInTheDocument();
  expect(screen.getByText(/Brief: nicht vorhanden/)).toBeInTheDocument();
  expect(screen.getByText(/Abrufhinweis: VONTOBEL_QUOTE_TIMEOUT/)).toBeInTheDocument();
  expect(screen.getByText(/Kurszeit:.*14.9.2026/)).toBeInTheDocument();
  expect(screen.getByText(/keine Orderfreigabe/)).toBeInTheDocument();
  expect(request).toHaveBeenCalledTimes(1);
  expect(request.mock.calls[0][0]).toContain('/market-data/warrants/quote-coverage');
  expect(request.mock.calls[0][1]).toEqual({ signal: expect.any(AbortSignal) });
});

it('filters all issuer labels and exposes unlisted products without technical ID input', async () => {
  const names = [
    'BNP PAR',
    'DZ BANK',
    'HSBC T+B',
    'JP MORGAN',
    'UniCredit',
    'UBS',
    'MS COI.',
    'VONT FINL.',
  ];
  request.mockResolvedValue({
    ...report,
    items: names.map((name, i) => ({
      ...item,
      warrant_id: String(i),
      issuer: name,
      name: `Synthetic ${name}`,
      routes: [],
      coverage: 'NO_USABLE_ROUTE',
    })),
  });
  render(<QuoteCoveragePanel />);
  fireEvent.click(screen.getByRole('button'));
  expect(await screen.findByText(/8 gehaltene Optionsscheine/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Kursquellen nach Emittent'), {
    target: { value: 'MS COI.' },
  });
  expect(screen.getByText('Synthetic MS COI.')).toBeInTheDocument();
  expect(screen.queryByText('Synthetic BNP PAR')).not.toBeInTheDocument();
  fireEvent.click(screen.getByText('Kurswege (0)'));
  expect(screen.getByText(/Keine passende gespeicherte Notierung/)).toBeInTheDocument();
  expect(request).toHaveBeenCalledTimes(1);
});

it('keeps references with unknown observation time distinct from bid and retrieval time', async () => {
  request.mockResolvedValue({
    ...report,
    items: [
      {
        ...item,
        coverage: 'REFERENCE_ONLY',
        routes: [
          {
            ...route,
            bid: null,
            ask: null,
            reference_price: '0.77',
            reference_price_type: 'PREVIOUS_CLOSE',
            observation_status: 'REFERENCE_ONLY',
            observed_at: null,
            age_seconds: null,
          },
        ],
      },
    ],
  });
  render(<QuoteCoveragePanel />);
  fireEvent.click(screen.getByRole('button'));
  await screen.findByText('Synthetic old bid');
  fireEvent.click(screen.getByText('Kurswege (1)'));
  expect(screen.getByText(/Referenz.*0.77 EUR · nur indikativ/)).toBeInTheDocument();
  expect(screen.getByText(/Kurszeit: Unbekannt/)).toBeInTheDocument();
  expect(screen.queryByText(/^Geld:/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Invalid Date/)).not.toBeInTheDocument();
});

it('shows read failure instead of stale success and supports read-only retry', async () => {
  request
    .mockResolvedValueOnce(report)
    .mockRejectedValueOnce(new Error('secret'))
    .mockResolvedValueOnce({ ...report, scheduler_enabled: false, items: [] });
  render(<QuoteCoveragePanel />);
  fireEvent.click(screen.getByRole('button'));
  await screen.findByText('Synthetic old bid');
  fireEvent.click(screen.getByRole('button'));
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Kursquellen konnten nicht geladen werden',
  );
  expect(screen.queryByText('Synthetic old bid')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button'));
  expect(await screen.findByText(/Automatischer Abruf: ausgeschaltet/)).toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('filters operational failures independently of observed bid age and aborts unmounted reads', async () => {
  request.mockResolvedValue({
    ...report,
    items: [
      { ...item, coverage: 'BID_WITHIN_AGE_BUDGET', refresh_status: 'ERROR' },
      {
        ...item,
        name: 'Synthetic normal',
        warrant_id: 'normal',
        coverage: 'BID_WITHIN_AGE_BUDGET',
        refresh_status: 'AVAILABLE',
      },
    ],
  });
  const { unmount } = render(<QuoteCoveragePanel />);
  fireEvent.click(screen.getByRole('button'));
  await screen.findByText('Synthetic normal');
  fireEvent.click(screen.getByLabelText('Nur Prüfbedarf'));
  const table = screen.getByRole('table');
  expect(within(table).getByText('Synthetic old bid')).toBeInTheDocument();
  expect(within(table).queryByText('Synthetic normal')).not.toBeInTheDocument();
  const signal = request.mock.calls[0][1]?.signal;
  unmount();
  expect(signal?.aborted).toBe(true);
});
