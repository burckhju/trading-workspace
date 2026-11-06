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
  expect(screen.getByText(/^Kurszeit:/)).toHaveTextContent(/Kurszeit:.*14.9.2026/);
  expect(screen.getByText(/^Kurszeit:/).querySelector('time')).toHaveAttribute(
    'datetime',
    '2026-09-14T10:00:00Z',
  );
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
  expect(screen.getByText('Geld: nicht vorhanden')).toBeInTheDocument();
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
        routes: [{ ...route, refresh_error: null }],
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

it('keeps separate issuer failures visible beside successful other sources and in gap filter', async () => {
  request.mockResolvedValue({
    ...report,
    items: [
      {
        ...item,
        coverage: 'BID_WITHIN_AGE_BUDGET',
        refresh_status: 'MIXED',
        refresh_reason: null,
        refresh_jobs: [
          {
            lane: 'WARRANT_QUOTES',
            status: 'AVAILABLE',
            reason: 'QUOTE_OBSERVATIONS_AVAILABLE',
            checked_at: '2026-09-15T10:00:00Z',
            next_run_at: null,
          },
          {
            lane: 'ISSUER_QUOTES',
            status: 'ERROR',
            reason: 'ISSUER_TIMEOUT',
            checked_at: '2026-09-15T09:59:00Z',
            next_run_at: null,
          },
        ],
      },
    ],
  });
  render(<QuoteCoveragePanel />);
  fireEvent.click(screen.getByRole('button'));
  await screen.findByText('Synthetic old bid');
  fireEvent.click(screen.getByLabelText('Nur Prüfbedarf'));
  expect(screen.getByText('Unterschiedliche Abrufstände – Details prüfen')).toBeInTheDocument();
  expect(screen.getByText('Weitere Kursquellen: Schedulerlauf abgeschlossen')).toBeInTheDocument();
  expect(screen.getByText('Emittentenabruf: Letzter Abruf fehlgeschlagen')).toBeInTheDocument();
  expect(screen.getByText('ISSUER_TIMEOUT')).toBeInTheDocument();
  expect(screen.queryByText('Noch kein Abrufnachweis in dieser Laufzeit')).not.toBeInTheDocument();
  expect(request).toHaveBeenCalledTimes(1);
});

it('keeps a fresh retained quote with a failed provider in the gap filter despite AVAILABLE', async () => {
  request.mockResolvedValue({
    ...report,
    items: [
      {
        ...item,
        coverage: 'BID_WITHIN_AGE_BUDGET',
        refresh_status: 'AVAILABLE',
        routes: [{ ...route, observation_status: 'BID_WITHIN_AGE_BUDGET', age_seconds: 30 }],
      },
    ],
  });
  render(<QuoteCoveragePanel />);
  fireEvent.click(screen.getByRole('button'));
  await screen.findByText('Synthetic old bid');
  fireEvent.click(screen.getByLabelText('Nur Prüfbedarf'));

  expect(screen.getByText('Synthetic old bid')).toBeVisible();
  expect(screen.getByText('Schedulerlauf abgeschlossen')).toBeVisible();
  expect(screen.getByText(/Mindestens ein Providerabruf ohne bestätigten Erfolg/)).toBeVisible();
  expect(screen.queryByText(/Letzter Abruf erfolgreich/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByText('Kurswege (1)'));
  expect(
    screen.getByText('Gespeicherter Ersatzkurs · aktueller Providererfolg nicht bestätigt.'),
  ).toBeVisible();
  expect(screen.getByText(/^Kurszeit:/)).toHaveTextContent(/Kurszeit:.*14.9.2026/);
});

it('does not invent a substitute quote for a failed provider without stored prices', async () => {
  request.mockResolvedValue({
    ...report,
    items: [{ ...item, routes: [{ ...route, bid: null, reference_price: null }] }],
  });
  render(<QuoteCoveragePanel />);
  fireEvent.click(screen.getByRole('button'));
  await screen.findByText('Synthetic old bid');
  fireEvent.click(screen.getByText('Kurswege (1)'));

  expect(screen.getByText(/Abrufhinweis: VONTOBEL_QUOTE_TIMEOUT/)).toBeVisible();
  expect(screen.queryByText(/Gespeicherter Ersatzkurs/)).not.toBeInTheDocument();
});

it('does not label a locally deferred refresh as a failed provider attempt', async () => {
  request.mockResolvedValue({
    ...report,
    items: [
      {
        ...item,
        refresh_status: 'DEFERRED',
        routes: [{ ...route, refresh_error: 'FRANKFURT_REQUEST_THROTTLED' }],
      },
    ],
  });
  render(<QuoteCoveragePanel />);
  fireEvent.click(screen.getByRole('button'));
  await screen.findByText('Synthetic old bid');
  fireEvent.click(screen.getByText('Kurswege (1)'));

  expect(screen.getByText('Wiederholung nach Abruflimit')).toBeVisible();
  expect(screen.getByText(/Abrufhinweis: FRANKFURT_REQUEST_THROTTLED/)).toBeVisible();
  expect(
    screen.getByText('Gespeicherter Ersatzkurs · aktueller Providererfolg nicht bestätigt.'),
  ).toBeVisible();
  expect(screen.queryByText(/fehlgeschlagen/)).not.toBeInTheDocument();
});

it('separates product population, source identity, time basis and supplied freshness values', async () => {
  request.mockResolvedValue({
    ...report,
    assessment_scope: 'STORED_OBSERVATIONS_NOT_LIVE_VALUATION',
    execution_usable: false,
    items: [
      {
        ...item,
        routes: [
          {
            ...route,
            mapping_id: 'mapping-exact-version',
            provider_identity: 'historical-provider-identity',
            quote_time_text: '14.09.2026 10:00 (Zone nicht geliefert)',
            quote_time_basis: 'SOURCE_LOCAL_TIMEZONE_UNKNOWN',
            observed_at: null,
            age_seconds: null,
            max_quote_age_seconds: 3600,
          },
        ],
      },
    ],
  });
  render(<QuoteCoveragePanel />);
  fireEvent.click(screen.getByRole('button'));
  await screen.findByText('Synthetic old bid');
  expect(screen.getByText(/1 gehaltene Optionsscheine/)).toBeVisible();
  expect(
    screen.getByText(/Die gelieferte Liste zählt Produkte, keine Positionen oder Kurse/),
  ).toBeVisible();
  expect(screen.getByText('STORED_OBSERVATIONS_NOT_LIVE_VALUATION')).toBeVisible();
  expect(screen.getByText('false', { exact: true })).toBeVisible();
  fireEvent.click(screen.getByText('Kurswege (1)'));
  expect(screen.getByRole('heading', { name: 'Quellenidentität und Verfügbarkeit' })).toBeVisible();
  expect(screen.getByText('mapping-exact-version')).toBeVisible();
  expect(screen.getByText('historical-provider-identity')).toBeVisible();
  expect(screen.getByText('listing', { exact: true })).toBeVisible();
  expect(screen.getByText('XSTU', { exact: true })).toBeVisible();
  expect(screen.getByText('Kurszeit: Unbekannt')).toBeVisible();
  expect(
    screen.getByText('Originalzeittext: 14.09.2026 10:00 (Zone nicht geliefert)'),
  ).toBeVisible();
  expect(screen.getByText('Zeitbasis der Quelle: SOURCE_LOCAL_TIMEZONE_UNKNOWN')).toBeVisible();
  expect(screen.getByText('Kursalter am Prüfstand: Unbekannt')).toBeVisible();
  expect(screen.getByText('Altersgrenze laut Quelle: 3600 Sekunden')).toBeVisible();
  expect(screen.getByText(/^Zuletzt abgerufen:/)).toHaveTextContent(/14.9.2026.*UTC/);
  expect(screen.queryByText(/100 %|0 %|Qualitätsquote/)).not.toBeInTheDocument();
});

it('shows each missing price kind while keeping exact zero and ask-only evidence', async () => {
  request.mockResolvedValue({
    ...report,
    items: [
      {
        ...item,
        routes: [
          {
            ...route,
            bid: null,
            ask: '0.00',
            age_seconds: 0,
            feed_delay_seconds: 0,
            max_quote_age_seconds: 0,
            refresh_error: null,
          },
        ],
      },
    ],
  });
  render(<QuoteCoveragePanel />);
  fireEvent.click(screen.getByRole('button'));
  await screen.findByText('Synthetic old bid');
  fireEvent.click(screen.getByText('Kurswege (1)'));
  expect(screen.getByText('Geld: nicht vorhanden')).toBeVisible();
  expect(screen.getByText('Brief: 0.00 EUR')).toBeVisible();
  expect(screen.getByText('Referenz (Preisart nicht belegt): nicht vorhanden')).toBeVisible();
  expect(screen.getByText('Kursalter am Prüfstand: 0 Sekunden')).toBeVisible();
  expect(screen.getByText('Altersgrenze laut Quelle: 0 Sekunden')).toBeVisible();
  expect(screen.getByText('Quellenverzögerung: 0 Sekunden')).toBeVisible();
  expect(screen.getByText('Zeitbasis der Quelle: Nicht geliefert')).toBeVisible();
  expect(screen.getByText('Keine gespeicherte Mapping-ID geliefert')).toBeVisible();
  expect(screen.getByText(/Scope-Feld nicht geliefert/)).toBeVisible();
});

it('keeps an unavailable source and unknown owner codes independent of a fresh alternative', async () => {
  request.mockResolvedValue({
    ...report,
    items: [
      {
        ...item,
        coverage: 'BID_WITHIN_AGE_BUDGET',
        routes: [
          { ...route, refresh_error: null, observation_status: 'BID_WITHIN_AGE_BUDGET' },
          {
            ...route,
            provider: 'GETTEX_DELAYED',
            configured: false,
            listing_id: 'different-listing',
            provider_identity: null,
            mapping_status: null,
            route_reason: 'FUTURE_ROUTE_REASON',
            observation_status: 'FUTURE_OBSERVATION_STATUS',
            bid: null,
            ask: null,
            refresh_error: null,
            observed_at: '2026-09-14T10:00:00',
          },
        ],
      },
    ],
  });
  render(<QuoteCoveragePanel />);
  fireEvent.click(screen.getByRole('button'));
  await screen.findByText('Synthetic old bid');
  fireEvent.click(screen.getByText('Quellenkonfiguration des Prüfstands'));
  expect(screen.getByText('GETTEX_DELAYED: nicht konfiguriert')).toBeVisible();
  fireEvent.click(screen.getByText('Kurswege (2)'));
  expect(screen.getByText('Provider nicht konfiguriert')).toBeVisible();
  expect(screen.getByText('Routennachweis: FUTURE_ROUTE_REASON')).toBeVisible();
  expect(screen.getByText('Beobachtungsstatus: FUTURE_OBSERVATION_STATUS')).toBeVisible();
  expect(screen.getByText('Keine gespeicherte Providerzuordnung belegt')).toBeVisible();
  expect(
    screen.getByText('Kurszeit: 2026-09-14T10:00:00 (kein belegter Zeitpunkt mit Zeitzone)'),
  ).toBeVisible();
  expect(
    screen.queryByText(/ISIN-direkt|Provider wieder erreichbar|gesund/),
  ).not.toBeInTheDocument();
  expect(request).toHaveBeenCalledTimes(1);
});

it('provides table semantics and a labelled keyboard scroll area without reads on inspection', async () => {
  request.mockResolvedValue(report);
  render(<QuoteCoveragePanel />);
  fireEvent.click(screen.getByRole('button'));
  await screen.findByText('Synthetic old bid');
  const region = screen.getByRole('region', {
    name: 'Kursabdeckung je Produkt, horizontal scrollbar',
  });
  expect(region).toHaveAttribute('tabindex', '0');
  const table = within(region).getByRole('table', {
    name: 'Verifizierte Kurswege gehaltener Optionsscheine',
  });
  expect(within(table).getAllByRole('columnheader')).toHaveLength(3);
  expect(within(table).getByRole('rowheader')).toHaveAttribute('scope', 'row');
  expect(screen.getByRole('status')).not.toContainElement(table);
  fireEvent.focus(region);
  fireEvent.click(screen.getByText('Quellenkonfiguration des Prüfstands'));
  fireEvent.click(screen.getByText('Kurswege (1)'));
  fireEvent.click(screen.getByText('Diagnose', { exact: true }));
  fireEvent.change(screen.getByLabelText('Kursquellen nach Emittent'), {
    target: { value: 'VONT FINL.' },
  });
  fireEvent.click(screen.getByLabelText('Nur Prüfbedarf'));
  expect(request).toHaveBeenCalledTimes(1);
});
