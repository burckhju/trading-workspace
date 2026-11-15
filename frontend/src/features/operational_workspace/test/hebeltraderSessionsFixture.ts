import type {
  CompletedSessionCount,
  HebeltraderSessionsReport,
  SessionDay,
  SessionEvidenceCurrent,
  SessionPeriodView,
} from '../hebeltraderSessions';

export function sessionCalendar(
  overrides: Partial<SessionEvidenceCurrent> = {},
): SessionEvidenceCurrent {
  return {
    workspace_id: 'workspace-1',
    instrument_kind: 'UNDERLYING',
    instrument_id: 'underlying-1',
    known_at: '2026-09-11T11:30:00Z',
    revision_id: 'calendar-revision-2',
    supersedes_revision_id: 'calendar-revision-1',
    revision_number: 2,
    calendar_id: 'synthetic-calendar',
    calendar_version: 'document-v2',
    binding: {
      instrument_kind: 'UNDERLYING',
      instrument_id: 'underlying-1',
      listing_id: 'explicit-listing-1',
      trading_venue_id: 'venue-1',
      venue_mic: 'XETR',
      timezone: 'Europe/Berlin',
      market_segment: 'Synthetisches Segment',
      valid_from: '2026-01-01',
      valid_through: '2026-12-31',
    },
    coverage_start: '2026-09-01',
    coverage_end: '2026-09-30',
    evidence_status: 'ACTIVE',
    source: {
      manifest_sha256: 'a'.repeat(64),
      document_sha256: 'b'.repeat(64),
      document_filename: 'synthetic-sessions.pdf',
      document_media_type: 'application/pdf',
      publisher: 'Synthetischer Kalenderherausgeber',
      reference: 'Synthetisches Sitzungsdokument, Seiten 2–3',
      published_at: null,
      published_on: '2026-08-31',
      retrieved_at: '2026-09-01T08:00:00Z',
      reviewed_at: '2026-09-01T09:00:00Z',
      review_reference: 'Dokumentprüfung, synthetischer Fall 42',
      recorded_by: 'reviewer-1',
    },
    recorded_at: '2026-09-01T10:00:00Z',
    read_at: '2026-09-11T11:30:00Z',
    status: 'AVAILABLE',
    reasons: [],
    verification: 'MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION',
    operation_status: 'READ_ONLY',
    ...overrides,
  };
}

export function sessionPeriod(overrides: Partial<SessionPeriodView> = {}): SessionPeriodView {
  return {
    start_date: '2026-09-09',
    end_date: '2026-09-11',
    status: 'COMPLETE',
    fingerprint: 'c'.repeat(64),
    missing_dates: [],
    days: [
      {
        session_date: '2026-09-09',
        status: 'SESSION',
        intervals: [
          { opens_at: '2026-09-09T09:00:00+02:00', closes_at: '2026-09-09T12:00:00+02:00' },
          { opens_at: '2026-09-09T13:00:00+02:00', closes_at: '2026-09-09T17:30:00+02:00' },
        ],
        source_reference: 'Synthetisches Dokument, reguläre Sitzung 2026-09-09',
      },
      {
        session_date: '2026-09-10',
        status: 'CLOSED',
        intervals: [],
        source_reference: 'Synthetisches Dokument, Schließtag 2026-09-10',
      },
      {
        session_date: '2026-09-11',
        status: 'SESSION',
        intervals: [
          { opens_at: '2026-09-11T09:00:00+02:00', closes_at: '2026-09-11T13:00:00+02:00' },
        ],
        source_reference: 'Synthetisches Dokument, verkürzte Sitzung 2026-09-11',
      },
    ],
    ...overrides,
  };
}

export function sessionCount(
  overrides: Partial<CompletedSessionCount> = {},
): CompletedSessionCount {
  return {
    status: 'AVAILABLE',
    anchor_date: '2026-09-08',
    evaluated_at: '2026-09-11T11:30:00Z',
    completed_sessions: 2,
    completed_session_dates: ['2026-09-09', '2026-09-11'],
    twentieth_session_date: null,
    twentieth_closes_at: null,
    threshold_reached: false,
    reasons: [],
    threshold_sessions: 20,
    ...overrides,
  };
}

export function sessionReport(
  overrides: Partial<HebeltraderSessionsReport> = {},
): HebeltraderSessionsReport {
  return {
    definition_version: 'hebeltrader-sessions-v1',
    baseline_id: 'HEBELTRADER_CONFIRMED_BASELINE',
    baseline_version: '1.0.0',
    implementation_status: 'F207_3_SESSION_EVIDENCE_AND_COUNT_ONLY',
    rule_evaluation_status: 'B04_B05_B06_B58_NOT_EVALUATED',
    operation_status: 'NOT_ACTIVATED',
    read_status: 'READ_ONLY',
    trade_id: 'trade-1',
    position_id: 'position-1',
    product_id: 'product-1',
    underlying_id: 'underlying-1',
    position_state: 'OPEN',
    basis_id: 'position-basis-1',
    read_started_at: '2026-09-11T11:30:00Z',
    read_completed_at: '2026-09-11T11:30:01Z',
    evaluated_at: '2026-09-11T11:30:00Z',
    entry: {
      execution_id: 'effective-buy-1',
      executed_at: null,
      executed_on: '2026-09-08',
      execution_timezone: 'Europe/Berlin',
      time_precision: 'DATE_ONLY',
    },
    calendar: sessionCalendar(),
    period: sessionPeriod(),
    count: sessionCount(),
    issues: [],
    notices: ['Synthetische Dokumentbelege; keine Aussage über tatsächliche Marktsitzungen.'],
    ...overrides,
  };
}

export function unavailableSessionReport(
  overrides: Partial<HebeltraderSessionsReport> = {},
): HebeltraderSessionsReport {
  return sessionReport({
    calendar: sessionCalendar({
      revision_id: null,
      supersedes_revision_id: null,
      revision_number: null,
      calendar_id: null,
      calendar_version: null,
      binding: null,
      coverage_start: null,
      coverage_end: null,
      evidence_status: null,
      source: null,
      recorded_at: null,
      status: 'MISSING',
      reasons: ['SESSION_BINDING_MISSING'],
    }),
    period: sessionPeriod({
      status: 'NOT_REQUESTED',
      start_date: null,
      end_date: null,
      fingerprint: null,
      days: [],
      missing_dates: [],
    }),
    count: sessionCount({
      status: 'NOT_ASSESSABLE',
      anchor_date: null,
      completed_sessions: null,
      completed_session_dates: [],
      threshold_reached: null,
      reasons: ['SESSION_BINDING_MISSING'],
    }),
    issues: [
      {
        code: 'SESSION_BINDING_MISSING',
        detail: 'Eine ausdrücklich zugeordnete Kalenderrevision fehlt.',
      },
    ],
    ...overrides,
  });
}

/** Explicit synthetic days, not an exchange calendar or production rule. */
export function syntheticSessionDays(total: number): SessionDay[] {
  return Array.from({ length: total }, (_, index) => {
    const day = new Date(Date.UTC(2026, 8, 1 + index)).toISOString().slice(0, 10);
    return {
      session_date: day,
      status: 'SESSION',
      intervals: [{ opens_at: `${day}T09:00:00+02:00`, closes_at: `${day}T17:00:00+02:00` }],
      source_reference: `Synthetischer Einzelbeleg ${index + 1}`,
    };
  });
}
