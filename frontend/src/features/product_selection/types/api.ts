export type Uuid = string;
export type IsoDateTime = string;

export type DataAvailability = 'AVAILABLE' | 'MISSING' | 'INSUFFICIENT' | 'NOT_APPLICABLE';
export type CriterionOutcome = 'FULFILLED' | 'NOT_FULFILLED' | 'NOT_EVALUABLE' | 'NOT_APPLICABLE';
export type EligibilityStatus = 'ELIGIBLE' | 'INELIGIBLE' | 'NOT_EVALUABLE';
export type MetricOrigin = 'CALCULATED' | 'PROVIDER';
export type TradePlanStatus =
  | 'DRAFT'
  | 'READY_FOR_REVIEW'
  | 'APPROVED'
  | 'ABANDONED'
  | 'SUPERSEDED';

export interface ModelReferenceResponse {
  model_id: string;
  model_version: string;
}

export interface EvaluationInputResponse {
  name: string;
  value: string | null;
  availability: DataAvailability;
  source: string;
  observed_at: IsoDateTime | null;
  quality: string | null;
}

export interface CriterionResultResponse {
  criterion_id: string;
  outcome: CriterionOutcome;
  explanation: string;
  actual_value: string | null;
  expected_value: string | null;
  data_availability: DataAvailability;
}

export interface EvaluationMetricResponse {
  metric_id: string;
  value: string | null;
  unit: string | null;
  origin: MetricOrigin;
  source: string;
  formula_or_rule: string | null;
  data_availability: DataAvailability;
}

export interface ProductEvaluationResponse {
  id: Uuid;
  run_id: Uuid;
  warrant_id: Uuid;
  warrant_terms_version_id: Uuid;
  warrant_listing_id: Uuid;
  evaluated_at: IsoDateTime;
  eligibility_model: ModelReferenceResponse;
  evaluation_model: ModelReferenceResponse;
  inputs: EvaluationInputResponse[];
  criteria: CriterionResultResponse[];
  metrics: EvaluationMetricResponse[];
  eligibility_status: EligibilityStatus;
  reasons: string[];
}

export interface UniverseOmissionResponse {
  warrant_id: Uuid;
  reason: string;
  explanation: string;
}

export interface ProductSelectionResponse {
  id: Uuid;
  run_id: Uuid;
  product_evaluation_id: Uuid;
  selected_at: IsoDateTime;
  selected_by: Uuid;
  rationale: string | null;
}

export interface ProductSelectionRunSummaryResponse {
  id: Uuid;
  trade_plan_id: Uuid;
  trade_plan_version_id: Uuid;
  trade_plan_version_status: TradePlanStatus;
  underlying_id: Uuid;
  evaluated_at: IsoDateTime;
  universe_model: ModelReferenceResponse;
  eligibility_model: ModelReferenceResponse;
  evaluation_model: ModelReferenceResponse;
  created_at: IsoDateTime;
  created_by: Uuid;
}

export interface ProductSelectionRunDetailResponse {
  run: ProductSelectionRunSummaryResponse;
  evaluations: ProductEvaluationResponse[];
  universe_omissions: UniverseOmissionResponse[];
  selection: ProductSelectionResponse | null;
}

export interface StartProductSelectionRunRequest {
  trade_plan_id: Uuid;
  trade_plan_version_id: Uuid;
  evaluated_at?: IsoDateTime | null;
}

export interface SelectProductRequest {
  product_evaluation_id: Uuid;
  rationale?: string | null;
}
