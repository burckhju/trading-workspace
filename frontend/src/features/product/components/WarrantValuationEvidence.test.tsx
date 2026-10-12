import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { dataEvidenceApi } from '../services/dataEvidence';
import type { WarrantResponse, WarrantTermsResponse } from '../types/api';
import type { ValuationEvidenceView } from '../types/dataEvidence';
import { WarrantValuationEvidence } from './WarrantValuationEvidence';
vi.mock('../services/dataEvidence', () => ({
  dataEvidenceApi: { facts: vi.fn(), recordFacts: vi.fn() },
}));
const warrant = { id: 'w', isin: 'DE000VH2LU21', version: 3 } as WarrantResponse;
const terms = {
  id: 't',
  version_no: 2,
  option_direction: 'CALL',
  strike: '100',
  ratio: '.1',
  maturity_date: '2027-01-15',
} as WarrantTermsResponse;
const missing: ValuationEvidenceView = {
  revision: 0,
  current: null,
  history: [],
  status: 'MISSING',
};
const fact = {
  product_type: 'VANILLA_WARRANT',
  exercise_style: 'EUROPEAN',
  quanto: false,
  ratio_convention: 'UNDERLYING_UNITS_PER_WARRANT',
  expiry_at: null,
  document_reference: 'Final terms page 2',
  source_url: null,
  reviewed_at: '2026-10-12T10:00:00Z',
  note: 'Verified against synthetic document',
} as const;
const saved: ValuationEvidenceView = {
  revision: 1,
  status: 'CURRENT',
  current: {
    id: 'e',
    terms_id: 't',
    revision: 1,
    recorded_at: '2026-10-12T11:00:00Z',
    actor_id: 'actor',
    origin: 'MANUAL_DOCUMENT_REVIEW',
    facts: fact,
  },
  history: [],
};
saved.history = [saved.current!];
async function open(view = missing) {
  vi.mocked(dataEvidenceApi.facts).mockResolvedValue(view);
  render(<WarrantValuationEvidence warrant={warrant} terms={terms} />);
  fireEvent.click(screen.getByText('Produktmerkmale für IV mit Beleg erfassen'));
  expect(dataEvidenceApi.facts).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Produktbelege laden' }));
  await screen.findByLabelText('Produktart');
}
function change(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}
describe('manual document evidence', () => {
  beforeEach(() => vi.clearAllMocks());
  it('starts unknown, requires attestation, saves exact identity/version and preserves provenance', async () => {
    vi.mocked(dataEvidenceApi.recordFacts).mockResolvedValue(saved);
    await open();
    expect(screen.getByLabelText('Quanto-Eigenschaft')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Belegrevision speichern' })).toBeDisabled();
    change('Produktart', 'VANILLA_WARRANT');
    change('Ausübungsart', 'EUROPEAN');
    change('Quanto-Eigenschaft', 'false');
    change('Bezugsverhältnis-Konvention', 'UNDERLYING_UNITS_PER_WARRANT');
    change('Dokument und Fundstelle', fact.document_reference);
    change('Beleg geprüft am, mit Zeitzone', fact.reviewed_at);
    change('Prüfnotiz / Grund der Berichtigung', fact.note);
    fireEvent.click(screen.getByRole('checkbox'));
    change('Quellen-URL (optional)', 'https://example.org/terms');
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    change('Quellen-URL (optional)', '');
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Belegrevision speichern' }));
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Live-IV ist dadurch noch nicht freigeschaltet',
    );
    expect(dataEvidenceApi.recordFacts).toHaveBeenCalledWith(
      'w',
      {
        terms_id: 't',
        expected_version: 3,
        expected_revision: 0,
        facts: fact,
        confirmation: 'CONFIRM_DOCUMENT_REVIEW',
      },
      expect.any(AbortSignal),
    );
    fireEvent.click(screen.getByText('Letzte 20 Belegrevisionen'));
    expect(screen.getByText(/erfasst 2026-10-12T11:00:00Z/)).toHaveTextContent(
      'geprüft 2026-10-12T10:00:00Z',
    );
    expect(screen.getByText(/Quanto nein/)).toBeVisible();
  });
  it('records unknown as a full revision and never claims success after failed writes', async () => {
    await open(saved);
    change('Quanto-Eigenschaft', '');
    change('Ausübungsart', 'AMERICAN');
    change('Bewertungszeitpunkt mit Zeitzone (optional)', '2027-01-15T17:30:00+01:00');
    fireEvent.click(screen.getByRole('checkbox'));
    vi.mocked(dataEvidenceApi.recordFacts).mockRejectedValue(new Error('offline'));
    fireEvent.click(screen.getByRole('button', { name: 'Belegrevision speichern' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Speichererfolg ist nicht bestätigt',
    );
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    const [, payload] = vi.mocked(dataEvidenceApi.recordFacts).mock.calls[0];
    expect(payload.expected_revision).toBe(1);
    expect(payload.facts.quanto).toBeNull();
    expect(payload.facts.exercise_style).toBe('AMERICAN');
  });
  it('shows invalidated evidence without copying its facts into a new identity', async () => {
    await open({ ...saved, status: 'IDENTITY_OR_TERMS_CHANGED', current: null });
    expect(screen.getByText(/erneute Prüfung erforderlich/)).toBeVisible();
    expect(screen.getByLabelText('Ausübungsart')).toHaveValue('');
    expect(screen.getByLabelText('Beleg geprüft am, mit Zeitzone')).toHaveValue('');
    expect(screen.getByText(/nimmt eine frühere Feststellung zurück/)).toBeVisible();
  });
  it('shows failed reads and aborts in-flight requests on leaving', async () => {
    vi.mocked(dataEvidenceApi.facts).mockRejectedValueOnce(new Error('offline'));
    const { unmount } = render(<WarrantValuationEvidence warrant={warrant} terms={terms} />);
    fireEvent.click(screen.getByText('Produktmerkmale für IV mit Beleg erfassen'));
    fireEvent.click(screen.getByRole('button', { name: 'Produktbelege laden' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('nicht erreichbar');
    vi.mocked(dataEvidenceApi.facts).mockImplementationOnce(() => new Promise(() => {}));
    fireEvent.click(screen.getByRole('button', { name: 'Produktbelege laden' }));
    const signal = vi.mocked(dataEvidenceApi.facts).mock.calls[1][1]!;
    unmount();
    expect(signal.aborted).toBe(true);
  });
});
