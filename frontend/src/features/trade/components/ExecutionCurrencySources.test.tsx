import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { executionCurrencyText } from '../services/executionCurrency';
import type { ExecutionCurrencyResolution } from '../types/api';
import { ExecutionCurrencySources } from './ExecutionCurrencySources';

const base: ExecutionCurrencyResolution = {
  currency_code: null,
  source: 'UNKNOWN',
  source_execution_ids: [],
  confirmation_ids: [],
};

describe('historical execution currency provenance', () => {
  it('shows the original reference, validity, exact evidence identity and resolver version without inventing a confirmation', () => {
    const resolution: ExecutionCurrencyResolution = {
      ...base,
      currency_code: 'EUR',
      source: 'HISTORICAL_LISTINGS',
      evidence_ids: ['source-v2'],
      evidence: [
        {
          id: 'source-v2',
          kind: 'HISTORICAL_LISTINGS',
          source_reference: 'Archivierter Handelskalender, Seite 7',
          recorded_at: '2026-10-28T13:00:00Z',
          valid_from: '2026-09-01T00:00:00+02:00',
          valid_to: '2026-11-01T00:00:00+01:00',
          source_fingerprint: 'abc123',
          verification: 'USER_VERIFIED_SOURCE',
          supersedes_evidence_id: 'source-v1',
        },
      ],
      resolver_version: 'historical-currency-v1',
    };
    render(<ExecutionCurrencySources resolution={resolution} />);
    expect(screen.getByText(/Eine erneute Eingabe ist nicht nötig/)).toBeVisible();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Verwendete Währungsherkunft'));
    expect(screen.getByText('Quelle: Archivierter Handelskalender, Seite 7')).toBeVisible();
    expect(screen.getByText(/Gültig von 2026-09-01.*bis ausschließlich 2026-11-01/)).toBeVisible();
    expect(screen.getByText('Quellenversion source-v2')).toBeVisible();
    expect(screen.getByText('Ersetzt Quelle source-v1')).toBeVisible();
    expect(screen.getByText('Quellennachweis abc123')).toBeVisible();
    expect(screen.getByText('Zuordnungsregel historical-currency-v1')).toBeVisible();
    expect(screen.queryByText(/ausdrücklich bestätigt/)).not.toBeInTheDocument();
    expect(executionCurrencyText(resolution)).toBe(
      'EUR · automatisch aus historischen Notierungen abgeleitet',
    );
  });

  it.each([
    ['NO_HISTORICAL_EVIDENCE', /Heutige Produktnotierungen allein belegen keine historische/],
    ['DOCUMENT_CONFLICT', /Ausführungsbelege nennen unterschiedliche Währungen/],
    ['LISTING_CONFLICT', /widersprechen sich für denselben Handelsplatz/],
    ['LISTING_HISTORY_INCOMPLETE', /nicht vollständig ab/],
    ['EXECUTION_TIME_UNKNOWN', /Ausführungsdatum oder seine Zeitzone/],
    ['MULTIPLE_LISTING_CURRENCIES', /eindeutiger Ausführungsplatz/],
    ['CORRECTION_SOURCE_REVIEW_REQUIRED', /Quelle gehört zu einer ersetzten Buchung/],
    ['EVIDENCE_HISTORY_INVALID', /Quellenhistorie ist widersprüchlich/],
  ])('explains the concrete unresolved reason %s', (reason, label) => {
    render(
      <ExecutionCurrencySources
        resolution={{
          ...base,
          source: reason.includes('CONFLICT') ? 'CONFLICT' : 'UNKNOWN',
          reason: String(reason),
        }}
      />,
    );
    expect(screen.getByText(label)).toBeVisible();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('does not label a conflicting source as a known currency', () => {
    expect(executionCurrencyText({ ...base, source: 'CONFLICT' })).toBe(
      'widersprüchliche Währungsbelege',
    );
  });
});
