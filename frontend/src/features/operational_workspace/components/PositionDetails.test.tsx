import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { position } from '../../../test/positionFixture';
import type { OperationalPosition } from '../types';
import { PositionDetails } from './PositionDetails';

// Existing read owners are covered by the host/browser regressions. These cases
// isolate the passive wording from their independent request lifecycle.
vi.mock('./PositionPriceHistory', () => ({ PositionPriceHistory: () => null }));
vi.mock('../../alert/components/PositionRiskPanel', () => ({ PositionRiskPanel: () => null }));

function show(overrides: Partial<OperationalPosition> = {}) {
  render(
    <MemoryRouter>
      <PositionDetails position={position(overrides)} />
    </MemoryRouter>,
  );
  return within(screen.getByRole('region', { name: 'Details Test Warrant' }));
}

it('retains the supplied STALE restriction', () => {
  const details = show({ valuation_status: 'STALE' });
  expect(details.getByText(/Kursdaten veraltet:/)).toHaveTextContent('Keine Orderfreigabe');
  expect(details.getByText('25,00 EUR')).toBeInTheDocument();
});

it('does not infer staleness or usability from LAST_AVAILABLE alone', () => {
  const details = show({ valuation_status: 'LAST_AVAILABLE', analysis_warning: null });
  expect(details.queryByText(/veraltet|Referenzkurs|verwendbar|nutzbar/i)).not.toBeInTheDocument();
  expect(details.getByText(/Letzter verfügbarer Kursstand/)).toBeInTheDocument();
  expect(details.getByText('25,00 EUR')).toBeInTheDocument();
  expect(details.getByText('+5,00 EUR')).toBeInTheDocument();
});

it('explains the separate known outdated warning on LAST_AVAILABLE', () => {
  const details = show({
    valuation_status: 'LAST_AVAILABLE',
    analysis_warning: 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY',
  });
  expect(details.getByText(/Kursdaten veraltet:/)).toBeInTheDocument();
  expect(details.getByText('25,00 EUR')).toBeInTheDocument();
});

it.each([
  ['MISSING', /Produktkurs fehlt/i],
  ['UNAVAILABLE', /Produktkurs nicht verfügbar/i],
  ['ERROR', /Fehler bei der Produktbewertung/i],
] as const)('does not invent an available reference quote for %s', (status, message) => {
  const details = show({
    valuation_status: status,
    analysis_warning: null,
    valuation_currency: null,
    market_value: null,
    unrealized_gross_pnl: null,
    unrealized_pnl_usable: false,
    unrealized_pnl_reason: 'WARRANT_QUOTE_MISSING',
    quote_source: null,
    quote_observed_at: null,
  });
  expect(details.getByText(/Keine Orderfreigabe/)).not.toHaveTextContent(
    /Referenzkurs|veraltet|verwendbar|nutzbar/i,
  );
  expect(details.getByText(message)).toBeInTheDocument();
  expect(details.queryByText('25,00 EUR')).not.toBeInTheDocument();
  expect(details.queryByText('+5,00 EUR')).not.toBeInTheDocument();
  expect(details.getByText(/Quelle: Unbekannt.*Kurszeitpunkt: Unbekannt/)).toBeInTheDocument();
});

it.each([
  { valuation_status: 'AVAILABLE', analysis_warning: 'FUTURE_STALE_REFERENCE_WARNING' },
  { valuation_status: 'FUTURE_AVAILABLE_STATUS', analysis_warning: null },
  {
    valuation_status: 'FUTURE_AVAILABLE_STATUS',
    analysis_warning: 'REFERENCE_PRICE_INDICATIVE_ANALYSIS_ONLY',
  },
])('keeps an unknown code neutral: %j', (overrides) => {
  const details = show(overrides);
  expect(details.queryByText(/veraltet|Referenzkurs|verwendbar|nutzbar/i)).not.toBeInTheDocument();
  const notice = details.getByText(/nicht (?:bekannt|einordenbar)/i);
  expect(notice).toHaveTextContent('Keine Orderfreigabe');
  expect(notice).not.toHaveAttribute('role');
  expect(notice).not.toHaveAttribute('aria-live');
  expect(details.getByText('25,00 EUR')).toBeInTheDocument();
  expect(details.getByText('+5,00 EUR')).toBeInTheDocument();
});

it.each([
  ['QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY', /Kurszeitpunkt unbekannt/],
  ['QUOTE_TIMEZONE_UNKNOWN_INDICATIVE_ANALYSIS_ONLY', /Zeitzone.*unbekannt/],
  [
    'QUOTE_REFRESH_FAILED_INDICATIVE_ANALYSIS_ONLY',
    /Kursabruf.*fehlgeschlagen|Kursabruf nicht verfügbar/,
  ],
  ['REFERENCE_PRICE_INDICATIVE_ANALYSIS_ONLY', /Handels- oder Schlusskurs/],
] as const)('explains the known %s cause without inventing staleness', (warning, message) => {
  const details = show({
    valuation_status: 'INDICATIVE',
    analysis_warning: warning,
    quote_observed_at:
      warning === 'QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY' ||
      warning === 'QUOTE_TIMEZONE_UNKNOWN_INDICATIVE_ANALYSIS_ONLY'
        ? null
        : '2026-09-08T08:00:00Z',
  });
  expect(details.getByText(message)).toBeInTheDocument();
  expect(details.queryByText(/veraltet/)).not.toBeInTheDocument();
});

it('keeps AVAILABLE without a warning quiet', () => {
  const details = show({ analysis_warning: null });
  expect(details.queryByText(/Keine Orderfreigabe/)).not.toBeInTheDocument();
  expect(details.getByText('25,00 EUR')).toBeInTheDocument();
  expect(details.getByText('+5,00 EUR')).toBeInTheDocument();
});

it('describes INDICATIVE without assuming a reference quote', () => {
  const details = show({ valuation_status: 'INDICATIVE' });
  expect(details.getByText(/Indikative Bewertung/)).toBeInTheDocument();
  expect(details.queryByText(/Referenzkurs|veraltet/i)).not.toBeInTheDocument();
});

it('preserves a composed market value and independent unusable PnL on LAST_AVAILABLE', () => {
  const details = show({
    valuation_status: 'LAST_AVAILABLE',
    unrealized_pnl_usable: false,
    unrealized_pnl_reason: 'COST_BASIS_CURRENCY_UNKNOWN',
  });
  expect(details.getByText('25,00 EUR')).toBeInTheDocument();
  expect(details.queryByText('+5,00 EUR')).not.toBeInTheDocument();
  expect(details.getByText(/Kaufwährung.*nicht.*belegt/i)).toBeInTheDocument();
  expect(details.queryByText(/veraltet/)).not.toBeInTheDocument();
});
