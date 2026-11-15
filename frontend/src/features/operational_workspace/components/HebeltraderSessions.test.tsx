import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { position } from '../../../test/positionFixture';
import type { HebeltraderSessionsReport } from '../hebeltraderSessions';
import { readHebeltraderSessions } from '../services/hebeltraderSessions';
import {
  sessionCalendar,
  sessionCount,
  sessionPeriod,
  sessionReport,
  syntheticSessionDays,
  unavailableSessionReport,
} from '../test/hebeltraderSessionsFixture';
import { HebeltraderSessions } from './HebeltraderSessions';
import { PositionDetails } from './PositionDetails';

vi.mock('../services/hebeltraderSessions', () => ({ readHebeltraderSessions: vi.fn() }));
vi.mock('./PositionPriceHistory', () => ({ PositionPriceHistory: () => null }));
vi.mock('./HebeltraderEvidenceCoverage', () => ({ HebeltraderEvidenceCoverage: () => null }));
vi.mock('./HebeltraderTargetHistory', () => ({ HebeltraderTargetHistory: () => null }));
vi.mock('../../alert/components/PositionRiskPanel', () => ({ PositionRiskPanel: () => null }));

beforeEach(() => {
  vi.mocked(readHebeltraderSessions)
    .mockReset()
    .mockImplementation((tradeId, positionId) =>
      Promise.resolve(sessionReport({ trade_id: tradeId, position_id: positionId })),
    );
});

function deferred() {
  let resolve!: (value: HebeltraderSessionsReport) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<HebeltraderSessionsReport>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

it('shows the server count, explicit calendar provenance and original date precision without evaluating or activating rules', async () => {
  const user = userEvent.setup();
  const view = render(<HebeltraderSessions tradeId="trade-1" positionId="position-1" />);
  expect(screen.getByText('Basiswertsitzungen werden gelesen …')).toBeInTheDocument();
  await screen.findByText('2 abgeschlossene Basiswertsitzungen');
  expect(
    screen.getByText(/serverseitiger Lesezeitpunkt, keine Original-BID-Zeit/),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      'Kalenderbelege und Sitzungszählung. B04, B05, B06 und B58 sind nicht ausgewertet.',
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByText('Dieser Teilschnitt ist nicht als laufende Überwachung aktiviert.'),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/Produktfristen und die Zählung seit Z1 sind hier nicht enthalten/),
  ).toBeInTheDocument();
  const table = within(screen.getByRole('table', { name: 'Dokumentierte Basiswert-Kalendertage' }));
  expect(table.getAllByText('Als abgeschlossen gezählt')).toHaveLength(2);
  expect(table.getByText('Dokumentiert geschlossen')).toBeInTheDocument();
  expect(table.getByText('2026-09-09T09:00:00+02:00')).toBeInTheDocument();
  expect(table.getByText('2026-09-09T13:00:00+02:00')).toBeInTheDocument();
  expect(table.getByText('2026-09-11T13:00:00+02:00')).toBeInTheDocument();
  await user.click(screen.getByText('Kalenderbindung, Quelle und Zeitstände'));
  expect(
    screen.getByText(/keine unabhängige Verifikation durch das System und kein Live-Marktstatus/),
  ).toBeVisible();
  expect(screen.getByText('a'.repeat(64))).toBeVisible();
  expect(screen.getByText('b'.repeat(64))).toBeVisible();
  expect(screen.getByText('calendar-revision-1')).toBeVisible();
  expect(screen.getByText(/underlying-1 · explicit-listing-1/)).toBeVisible();
  expect(screen.getByText('Synthetisches Sitzungsdokument, Seiten 2–3')).toBeVisible();
  expect(view.container.querySelector('time[datetime="2026-08-31"]')).toBeInTheDocument();
  expect(view.container.querySelector('time[datetime="2026-08-31T00:00:00Z"]')).toBeNull();
  expect(view.container.querySelector('time[datetime="2026-09-08T00:00:00Z"]')).toBeNull();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
  expect(readHebeltraderSessions).toHaveBeenCalledOnce();
});

it('presents the supplied twentieth close without turning the reached count into a B04 or B58 result', async () => {
  const days = syntheticSessionDays(20);
  const evaluated_at = '2026-09-20T18:00:00Z';
  vi.mocked(readHebeltraderSessions).mockResolvedValueOnce(
    sessionReport({
      evaluated_at,
      period: sessionPeriod({
        start_date: days[0].session_date,
        end_date: days[19].session_date,
        days,
      }),
      count: sessionCount({
        evaluated_at,
        anchor_date: '2026-08-31',
        completed_sessions: 20,
        completed_session_dates: days.map((day) => day.session_date),
        threshold_reached: true,
        twentieth_session_date: '2026-09-20',
        twentieth_closes_at: '2026-09-20T17:00:00+02:00',
      }),
    }),
  );
  render(<HebeltraderSessions tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('20 abgeschlossene Basiswertsitzungen');
  expect(screen.getByText(/20\. abgeschlossene Sitzung:/)).toHaveTextContent(
    '2026-09-20 · belegter Schluss: 2026-09-20T17:00:00+02:00',
  );
  expect(screen.getByText(/kein Verlust-, Verkaufs- oder Überwachungsbefund/)).toBeInTheDocument();
  expect(screen.getByText(/B04, B05, B06 und B58 sind nicht ausgewertet/)).toBeInTheDocument();
});

it('keeps an available zero on day zero separate from an unavailable count', async () => {
  vi.mocked(readHebeltraderSessions).mockResolvedValueOnce(
    sessionReport({
      count: sessionCount({
        anchor_date: '2026-09-11',
        completed_sessions: 0,
        completed_session_dates: [],
      }),
      period: sessionPeriod({
        status: 'NOT_REQUESTED',
        start_date: null,
        end_date: null,
        days: [],
        fingerprint: null,
      }),
    }),
  );
  render(<HebeltraderSessions tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('0 abgeschlossene Basiswertsitzungen');
  expect(
    screen.getByText(/Seit Tag 0 existieren noch keine späteren Kalendertage/),
  ).toBeInTheDocument();
  expect(screen.queryByText('Nicht beurteilbar')).not.toBeInTheDocument();
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
});

it('shows owner blockers and unknown, missing and withdrawn evidence without calling it zero or inventing holidays', async () => {
  const report = unavailableSessionReport({
    calendar: sessionCalendar({
      status: 'UNSUITABLE',
      evidence_status: 'WITHDRAWN',
      reasons: ['SESSION_EVIDENCE_WITHDRAWN'],
    }),
    period: sessionPeriod({
      status: 'INCOMPLETE',
      missing_dates: ['2026-09-10'],
      days: [{ ...sessionPeriod().days[0], status: 'UNKNOWN', intervals: [] }],
    }),
    issues: [
      {
        code: 'SESSION_DAYS_UNKNOWN',
        detail: 'Die dokumentierten Tagesbelege enthalten einen ausdrücklich unbekannten Tag.',
      },
    ],
    notices: ['Der zurückgezogene Dokumentstand wird nicht durch eine ältere Revision ersetzt.'],
  });
  vi.mocked(readHebeltraderSessions).mockResolvedValueOnce(report);
  render(<HebeltraderSessions tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('Nicht beurteilbar');
  expect(screen.getByText(report.issues[0].detail)).toBeInTheDocument();
  expect(screen.getByText(report.notices[0])).toBeInTheDocument();
  expect(screen.getByText('Unbekannt')).toBeInTheDocument();
  expect(screen.getByRole('region', { name: 'Fehlende Kalendertage' })).toHaveTextContent(
    '2026-09-10',
  );
  expect(screen.queryByText('0 abgeschlossene Basiswertsitzungen')).not.toBeInTheDocument();
});

it.each(['CLOSED', 'CANCELLED'] as const)(
  'keeps %s position evidence inspectable with a not-applicable result',
  async (position_state) => {
    vi.mocked(readHebeltraderSessions).mockResolvedValueOnce(
      unavailableSessionReport({
        position_state,
        count: sessionCount({
          status: 'NOT_APPLICABLE',
          completed_sessions: null,
          completed_session_dates: [],
          threshold_reached: null,
        }),
      }),
    );
    render(<HebeltraderSessions tradeId="trade-1" positionId="position-1" />);
    await screen.findByText('Für diese Position nicht anwendbar');
    expect(screen.getByText(/Die vorhandenen Belege bleiben lesbar/)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  },
);

it('paginates all supplied day and missing-date evidence without further reads or changing the total', async () => {
  const user = userEvent.setup();
  const days = syntheticSessionDays(30);
  const missingDates = syntheticSessionDays(31).map((day) => day.session_date);
  vi.mocked(readHebeltraderSessions).mockResolvedValueOnce(
    unavailableSessionReport({
      calendar: sessionCalendar(),
      period: sessionPeriod({
        status: 'INCOMPLETE',
        days,
        missing_dates: missingDates,
        start_date: '2026-09-01',
        end_date: '2026-10-01',
      }),
    }),
  );
  render(<HebeltraderSessions tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('Nicht beurteilbar');
  const table = screen.getByRole('table', { name: 'Dokumentierte Basiswert-Kalendertage' });
  expect(within(table).getAllByRole('row')).toHaveLength(26);
  const dayPages = within(screen.getByRole('navigation', { name: 'Seiten der Tagesbelege' }));
  await user.click(dayPages.getByRole('button', { name: 'Nächste Seite' }));
  expect(within(table).getAllByRole('row')).toHaveLength(6);
  expect(within(table).getByText('Synthetischer Einzelbeleg 30')).toBeInTheDocument();
  expect(dayPages.getByText('Seite 2 von 2 · 30 Einträge insgesamt')).toBeInTheDocument();
  await user.click(dayPages.getByRole('button', { name: 'Vorherige Seite' }));
  const missing = within(screen.getByRole('region', { name: 'Fehlende Kalendertage' }));
  await user.click(missing.getByRole('button', { name: 'Nächste Seite' }));
  expect(missing.getByText('2026-10-01')).toBeInTheDocument();
  expect(missing.getByText('Seite 2 von 2 · 31 Einträge insgesamt')).toBeInTheDocument();
  expect(readHebeltraderSessions).toHaveBeenCalledOnce();
});

it('keeps existing inputs through a failed read and a deliberate read-only retry', async () => {
  const user = userEvent.setup();
  vi.mocked(readHebeltraderSessions).mockRejectedValueOnce(
    new Error('Technischer Lesefehler, kein fehlender Kalenderbeleg.'),
  );
  render(
    <>
      <label>
        Vorhandene Belegreferenz
        <input defaultValue="" />
      </label>
      <HebeltraderSessions tradeId="trade-1" positionId="position-1" />
    </>,
  );
  await user.type(screen.getByLabelText('Vorhandene Belegreferenz'), 'Unveränderter Entwurf');
  expect(await screen.findByRole('alert')).toHaveTextContent('Technischer Lesefehler');
  expect(screen.queryByText('Nicht beurteilbar')).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Basiswertsitzungen erneut lesen' }));
  await screen.findByText('2 abgeschlossene Basiswertsitzungen');
  expect(screen.getByLabelText('Vorhandene Belegreferenz')).toHaveValue('Unveränderter Entwurf');
  expect(readHebeltraderSessions).toHaveBeenCalledTimes(2);
});

it.each(['resolve', 'reject'] as const)('ignores a late %s through A → B → A', async (outcome) => {
  const pending = deferred();
  vi.mocked(readHebeltraderSessions).mockReturnValueOnce(pending.promise);
  const view = render(<HebeltraderSessions tradeId="trade-1" positionId="position-1" />);
  view.rerender(<HebeltraderSessions tradeId="trade-2" positionId="position-2" />);
  await screen.findByText('2 abgeschlossene Basiswertsitzungen');
  view.rerender(<HebeltraderSessions tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('2 abgeschlossene Basiswertsitzungen');
  await act(async () => {
    if (outcome === 'resolve') pending.resolve(unavailableSessionReport());
    else pending.reject(new Error('Veralteter Fehler'));
    await pending.promise.catch(() => undefined);
  });
  expect(screen.queryByText('Nicht beurteilbar')).not.toBeInTheDocument();
  expect(screen.queryByText('Veralteter Fehler')).not.toBeInTheDocument();
  expect(vi.mocked(readHebeltraderSessions).mock.calls[0][2]?.aborted).toBe(true);
  expect(readHebeltraderSessions).toHaveBeenCalledTimes(3);
});

it('aborts reads after position and basis changes and on unmount', async () => {
  const pending = deferred();
  vi.mocked(readHebeltraderSessions).mockReturnValue(pending.promise);
  const view = render(<HebeltraderSessions tradeId="trade-1" positionId="position-1" />);
  view.rerender(<HebeltraderSessions tradeId="trade-1" positionId="position-2" />);
  view.rerender(
    <HebeltraderSessions tradeId="trade-1" positionId="position-2" reloadToken="changed-basis" />,
  );
  view.unmount();
  expect(readHebeltraderSessions).toHaveBeenCalledTimes(3);
  expect(vi.mocked(readHebeltraderSessions).mock.calls.every((call) => call[2]?.aborted)).toBe(
    true,
  );
  await act(async () => {
    pending.resolve(sessionReport());
    await pending.promise;
  });
});

it('uses the existing details host and reload token without altering execution navigation', async () => {
  const p = position({ trade_id: 'trade-1', position_id: 'position-1' });
  const view = render(
    <MemoryRouter>
      <PositionDetails position={p} />
    </MemoryRouter>,
  );
  await screen.findByText('2 abgeschlossene Basiswertsitzungen');
  expect(
    screen.getByRole('link', { name: 'Kauf-/Verkaufsdaten und Historie öffnen' }),
  ).toHaveAttribute('href', `${p.target}#execution-dates`);
  view.rerender(
    <MemoryRouter>
      <PositionDetails position={{ ...p, open_quantity: p.open_quantity + 1 }} />
    </MemoryRouter>,
  );
  await screen.findByText('2 abgeschlossene Basiswertsitzungen');
  expect(readHebeltraderSessions).toHaveBeenCalledTimes(2);
  expect(vi.mocked(readHebeltraderSessions).mock.calls[0][2]?.aborted).toBe(true);
});
