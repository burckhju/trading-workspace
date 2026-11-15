import { MarketApiError, requestJson } from '../../market/services/http';
import {
  sessionCalendar,
  sessionCount,
  sessionPeriod,
  sessionReport,
  unavailableSessionReport,
} from '../test/hebeltraderSessionsFixture';
import { readHebeltraderSessions, verifyHebeltraderSessions } from './hebeltraderSessions';

vi.mock('../../market/services/http', async (original) => ({
  ...(await original<typeof import('../../market/services/http')>()),
  requestJson: vi.fn(),
}));

it('uses only the exact position-scoped GET and preserves original clocks, provenance and cancellation', async () => {
  const report = sessionReport({ trade_id: 'trade/a', position_id: 'position/b' });
  vi.mocked(requestJson).mockResolvedValueOnce(report);
  const signal = new AbortController().signal;
  expect(await readHebeltraderSessions('trade/a', 'position/b', signal)).toBe(report);
  expect(requestJson).toHaveBeenCalledOnce();
  expect(requestJson).toHaveBeenCalledWith(
    expect.stringMatching(/trades\/trade%2Fa\/hebeltrader-sessions\?position_id=position%2Fb$/),
    { signal },
  );
  expect(report.period.days[0].intervals[0].opens_at).toBe('2026-09-09T09:00:00+02:00');
  expect(report.calendar.source?.published_on).toBe('2026-08-31');
});

it('accepts a real zero on day zero without inventing later rows or requiring a complete requested period', () => {
  const report = sessionReport({
    entry: {
      execution_id: 'buy-today',
      executed_at: '2026-09-11T10:00:00Z',
      executed_on: null,
      execution_timezone: null,
      time_precision: 'EXACT',
    },
    period: sessionPeriod({
      status: 'NOT_REQUESTED',
      days: [],
      start_date: null,
      end_date: null,
      fingerprint: null,
    }),
    count: sessionCount({
      anchor_date: '2026-09-11',
      completed_sessions: 0,
      completed_session_dates: [],
    }),
  });
  expect(verifyHebeltraderSessions(report, 'trade-1', 'position-1')).toBe(report);
});

it('preserves missing, withdrawn and ambiguous entry evidence with owner reasons instead of protocol errors', () => {
  const missing = unavailableSessionReport();
  expect(verifyHebeltraderSessions(missing, 'trade-1', 'position-1')).toBe(missing);
  const withdrawn = unavailableSessionReport({
    calendar: sessionCalendar({
      status: 'UNSUITABLE',
      evidence_status: 'WITHDRAWN',
      reasons: ['SESSION_EVIDENCE_WITHDRAWN'],
    }),
  });
  expect(verifyHebeltraderSessions(withdrawn, 'trade-1', 'position-1')).toBe(withdrawn);
  const ambiguous = unavailableSessionReport({
    entry: { ...sessionReport().entry!, execution_timezone: 'Unbekannt' },
    issues: [
      {
        code: 'ENTRY_TIMEZONE_INVALID',
        detail: 'Die Zeitzone des Datumsbelegs ist nicht geeignet.',
      },
    ],
  });
  expect(verifyHebeltraderSessions(ambiguous, 'trade-1', 'position-1')).toBe(ambiguous);
});

it('accepts incomplete raw days and explicit missing dates without a count', () => {
  const report = unavailableSessionReport({
    calendar: sessionCalendar(),
    period: sessionPeriod({
      status: 'INCOMPLETE',
      missing_dates: ['2026-09-10'],
      days: [{ ...sessionPeriod().days[0], status: 'UNKNOWN', intervals: [] }],
    }),
    count: sessionCount({
      status: 'NOT_ASSESSABLE',
      completed_sessions: null,
      completed_session_dates: [],
      threshold_reached: null,
      reasons: ['SESSION_DAYS_UNKNOWN', 'SESSION_DAYS_MISSING'],
    }),
  });
  expect(verifyHebeltraderSessions(report, 'trade-1', 'position-1')).toBe(report);
});

it('rejects foreign identities, altered rule scope, unsuitable clocks and contradictory available summaries', () => {
  const original = sessionReport();
  const calendar = sessionCalendar();
  const cases: unknown[] = [
    null,
    [],
    { ...original, trade_id: 'other' },
    { ...original, position_id: 'other' },
    { ...original, operation_status: 'ACTIVE' },
    { ...original, rule_evaluation_status: 'B04_EVALUATED' },
    { ...original, implementation_status: 'BASELINE_COMPLETE' },
    { ...original, read_status: 'WRITE' },
    { ...original, definition_version: 'future' },
    { ...original, calendar: { ...calendar, instrument_id: 'foreign-underlying' } },
    { ...original, calendar: { ...calendar, instrument_kind: 'WARRANT' } },
    { ...original, calendar: { ...calendar, verification: 'INDEPENDENT_VERIFICATION' } },
    { ...original, calendar: { ...calendar, source: null } },
    {
      ...original,
      calendar: { ...calendar, binding: { ...calendar.binding, instrument_id: 'foreign' } },
    },
    {
      ...original,
      calendar: { ...calendar, binding: { ...calendar.binding, timezone: 'Unknown/Zone' } },
    },
    {
      ...original,
      calendar: { ...calendar, source: { ...calendar.source, manifest_sha256: 'missing' } },
    },
    {
      ...original,
      calendar: {
        ...calendar,
        source: { ...calendar.source, published_at: '2026-08-31T00:00:00Z' },
      },
    },
    { ...original, evaluated_at: '2026-09-11T11:30:00' },
    { ...original, entry: { ...original.entry, executed_on: '2026-02-30' } },
    { ...original, period: { ...original.period, status: 'INCOMPLETE' } },
    { ...original, period: { ...original.period, status: 'NOT_REQUESTED' } },
    {
      ...original,
      period: { ...original.period, days: [original.period.days[1], original.period.days[0]] },
    },
    {
      ...original,
      period: { ...original.period, days: [{ ...original.period.days[0], status: 'CLOSED' }] },
    },
    {
      ...original,
      period: {
        ...original.period,
        days: [
          {
            ...original.period.days[0],
            intervals: [{ opens_at: '2026-09-09T09:00:00', closes_at: '2026-09-09T17:30:00Z' }],
          },
        ],
      },
    },
    { ...original, count: { ...original.count, evaluated_at: '2026-09-11T12:30:00Z' } },
    { ...original, count: { ...original.count, completed_sessions: 999 } },
    { ...original, count: { ...original.count, threshold_reached: true } },
    { ...original, count: { ...original.count, status: 'NOT_ASSESSABLE' } },
    { ...original, issues: [{ code: 'SESSION_DAYS_MISSING' }] },
  ];
  for (const invalid of cases)
    expect(() => verifyHebeltraderSessions(invalid, 'trade-1', 'position-1')).toThrow(
      'nicht sicher zuordnen',
    );
});

it('keeps permission and transport failures distinct from absent calendar evidence', async () => {
  vi.mocked(requestJson).mockRejectedValueOnce(
    new MarketApiError(403, {
      code: 'FORBIDDEN',
      message: 'Forbidden',
      details: [],
      timestamp: '2026-09-11T11:30:00Z',
    }),
  );
  await expect(readHebeltraderSessions('trade-1', 'position-1')).rejects.toThrow(
    'Keine Berechtigung',
  );
  vi.mocked(requestJson).mockRejectedValueOnce(new Error('offline'));
  await expect(readHebeltraderSessions('trade-1', 'position-1')).rejects.toThrow(
    'Fehlende Kalenderbelege sind damit nicht festgestellt',
  );
});
