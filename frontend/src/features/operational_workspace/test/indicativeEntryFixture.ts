import type {
  IndicativeAssessmentView,
  IndicativeEntryReport,
  IndicativeEpisodeView,
} from '../indicativeEntry';

// Isolated synthetic records; no provider, real position or notification calls.
export function indicativeAssessment(
  overrides: Partial<IndicativeAssessmentView> = {},
): IndicativeAssessmentView {
  return {
    id: 'synthetic-assessment',
    rule_version: 'indicative-entry-review-v2',
    evaluated_at: '2026-11-18T15:30:00Z',
    recorded_at: '2026-11-18T15:30:01Z',
    outcome: 'UNAVAILABLE',
    reasons: ['REVIEW_RECOVERY_EVIDENCE_WEAKER'],
    evaluation_mode: 'DELAYED_SOURCE_BID',
    bid: '0.56',
    gross_entry: '0.55',
    currency: 'EUR',
    remaining_quantity: 2300,
    original_bid_at: null,
    source_quote_at: '2026-11-18T15:10:00Z',
    source_time_basis: 'SHARED_QUOTE_TIME',
    source_freshness: 'WITHIN_1800_SECONDS',
    product_scale_quality: 'CURRENT_UNIT_HISTORY_ASSUMED',
    history_continuity_assumed: true,
    received_at: '2026-11-18T15:29:00Z',
    completed_sessions: 19,
    session_count_at: '2026-11-18T15:10:00Z',
    review_completed_sessions: 20,
    review_due: true,
    owner_basis_id: 'synthetic-economic-owner',
    source: {
      provider: 'SYNTHETIC',
      venue_mic: 'XSYN',
      source_status_point: 'OPEN',
      source_status_observed_at: '2026-11-17T15:10:00Z',
      source_status_captured_at: '2026-11-18T15:29:00Z',
    },
    ...overrides,
  };
}

export function indicativeEpisode(
  overrides: Partial<IndicativeEpisodeView> = {},
): IndicativeEpisodeView {
  return {
    id: 'synthetic-entry-loss',
    kind: 'ENTRY_LOSS',
    rule_version: 'indicative-entry-review-v1',
    episode_number: 1,
    alert_id: 'synthetic-alert',
    opening_assessment_id: 'synthetic-opening',
    closing_assessment_id: null,
    opened_at: '2026-11-17T15:00:00Z',
    closed_at: null,
    close_reason: null,
    ...overrides,
  };
}

export function indicativeReport(
  overrides: Partial<IndicativeEntryReport> = {},
): IndicativeEntryReport {
  return {
    trade_id: 'synthetic-trade',
    position_id: 'synthetic-position',
    activation_status: 'NOT_ACTIVATED',
    runner_enabled: false,
    notifications_enabled: false,
    latest_assessment: null,
    active_episodes: [],
    recent_episodes: [],
    assessment_count: 0,
    episode_count: 0,
    read_at: '2026-11-18T15:31:00Z',
    definition_version: 'indicative-entry-review-v2',
    scope: 'INDICATIVE_ENTRY_V2',
    qualified_b04: false,
    full_baseline_activated: false,
    read_status: 'READ_ONLY',
    ...overrides,
  };
}
