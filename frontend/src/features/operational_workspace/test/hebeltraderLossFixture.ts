import type {
  HebeltraderLossReport,
  LossAssessmentView,
  LossEpisodeView,
} from '../hebeltraderLoss';

export function lossAssessment(overrides: Partial<LossAssessmentView> = {}): LossAssessmentView {
  return {
    id: 'assessment-1',
    evaluated_at: '2026-11-17T12:00:00Z',
    recorded_at: '2026-11-17T12:00:00Z',
    outcome: 'NOT_ASSESSABLE',
    reasons: ['B58_REAL_SOURCE_PATH_NOT_QUALIFIED'],
    bid_at: '2026-11-17T11:59:00Z',
    bid: '0.48',
    gross_entry: '0.55',
    currency: 'EUR',
    remaining_quantity: 2300,
    completed_sessions_at_bid: 20,
    owner_basis_id: 'synthetic-owner-basis',
    ...overrides,
  };
}
export function lossEpisode(overrides: Partial<LossEpisodeView> = {}): LossEpisodeView {
  return {
    id: 'episode-1',
    episode_number: 1,
    alert_id: 'alert-1',
    opening_assessment_id: 'opening-assessment',
    closing_assessment_id: null,
    opened_at: '2026-11-17T11:00:00Z',
    closed_at: null,
    close_reason: null,
    ...overrides,
  };
}
export function lossReport(overrides: Partial<HebeltraderLossReport> = {}): HebeltraderLossReport {
  return {
    trade_id: 'trade-1',
    position_id: 'position-1',
    activation_status: 'NOT_ACTIVATED',
    runner_enabled: false,
    source_qualification_references: [],
    latest_assessment: null,
    active_episode: null,
    recent_episodes: [],
    assessment_count: 0,
    episode_count: 0,
    read_at: '2026-11-17T12:01:00Z',
    definition_version: 'hebeltrader-b04-b57-v1',
    rule_scope: 'B04_B57_WITH_B58_INPUTS',
    baseline_id: 'HEBELTRADER_CONFIRMED_BASELINE',
    baseline_version: '1.0.0',
    implementation_status: 'B04_B57_IMPLEMENTED',
    full_baseline_activated: false,
    remaining_scope: ['B05', 'B06', 'F207_2_PROTECTION', 'F207_5_LIFECYCLE_ACCEPTANCE'],
    read_status: 'READ_ONLY',
    ...overrides,
  };
}
