import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { position } from '../../../test/positionFixture';
import type { HebeltraderOriginalBidReport } from '../hebeltraderOriginalBid';
import { readHebeltraderOriginalBid } from '../services/hebeltraderOriginalBid';
import { missingBidSideReport, originalBidReport } from '../test/hebeltraderOriginalBidFixture';
import { HebeltraderOriginalBid } from './HebeltraderOriginalBid';
import { PositionDetails } from './PositionDetails';

vi.mock('../services/hebeltraderOriginalBid', () => ({ readHebeltraderOriginalBid: vi.fn() }));
vi.mock('./PositionPriceHistory', () => ({ PositionPriceHistory: () => null }));
vi.mock('./HebeltraderEvidenceCoverage', () => ({ HebeltraderEvidenceCoverage: () => null }));
vi.mock('./HebeltraderTargetHistory', () => ({ HebeltraderTargetHistory: () => null }));
vi.mock('./HebeltraderSessions', () => ({
  HebeltraderSessions: () => <p>Bestehender Sitzungsread bis Serverzeit</p>,
}));
vi.mock('../../alert/components/PositionRiskPanel', () => ({ PositionRiskPanel: () => null }));

beforeEach(() => {
  vi.mocked(readHebeltraderOriginalBid)
    .mockReset()
    .mockImplementation((tradeId, positionId) =>
      Promise.resolve(originalBidReport({ trade_id: tradeId, position_id: positionId })),
    );
});

function field(label: string) {
  return screen.getByText(label, { selector: 'dt' }).nextElementSibling;
}
function deferred() {
  let resolve!: (value: HebeltraderOriginalBidReport) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<HebeltraderOriginalBidReport>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

it('shows exact saved BID and owner entry values while keeping scale, live market and rule gaps explicit', async () => {
  const user = userEvent.setup();
  const view = render(<HebeltraderOriginalBid tradeId="trade-1" positionId="position-1" />);
  expect(screen.getByText('Original-Geldkursbeleg wird gelesen …')).toBeInTheDocument();
  await screen.findByText('Teilbelege vorhanden; Gesamtqualifikation offen');
  expect(field('Gespeicherter Geldkurs (BID)')).toHaveTextContent('1.234567890123 EUR');
  expect(field('Exakte Original-BID-Zeit')).toHaveTextContent('2026-09-21T13:00:00Z');
  expect(field('Kursalter laut Server')).toHaveTextContent(
    '300 Sekunden · Höchstalter 900 Sekunden',
  );
  expect(field('Basiswertsitzungen allein zur BID-Zeit')).toHaveTextContent(
    '20 abgeschlossene Sitzungen',
  );
  expect(field('Basiswertsitzungen allein zur BID-Zeit')).toHaveTextContent('2026-09-21T13:00:00Z');
  expect(field('Produktsitzung zum Serverlesezeitpunkt')).toHaveTextContent('2026-09-21T13:05:00Z');
  const checks = within(
    screen.getByRole('list', { name: 'Voraussetzungen für den Original-Geldkurs' }),
  );
  expect(checks.getAllByRole('listitem')).toHaveLength(8);
  expect(checks.getByText('Historischer Produkt-Preismaßstab · Beleg fehlt')).toBeVisible();
  expect(checks.getByText('Verifizierte offene Produktsitzung · Beleg fehlt')).toBeVisible();
  expect(field('Regelfunktion')).toHaveTextContent('B04, B05, B06 und B58 sind nicht ausgewertet');
  expect(field('Betriebszustand')).toHaveTextContent('nicht als laufende Überwachung aktiviert');
  await user.click(screen.getByText('Geldkursquelle, Positionsbasis und Kalenderbelege'));
  expect(field('Restbestand und Bruttoeinstand des Ausführungsowners')).toHaveTextContent(
    'Ø 0.987654321 · Kostenbeitrag 6.913580247',
  );
  expect(field('Gemeinsame Snapshotzeit (keine BID-Seitenzeit)')).toHaveTextContent(
    '2026-09-21T12:59:58Z',
  );
  expect(field('Originalzeittext der BID-Seite')).toHaveTextContent(
    '2026-09-21T15:00:00+02:00 · Feld bid_at',
  );
  expect(field('Quellenmeldung zum Handel')).toHaveTextContent(
    'OPEN · Kein verifizierter Live-Marktstatus',
  );
  expect(field('Speichergrenze')).toHaveTextContent(
    'Zeitpunkt der Speicherung nicht aufgezeichnet',
  );
  expect(field('SHA-256 des gespeicherten JSON-Payloads')).toHaveTextContent('f'.repeat(64));
  expect(field('SHA-256 des gespeicherten JSON-Payloads')).toHaveTextContent(
    'Kein Hash ursprünglicher Providerantwortbytes',
  );
  expect(view.container.querySelector('time[datetime="2026-08-31"]')).toBeInTheDocument();
  expect(view.container.querySelector('time[datetime="2026-08-31T00:00:00Z"]')).toBeNull();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(screen.getAllByRole('button')).toHaveLength(1);
  expect(readHebeltraderOriginalBid).toHaveBeenCalledOnce();
});

it('does not reuse a later server-time count or infer a twentieth close from the displayed read clock', async () => {
  const report = originalBidReport();
  report.underlying_sessions.count = {
    ...report.underlying_sessions.count!,
    completed_sessions: 19,
    completed_session_dates: report.underlying_sessions.count!.completed_session_dates.slice(0, 19),
    threshold_reached: false,
    twentieth_session_date: null,
    twentieth_closes_at: null,
  };
  report.checks[5] = {
    ...report.checks[5],
    status: 'NOT_REACHED',
    detail: 'Der spätere Schluss zählt zur Original-BID-Zeit noch nicht.',
    reasons: ['TWENTIETH_SESSION_NOT_COMPLETED_AT_BID'],
  };
  vi.mocked(readHebeltraderOriginalBid).mockResolvedValueOnce(report);
  render(<HebeltraderOriginalBid tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('Teilbelege vorhanden; Gesamtqualifikation offen');
  expect(field('Basiswertsitzungen allein zur BID-Zeit')).toHaveTextContent(
    '19 abgeschlossene Sitzungen',
  );
  expect(field('Basiswertsitzungen allein zur BID-Zeit')).not.toHaveTextContent(
    '2026-09-21T13:05:00Z',
  );
  expect(
    screen.getByText('20 Basiswertsitzungen zur Geldkurszeit · Noch nicht erreicht'),
  ).toBeVisible();
});

it('leaves legacy BID time and event-time counting absent even when a combined quote time exists', async () => {
  const user = userEvent.setup();
  vi.mocked(readHebeltraderOriginalBid).mockResolvedValueOnce(missingBidSideReport());
  render(<HebeltraderOriginalBid tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('Teilbelege vorhanden; Gesamtqualifikation offen');
  expect(field('Exakte Original-BID-Zeit')).toHaveTextContent('Nicht belegt');
  expect(field('Kursalter laut Server')).toHaveTextContent('Nicht beurteilbar');
  expect(field('Basiswertsitzungen allein zur BID-Zeit')).toHaveTextContent(
    'Keine Zählung zur BID-Zeit verfügbar',
  );
  expect(field('Basiswertsitzungen allein zur BID-Zeit')).not.toHaveTextContent('0 abgeschlossene');
  await user.click(screen.getByText('Geldkursquelle, Positionsbasis und Kalenderbelege'));
  expect(field('Gemeinsame Snapshotzeit (keine BID-Seitenzeit)')).toHaveTextContent(
    '2026-09-21T12:59:58Z',
  );
  expect(field('Originalzeittext der BID-Seite')).toHaveTextContent(
    'Nicht belegt; keine Ableitung',
  );
});

it('preserves distinct documented intervals and owner-unsuitable reasons without announcing an open market', async () => {
  const report = originalBidReport({ coverage_status: 'UNSUITABLE' });
  report.product_sessions.interval_relation = 'DIFFERENT_INTERVALS';
  report.product_sessions.at_read.interval = {
    opens_at: '2026-09-21T13:04:00Z',
    closes_at: '2026-09-21T14:00:00Z',
  };
  report.checks[2] = {
    ...report.checks[2],
    status: 'UNSUITABLE',
    detail: 'Die Währungen passen nicht; keine automatische Umrechnung.',
    reasons: ['EXECUTION_BID_CURRENCY_MISMATCH'],
  };
  vi.mocked(readHebeltraderOriginalBid).mockResolvedValueOnce(report);
  render(<HebeltraderOriginalBid tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('Belege für diesen Prüfstand ungeeignet oder fehlend');
  expect(screen.getByText(/verschiedenen dokumentierten Handelsintervallen/)).toHaveTextContent(
    'Daraus folgt kein verifiziert offener Live-Markt',
  );
  expect(screen.getByText(report.checks[2].detail)).toBeVisible();
});

it('keeps inputs during an initial error and a deliberate saved-read retry, without automatic polling', async () => {
  const user = userEvent.setup();
  vi.mocked(readHebeltraderOriginalBid).mockRejectedValueOnce(
    new Error('Technischer Lesefehler, kein fehlender Kursbeleg.'),
  );
  render(
    <>
      <label>
        Bestehender Qualifikationsentwurf
        <input defaultValue="" />
      </label>
      <HebeltraderOriginalBid tradeId="trade-1" positionId="position-1" />
    </>,
  );
  await user.type(
    screen.getByLabelText('Bestehender Qualifikationsentwurf'),
    'Mein konkreter Nachweis',
  );
  expect(await screen.findByRole('alert')).toHaveTextContent('Technischer Lesefehler');
  expect(
    screen.queryByText('Teilbelege vorhanden; Gesamtqualifikation offen'),
  ).not.toBeInTheDocument();
  expect(readHebeltraderOriginalBid).toHaveBeenCalledOnce();
  await user.click(
    screen.getByRole('button', { name: 'Gespeicherten Geldkursbeleg erneut lesen' }),
  );
  await screen.findByText('Teilbelege vorhanden; Gesamtqualifikation offen');
  expect(screen.getByLabelText('Bestehender Qualifikationsentwurf')).toHaveValue(
    'Mein konkreter Nachweis',
  );
  expect(readHebeltraderOriginalBid).toHaveBeenCalledTimes(2);
});

it('re-reads a saved report explicitly and does not keep an old qualification after a failed refresh', async () => {
  const user = userEvent.setup();
  vi.mocked(readHebeltraderOriginalBid)
    .mockResolvedValueOnce(originalBidReport())
    .mockRejectedValueOnce(new Error('Erneuter Read fehlgeschlagen.'));
  render(<HebeltraderOriginalBid tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('Teilbelege vorhanden; Gesamtqualifikation offen');
  await user.click(
    screen.getByRole('button', { name: 'Gespeicherten Geldkursbeleg erneut lesen' }),
  );
  await screen.findByRole('alert');
  expect(
    screen.queryByText('Teilbelege vorhanden; Gesamtqualifikation offen'),
  ).not.toBeInTheDocument();
  expect(readHebeltraderOriginalBid).toHaveBeenCalledTimes(2);
});

it.each(['resolve', 'reject'] as const)('ignores late %s through A → B → A', async (outcome) => {
  const pending = deferred();
  vi.mocked(readHebeltraderOriginalBid).mockReturnValueOnce(pending.promise);
  const view = render(<HebeltraderOriginalBid tradeId="trade-1" positionId="position-1" />);
  view.rerender(<HebeltraderOriginalBid tradeId="trade-2" positionId="position-2" />);
  await screen.findByText('Teilbelege vorhanden; Gesamtqualifikation offen');
  view.rerender(<HebeltraderOriginalBid tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('Teilbelege vorhanden; Gesamtqualifikation offen');
  await act(async () => {
    if (outcome === 'resolve') pending.resolve(missingBidSideReport());
    else pending.reject(new Error('Veralteter Fehler'));
    await pending.promise.catch(() => undefined);
  });
  expect(field('Exakte Original-BID-Zeit')).toHaveTextContent('2026-09-21T13:00:00Z');
  expect(screen.queryByText('Veralteter Fehler')).not.toBeInTheDocument();
  expect(vi.mocked(readHebeltraderOriginalBid).mock.calls[0][2]?.aborted).toBe(true);
});

it('invalidates the position and reload token and ignores responses after unmount', async () => {
  const pending = deferred();
  vi.mocked(readHebeltraderOriginalBid).mockReturnValue(pending.promise);
  const view = render(<HebeltraderOriginalBid tradeId="trade-1" positionId="position-1" />);
  view.rerender(<HebeltraderOriginalBid tradeId="trade-1" positionId="position-2" />);
  view.rerender(
    <HebeltraderOriginalBid tradeId="trade-1" positionId="position-2" reloadToken="basis-2" />,
  );
  view.unmount();
  expect(readHebeltraderOriginalBid).toHaveBeenCalledTimes(3);
  expect(vi.mocked(readHebeltraderOriginalBid).mock.calls.every((call) => call[2]?.aborted)).toBe(
    true,
  );
  await act(async () => {
    pending.resolve(originalBidReport());
    await pending.promise;
  });
});

it.each(['CLOSED', 'CANCELLED'] as const)(
  'keeps %s evidence inspectable without applicable rule claims',
  async (position_state) => {
    const report = missingBidSideReport({ position_state, coverage_status: 'NOT_APPLICABLE' });
    report.bid.status = 'NOT_APPLICABLE';
    report.checks = report.checks.map((check) => ({
      ...check,
      status: 'NOT_APPLICABLE',
      detail: 'Die Position ist geschlossen oder storniert.',
    }));
    vi.mocked(readHebeltraderOriginalBid).mockResolvedValueOnce(report);
    render(<HebeltraderOriginalBid tradeId="trade-1" positionId="position-1" />);
    await screen.findByText('Für diese Position nicht anwendbar');
    expect(screen.getByText(/Die gespeicherten Belege bleiben lesbar/)).toBeVisible();
    expect(screen.getAllByRole('button')).toHaveLength(1);
  },
);

it('uses the existing details basis invalidation and preserves its execution-history navigation', async () => {
  const p = position();
  const view = render(
    <MemoryRouter>
      <PositionDetails position={p} />
    </MemoryRouter>,
  );
  await screen.findByText('Teilbelege vorhanden; Gesamtqualifikation offen');
  expect(screen.getByText('Bestehender Sitzungsread bis Serverzeit')).toBeInTheDocument();
  expect(
    screen.getByRole('link', { name: 'Kauf-/Verkaufsdaten und Historie öffnen' }),
  ).toHaveAttribute('href', `${p.target}#execution-dates`);
  view.rerender(
    <MemoryRouter>
      <PositionDetails position={{ ...p, cost_basis: '21.00' }} />
    </MemoryRouter>,
  );
  await screen.findByText('Teilbelege vorhanden; Gesamtqualifikation offen');
  expect(readHebeltraderOriginalBid).toHaveBeenCalledTimes(2);
  expect(vi.mocked(readHebeltraderOriginalBid).mock.calls[0][2]?.aborted).toBe(true);
});
