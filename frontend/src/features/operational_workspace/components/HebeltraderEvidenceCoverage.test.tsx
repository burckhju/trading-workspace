import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { hebeltraderEvidence, hebeltraderSource } from '../../../test/hebeltraderEvidenceFixture';
import { position } from '../../../test/positionFixture';
import type { HebeltraderEvidenceReport } from '../hebeltraderEvidence';
import { readHebeltraderEvidence } from '../services/hebeltraderEvidence';
import { HebeltraderEvidenceCoverage } from './HebeltraderEvidenceCoverage';
import { PositionDetails } from './PositionDetails';

vi.mock('../services/hebeltraderEvidence', () => ({ readHebeltraderEvidence: vi.fn() }));
vi.mock('./PositionPriceHistory', () => ({ PositionPriceHistory: () => null }));
vi.mock('../../alert/components/PositionRiskPanel', () => ({ PositionRiskPanel: () => null }));

beforeEach(() => {
  vi.mocked(readHebeltraderEvidence).mockReset().mockResolvedValue(hebeltraderEvidence());
});

function deferred() {
  let resolve!: (value: HebeltraderEvidenceReport) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<HebeltraderEvidenceReport>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

it('shows concrete evidence, missing facts, later rule dependencies and separate status dimensions', async () => {
  render(<HebeltraderEvidenceCoverage tradeId="trade-1" positionId="position-1" />);
  expect(screen.getByText('Belegabdeckung wird geladen …')).toBeInTheDocument();
  await screen.findByText('Belege noch unvollständig');
  expect(screen.getByText('Ausführungen: Vorhanden')).toBeInTheDocument();
  expect(screen.getByText('Einstiegsgruppe: Fehlt')).toBeInTheDocument();
  expect(screen.getByText(/Klärung: Ursprünglichen Auftrag/)).toBeInTheDocument();
  expect(screen.getByText(/Benötigt für: B01, B55/)).toBeInTheDocument();
  expect(
    screen.getByText('F207-4: Evidenzverknüpfung. Keine Baseline-Regelauswertung.'),
  ).toBeInTheDocument();
  expect(screen.getByText('Durch diesen Read nicht geprüft.')).toBeInTheDocument();
  expect(screen.getByText(/Vollständige Belege bedeuten keine aktive/)).toBeInTheDocument();
  expect(screen.getByText('execution:buy-1')).toBeInTheDocument();
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
  expect(readHebeltraderEvidence).toHaveBeenCalledOnce();
});

it('does not turn complete evidence into rule execution or source replacement', async () => {
  vi.mocked(readHebeltraderEvidence).mockResolvedValue(
    hebeltraderEvidence({
      coverage_status: 'COMPLETE',
      original_z1_quantity: 100,
      assigned_z1_sold_quantity: 0,
      personal_underlying_entry: '100.123456789',
      underlying_currency: 'USD',
      evidence_revision_id: 'revision-2',
      evidence_recorded_at: '2026-11-14T09:30:00Z',
      source: hebeltraderSource({
        currentness: 'SOURCE_SUPERSEDED',
        supersedes_version_id: 'source-0',
      }),
    }),
  );
  const view = render(<HebeltraderEvidenceCoverage tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('Belege dieses Schnitts vollständig');
  expect(screen.getByText('100.123456789 USD')).toBeInTheDocument();
  expect(screen.getByText('0')).toBeInTheDocument();
  expect(screen.getByText(/Historisch gebundene Version/)).toBeInTheDocument();
  expect(screen.getByText('Vorgängerversion: source-0')).toBeInTheDocument();
  expect(screen.getByText(/Quellenversion 1 \(source-version-1\)/)).toBeInTheDocument();
  expect(view.container.querySelector('time[datetime="2026-08-03"]')).toBeInTheDocument();
  expect(view.container.querySelector('time[datetime="2026-08-03T00:00:00Z"]')).toBeNull();
  expect(screen.getByText(/Nur Datum belegt/)).toBeInTheDocument();
  expect(screen.getByText(/SHA-256:/)).toHaveTextContent('a'.repeat(64));
  expect(screen.getByText(/Keine Baseline-Regelauswertung/)).toBeInTheDocument();
});

it('renders conflicts and unsuitable evidence without hiding clarification', async () => {
  const source = hebeltraderSource({ external_reference: null });
  vi.mocked(readHebeltraderEvidence).mockResolvedValue(
    hebeltraderEvidence({
      coverage_status: 'CONFLICTED',
      source,
      items: [
        {
          key: 'foreign',
          label: 'Instrument',
          status: 'CONFLICT',
          detail: 'Fremdes Instrument.',
          affected_rules: [],
          clarification: 'Zuordnung prüfen.',
          references: [],
        },
        {
          key: 'future',
          label: 'Basiswertkurs',
          status: 'UNSUITABLE',
          detail: 'Kurs liegt nach dem Kauf.',
          affected_rules: ['B54'],
          clarification: null,
          references: [],
        },
      ],
    }),
  );
  render(<HebeltraderEvidenceCoverage tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('Widersprüche in den Belegen');
  expect(screen.getByText('Instrument: Widersprüchlich')).toBeInTheDocument();
  expect(screen.getByText('Basiswertkurs: Ungeeignet')).toBeInTheDocument();
  expect(screen.getByText('Klärung: Zuordnung prüfen.')).toBeInTheDocument();
  expect(screen.getByText(/Ohne Ausgabenreferenz/)).toBeInTheDocument();
  expect(screen.getByText(/Die gebundene Version ist aktuell/)).toBeInTheDocument();
});

it('keeps unrelated draft inputs through failed reads and a deliberate read retry', async () => {
  const user = userEvent.setup();
  vi.mocked(readHebeltraderEvidence).mockRejectedValueOnce(new Error('Lesen fehlgeschlagen.'));
  render(
    <>
      <label>
        Verkaufsnotiz
        <input defaultValue="" />
      </label>
      <HebeltraderEvidenceCoverage tradeId="trade-1" positionId="position-1" />
    </>,
  );
  await user.type(screen.getByLabelText('Verkaufsnotiz'), 'Meine unveränderte Eingabe');
  expect(await screen.findByRole('alert')).toHaveTextContent('Lesen fehlgeschlagen.');
  expect(screen.queryByText('Belege noch unvollständig')).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Belegabdeckung erneut lesen' }));
  await screen.findByText('Belege noch unvollständig');
  expect(screen.getByLabelText('Verkaufsnotiz')).toHaveValue('Meine unveränderte Eingabe');
  expect(readHebeltraderEvidence).toHaveBeenCalledTimes(2);
});

it.each(['resolve', 'reject'] as const)(
  'ignores a late %s across A → B → A and clears old evidence',
  async (outcome) => {
    const pending = deferred();
    vi.mocked(readHebeltraderEvidence).mockReturnValueOnce(pending.promise);
    const view = render(<HebeltraderEvidenceCoverage tradeId="trade-1" positionId="position-1" />);
    view.rerender(<HebeltraderEvidenceCoverage tradeId="trade-2" positionId="position-2" />);
    expect(screen.queryByText('Belege noch unvollständig')).not.toBeInTheDocument();
    await screen.findByText('Belege noch unvollständig');
    view.rerender(<HebeltraderEvidenceCoverage tradeId="trade-1" positionId="position-1" />);
    await screen.findByText('Belege noch unvollständig');
    await act(async () => {
      if (outcome === 'resolve')
        pending.resolve(hebeltraderEvidence({ coverage_status: 'COMPLETE' }));
      else pending.reject(new Error('Veralteter Fehler'));
      await pending.promise.catch(() => undefined);
    });
    expect(screen.queryByText('Belege dieses Schnitts vollständig')).not.toBeInTheDocument();
    expect(screen.queryByText('Veralteter Fehler')).not.toBeInTheDocument();
    expect(readHebeltraderEvidence).toHaveBeenCalledTimes(3);
    expect(vi.mocked(readHebeltraderEvidence).mock.calls[0][2]?.aborted).toBe(true);
  },
);

it('invalidates a changed position and reload token and aborts on unmount', async () => {
  const pending = deferred();
  vi.mocked(readHebeltraderEvidence).mockReturnValue(pending.promise);
  const view = render(<HebeltraderEvidenceCoverage tradeId="trade-1" positionId="position-1" />);
  view.rerender(<HebeltraderEvidenceCoverage tradeId="trade-1" positionId="position-2" />);
  view.rerender(
    <HebeltraderEvidenceCoverage tradeId="trade-1" positionId="position-2" reloadToken={1} />,
  );
  expect(readHebeltraderEvidence).toHaveBeenCalledTimes(3);
  view.unmount();
  expect(vi.mocked(readHebeltraderEvidence).mock.calls.every((call) => call[2]?.aborted)).toBe(
    true,
  );
  await act(async () => {
    pending.resolve(hebeltraderEvidence());
    await pending.promise;
  });
});

it('uses the existing position-details host and preserves its execution-history link', async () => {
  const p = position({ trade_id: 'trade-1', position_id: 'position-1' });
  render(
    <MemoryRouter>
      <PositionDetails position={p} />
    </MemoryRouter>,
  );
  await screen.findByText('Belege noch unvollständig');
  expect(
    screen.getByRole('link', { name: 'Kauf-/Verkaufsdaten und Historie öffnen' }),
  ).toHaveAttribute('href', `${p.target}#execution-dates`);
  expect(readHebeltraderEvidence).toHaveBeenCalledWith(
    'trade-1',
    'position-1',
    expect.any(AbortSignal),
  );
});
