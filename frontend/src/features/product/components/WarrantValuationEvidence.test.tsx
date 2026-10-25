import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useLayoutEffect } from 'react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MarketApiError } from '../../market/services/http';
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
  afterEach(() => vi.restoreAllMocks());
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

  it('pins identity, terms and version despite refreshed props and locks a pending save', async () => {
    vi.mocked(dataEvidenceApi.facts).mockResolvedValue(saved);
    let resolve!: (value: ValuationEvidenceView) => void;
    vi.mocked(dataEvidenceApi.recordFacts).mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    const onDirtyChange = vi.fn();
    const onBusyChange = vi.fn();
    const { rerender, container } = render(
      <WarrantValuationEvidence
        warrant={warrant}
        terms={terms}
        embedded
        onDirtyChange={onDirtyChange}
        onBusyChange={onBusyChange}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Produktbelege laden' }));
    await screen.findByLabelText('Produktart');
    change('Prüfnotiz / Grund der Berichtigung', 'Bewusst geänderte Prüfnotiz');
    fireEvent.click(screen.getByRole('checkbox'));
    expect(onDirtyChange).toHaveBeenLastCalledWith(true);
    rerender(
      <WarrantValuationEvidence
        warrant={{ ...warrant, version: 11, isin: 'DE000PAH0038' }}
        terms={{ ...terms, id: 'new-terms', version_no: 3 }}
        embedded
        onDirtyChange={onDirtyChange}
        onBusyChange={onBusyChange}
      />,
    );
    expect(screen.getByLabelText('Prüfnotiz / Grund der Berichtigung')).toHaveValue(
      'Bewusst geänderte Prüfnotiz',
    );
    act(() => {
      fireEvent.submit(container.querySelector('form')!);
      fireEvent.submit(container.querySelector('form')!);
    });
    expect(dataEvidenceApi.recordFacts).toHaveBeenCalledTimes(1);
    expect(dataEvidenceApi.recordFacts).toHaveBeenCalledWith(
      'w',
      expect.objectContaining({
        terms_id: 't',
        expected_version: 3,
        expected_revision: 1,
        facts: { ...fact, note: 'Bewusst geänderte Prüfnotiz' },
      }),
      expect.any(AbortSignal),
    );
    expect(onBusyChange).toHaveBeenLastCalledWith(true);
    expect(screen.getByLabelText('Prüfnotiz / Grund der Berichtigung')).toBeDisabled();
    expect(screen.getByRole('checkbox')).toBeDisabled();
    await act(async () => {
      resolve({ ...saved, revision: 2 });
      await Promise.resolve();
    });
    expect(onBusyChange).toHaveBeenLastCalledWith(false);
    expect(onDirtyChange).toHaveBeenLastCalledWith(false);
    expect(screen.getByRole('status')).toHaveTextContent('Belegrevision 2 gespeichert');
    expect(screen.getByRole('checkbox')).not.toBeChecked();
  });

  it('retains unsaved evidence when reloading is cancelled or the confirmed read fails', async () => {
    await open(saved);
    change('Dokument und Fundstelle', 'Noch nicht gespeicherter Fundort');
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    fireEvent.click(screen.getByRole('button', { name: 'Produktbelege laden' }));
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(dataEvidenceApi.facts).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Dokument und Fundstelle')).toHaveValue(
      'Noch nicht gespeicherter Fundort',
    );
    confirm.mockReturnValue(true);
    vi.mocked(dataEvidenceApi.facts).mockRejectedValueOnce(new Error('offline'));
    fireEvent.click(screen.getByRole('button', { name: 'Produktbelege laden' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('nicht erreichbar');
    expect(screen.getByLabelText('Dokument und Fundstelle')).toHaveValue(
      'Noch nicht gespeicherter Fundort',
    );
    expect(dataEvidenceApi.recordFacts).not.toHaveBeenCalled();
  });

  it('keeps the evidence draft on conflict and offers a deliberate product reload', async () => {
    vi.mocked(dataEvidenceApi.facts).mockResolvedValue(saved);
    vi.mocked(dataEvidenceApi.recordFacts).mockRejectedValue(
      new MarketApiError(409, {
        code: 'WARRANT_CONCURRENT_MODIFICATION',
        message: 'Produktversion wurde geändert.',
        details: [],
        timestamp: '',
      }),
    );
    const onReload = vi.fn();
    render(
      <WarrantValuationEvidence warrant={warrant} terms={terms} embedded onReload={onReload} />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Produktbelege laden' }));
    await screen.findByLabelText('Produktart');
    change('Ausübungsart', 'AMERICAN');
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Belegrevision speichern' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Produktversion wurde geändert');
    expect(screen.getByLabelText('Ausübungsart')).toHaveValue('AMERICAN');
    expect(screen.getByLabelText('Dokument und Fundstelle')).toHaveValue(fact.document_reference);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(onReload).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Produkt neu laden und prüfen' }));
    expect(onReload).toHaveBeenCalledTimes(1);
    expect(dataEvidenceApi.recordFacts).toHaveBeenCalledTimes(1);
  });

  it('ignores a late successful save after leaving the product', async () => {
    vi.mocked(dataEvidenceApi.facts).mockResolvedValue(saved);
    let resolve!: (value: ValuationEvidenceView) => void;
    vi.mocked(dataEvidenceApi.recordFacts).mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    const onDirtyChange = vi.fn();
    const onBusyChange = vi.fn();
    const { unmount } = render(
      <WarrantValuationEvidence
        warrant={warrant}
        terms={terms}
        embedded
        onDirtyChange={onDirtyChange}
        onBusyChange={onBusyChange}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Produktbelege laden' }));
    await screen.findByLabelText('Produktart');
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Belegrevision speichern' }));
    const signal = vi.mocked(dataEvidenceApi.recordFacts).mock.calls[0][2]!;
    unmount();
    expect(signal.aborted).toBe(true);
    onDirtyChange.mockClear();
    onBusyChange.mockClear();
    await act(async () => {
      resolve({ ...saved, revision: 2 });
      await Promise.resolve();
    });
    expect(onDirtyChange).not.toHaveBeenCalled();
    expect(onBusyChange).not.toHaveBeenCalled();
  });

  it('can close the embedded editor without recording evidence', async () => {
    vi.mocked(dataEvidenceApi.facts).mockResolvedValue(saved);
    const onCancel = vi.fn();
    render(
      <WarrantValuationEvidence warrant={warrant} terms={terms} embedded onCancel={onCancel} />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Produktbelege laden' }));
    await waitFor(() => expect(screen.getByLabelText('Produktart')).toBeEnabled());
    change('Ausübungsart', 'AMERICAN');
    fireEvent.click(screen.getByRole('button', { name: 'Belegeditor schließen' }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(dataEvidenceApi.recordFacts).not.toHaveBeenCalled();
  });

  it('blocks evidence input and submission during a parent product reload', async () => {
    vi.mocked(dataEvidenceApi.facts).mockResolvedValue(saved);
    const { rerender, container } = render(
      <WarrantValuationEvidence warrant={warrant} terms={terms} embedded />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Produktbelege laden' }));
    await screen.findByLabelText('Produktart');
    change('Ausübungsart', 'AMERICAN');
    fireEvent.click(screen.getByRole('checkbox'));
    rerender(<WarrantValuationEvidence warrant={warrant} terms={terms} embedded disabled />);
    expect(screen.getByLabelText('Ausübungsart')).toBeDisabled();
    expect(screen.getByRole('checkbox')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Produktbelege laden' })).toBeDisabled();
    fireEvent.submit(container.querySelector('form')!);
    change('Ausübungsart', 'EUROPEAN');
    expect(screen.getByLabelText('Ausübungsart')).toHaveValue('AMERICAN');
    expect(dataEvidenceApi.recordFacts).not.toHaveBeenCalled();
  });

  it('ignores a saved revision resolving during the destination commit', async () => {
    vi.mocked(dataEvidenceApi.facts).mockResolvedValue(saved);
    let resolve!: (value: ValuationEvidenceView) => void;
    let committed!: () => void;
    const afterCommit = new Promise<void>((done) => {
      committed = done;
    });
    vi.mocked(dataEvidenceApi.recordFacts).mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    const onDirtyChange = vi.fn();
    const onBusyChange = vi.fn();
    function Destination() {
      useLayoutEffect(() => {
        resolve({ ...saved, revision: 2 });
        queueMicrotask(committed);
      }, []);
      return <h1>Anderes Produkt</h1>;
    }
    const router = createMemoryRouter(
      [
        {
          path: '/edit',
          element: (
            <WarrantValuationEvidence
              warrant={warrant}
              terms={terms}
              embedded
              onDirtyChange={onDirtyChange}
              onBusyChange={onBusyChange}
            />
          ),
        },
        { path: '/next', element: <Destination /> },
      ],
      { initialEntries: ['/edit'] },
    );
    const view = render(<RouterProvider router={router} />);
    fireEvent.click(screen.getByRole('button', { name: 'Produktbelege laden' }));
    await screen.findByLabelText('Produktart');
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Belegrevision speichern' }));
    onDirtyChange.mockClear();
    onBusyChange.mockClear();
    const signal = vi.mocked(dataEvidenceApi.recordFacts).mock.calls[0][2]!;
    const environment = globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean };
    const previous = environment.IS_REACT_ACT_ENVIRONMENT;
    environment.IS_REACT_ACT_ENVIRONMENT = false;
    try {
      await router.navigate('/next');
      await afterCommit;
      expect(router.state.location.pathname).toBe('/next');
      expect(signal.aborted).toBe(true);
      expect(onDirtyChange).not.toHaveBeenCalled();
      expect(onBusyChange).not.toHaveBeenCalled();
    } finally {
      view.unmount();
      router.dispose();
      environment.IS_REACT_ACT_ENVIRONMENT = previous;
    }
  });
});
