export type Uuid = string;
export type IsoDate = string;
export type IsoDateTime = string;
export type DecimalString = string;

export type PostTradeObservationStatus = 'ACTIVE' | 'COMPLETED';
export type ExitReviewStatus = 'DRAFT' | 'FINALIZED';
export type ExitReviewCurrentness = 'CURRENT' | 'STALE';

export type ExitReviewAssessment = 'GOOD' | 'ACCEPTABLE' | 'IMPROVABLE' | 'NOT_ASSESSABLE';

export interface ObservationResponse {
  id: Uuid;
  trade_id: Uuid;
  status: PostTradeObservationStatus;
  underlying_listing_id: Uuid;
  target_observation_count: number;
  available_observation_count: number;
  missing_observation_count: number;
  is_complete: boolean;
  started_at: IsoDateTime;
  completed_at: IsoDateTime | null;
  created_at: IsoDateTime;
}

export interface ExitExecutionResponse {
  execution_id: Uuid;
  quantity: DecimalString;
  price_per_unit: DecimalString;
  executed_at: IsoDateTime;
}

export interface ActualExitResponse {
  full_exit_at: IsoDateTime;
  realized_gross_pnl: DecimalString;
  executions: ExitExecutionResponse[];
}

export interface ObservationPointResponse {
  trading_date: IsoDate;
  open: DecimalString;
  high: DecimalString;
  low: DecimalString;
  close: DecimalString;
  adjusted_close: DecimalString | null;
  quality_status: string | null;
}

export interface ObservedExtremeResponse {
  trading_date: IsoDate;
  value: DecimalString;
}

export interface LevelCrossingResponse {
  level: DecimalString;
  crossed: boolean;
  first_crossed_on: IsoDate | null;
}

export interface CounterfactualEvidenceResponse {
  available_observation_count: number;
  target_observation_count: number;
  horizon_complete: boolean;
  points: ObservationPointResponse[];
  highest_high: ObservedExtremeResponse | null;
  lowest_low: ObservedExtremeResponse | null;
  final_close: ObservedExtremeResponse | null;
  target_crossings: LevelCrossingResponse[];
  stop_crossing: LevelCrossingResponse | null;
}

export interface ProductContextResponse {
  warrant_id: Uuid;
  underlying_id: Uuid;
  historical_warrant_terms_version_id: Uuid | null;
  maturity_date: IsoDate | null;
  historical_underlying_listing_id: Uuid | null;
}

export interface PlanningContextResponse {
  trade_plan_id: Uuid | null;
  trade_plan_version_id: Uuid | null;
  original_stop: DecimalString | null;
  original_targets: DecimalString[];
}

export interface ManagementLevelResponse {
  event_id: Uuid;
  kind: string;
  effective_at: IsoDateTime;
  numeric_value: DecimalString | null;
}

export interface ObservationEvidenceResponse {
  observation_id: Uuid;
  trade_id: Uuid;
  product_context: ProductContextResponse | null;
  planning_context: PlanningContextResponse;
  management_levels: ManagementLevelResponse[];
  actual_exit: ActualExitResponse;
  counterfactual: CounterfactualEvidenceResponse;
}

export interface ExitReviewDraftRequest {
  timing: ExitReviewAssessment;
  process_adherence: ExitReviewAssessment;
  risk_decision: ExitReviewAssessment;
  overall_exit_decision: ExitReviewAssessment;
  rationale: string;
}

export interface ExitReviewResponse {
  exit_review_id: Uuid;
  current_version_id: Uuid;
  version: number;
  status: ExitReviewStatus;
  currentness: ExitReviewCurrentness;
  timing: ExitReviewAssessment | null;
  process_adherence: ExitReviewAssessment | null;
  risk_decision: ExitReviewAssessment | null;
  overall_exit_decision: ExitReviewAssessment | null;
  rationale: string | null;
  created_at: IsoDateTime;
  created_by: Uuid;
  finalized_at: IsoDateTime | null;
  finalized_by: Uuid | null;
  supersedes_version_id: Uuid | null;
  stale_at: IsoDateTime | null;
  stale_reason: string | null;
}

export interface HandoffResponse {
  ready: boolean;
  reason: string;
  post_trade_observation_id: Uuid | null;
  exit_review_id: Uuid | null;
  exit_review_version_id: Uuid | null;
}
