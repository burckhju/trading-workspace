export type LossOutcome = 'LOSS' | 'RECOVERED' | 'NOT_ASSESSABLE' | 'NOT_REACHED' | 'CLOSED';

export interface LossAssessmentView {
  id: string;
  evaluated_at: string;
  recorded_at: string;
  outcome: LossOutcome;
  reasons: string[];
  bid_at: string | null;
  bid: string | null;
  gross_entry: string;
  currency: string | null;
  remaining_quantity: number;
  completed_sessions_at_bid: number | null;
  owner_basis_id: string;
}

export interface LossEpisodeView {
  id: string;
  episode_number: number;
  alert_id: string;
  opening_assessment_id: string;
  closing_assessment_id: string | null;
  opened_at: string;
  closed_at: string | null;
  close_reason: string | null;
}

export interface HebeltraderLossReport {
  trade_id: string;
  position_id: string;
  activation_status: 'NOT_ACTIVATED' | 'BLOCKED_SOURCE' | 'SCOPE_ENABLED';
  runner_enabled: boolean;
  source_qualification_references: string[];
  latest_assessment: LossAssessmentView | null;
  active_episode: LossEpisodeView | null;
  recent_episodes: LossEpisodeView[];
  assessment_count: number;
  episode_count: number;
  read_at: string;
  definition_version: 'hebeltrader-b04-b57-v1';
  rule_scope: 'B04_B57_WITH_B58_INPUTS';
  baseline_id: 'HEBELTRADER_CONFIRMED_BASELINE';
  baseline_version: '1.0.0';
  implementation_status: 'B04_B57_IMPLEMENTED';
  full_baseline_activated: false;
  remaining_scope: string[];
  read_status: 'READ_ONLY';
}
