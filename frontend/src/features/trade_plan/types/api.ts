export type Uuid = string;
export type IsoDateTime = string;

export type TradePlanOriginType = 'CANDIDATE_EVALUATION' | 'MANUAL';
export type TradeDirection = 'LONG';
export type EntryType = 'PRICE' | 'PRICE_RANGE' | 'TRIGGER';
export type TradePlanStatus =
  | 'DRAFT'
  | 'READY_FOR_REVIEW'
  | 'APPROVED'
  | 'ABANDONED'
  | 'SUPERSEDED';

export interface EntryPlanRequest {
  type: EntryType;
  currency: string;
  price?: string | number | null;
  price_from?: string | number | null;
  price_to?: string | number | null;
  trigger?: string | null;
  reference_price?: string | number | null;
  valid_until?: IsoDateTime | null;
  rationale?: string | null;
}

export interface InvalidationPlanRequest {
  stop_price?: string | number | null;
  invalidation_rule?: string | null;
  rationale?: string | null;
}

export interface TargetRequest {
  sequence: number;
  price: string | number;
  rationale?: string | null;
}

export interface RiskAssumptionsRequest {
  thesis_risk: string;
  max_loss_assumption?: string | null;
  notes?: string | null;
}

export interface TradePlanContentRequest {
  thesis: string;
  entry: EntryPlanRequest;
  invalidation: InvalidationPlanRequest;
  targets: TargetRequest[];
  risk_assumptions: RiskAssumptionsRequest;
}

export interface CreateManualTradePlanRequest extends TradePlanContentRequest {
  origin_type: 'MANUAL';
  underlying_id: Uuid;
  candidate_id?: never;
  candidate_evaluation_id?: never;
}

export interface CreateCandidateTradePlanRequest extends TradePlanContentRequest {
  origin_type: 'CANDIDATE_EVALUATION';
  candidate_id: Uuid;
  candidate_evaluation_id: Uuid;
  underlying_id?: never;
}

export type CreateTradePlanRequest = CreateManualTradePlanRequest | CreateCandidateTradePlanRequest;

export interface AmendTradePlanRequest extends TradePlanContentRequest {
  change_reason: string;
}

export interface LifecycleReasonRequest {
  reason?: string | null;
}

export interface EntryPlanResponse {
  type: EntryType;
  currency: string;
  price: string | null;
  price_from: string | null;
  price_to: string | null;
  trigger: string | null;
  reference_price: string | null;
  valid_until: IsoDateTime | null;
  rationale: string | null;
}

export interface InvalidationPlanResponse {
  stop_price: string | null;
  invalidation_rule: string | null;
  rationale: string | null;
}

export interface TargetResponse {
  sequence: number;
  price: string;
  rationale: string | null;
}

export interface RiskAssumptionsResponse {
  thesis_risk: string;
  max_loss_assumption: string | null;
  notes: string | null;
}

export interface TradePlanSummaryResponse {
  id: Uuid;
  underlying_id: Uuid;
  origin_type: TradePlanOriginType;
  candidate_id: Uuid | null;
  candidate_evaluation_id: Uuid | null;
  created_at: IsoDateTime;
  created_by: Uuid;
}

export interface CandidateEvaluationSourceResponse {
  role: string;
  source_type: string;
  source_id: Uuid;
  source_version: number;
  model_id: string;
  model_version: string;
}

export interface CandidateEvaluationProvenanceResponse {
  candidate_id: Uuid;
  evaluation_id: Uuid;
  evaluation_version: number;
  direction: string;
  model_id: string;
  model_version: string;
  qualification: string;
  quality_status: string;
  evaluated_at: IsoDateTime;
  sources: CandidateEvaluationSourceResponse[];
}

export interface ApprovalResponse {
  approval_id: Uuid;
  trade_plan_version_id: Uuid;
  version: number;
  actor: string;
  approved_at: IsoDateTime;
  correlation_id: string | null;
}

export interface LifecycleEventResponse {
  id: Uuid;
  event_type: string;
  from_status: string | null;
  to_status: string;
  reason: string | null;
  actor: string;
  correlation_id: string | null;
  occurred_at: IsoDateTime;
}

export interface TradePlanVersionResponse {
  id: Uuid;
  trade_plan_id: Uuid;
  version: number;
  direction: TradeDirection;
  thesis: string;
  entry: EntryPlanResponse;
  invalidation: InvalidationPlanResponse;
  targets: TargetResponse[];
  risk_assumptions: RiskAssumptionsResponse;
  status: TradePlanStatus;
  created_at: IsoDateTime;
  created_by: Uuid;
  previous_version_id: Uuid | null;
  change_reason: string | null;
  candidate_evaluation: CandidateEvaluationProvenanceResponse | null;
  approval: ApprovalResponse | null;
  events: LifecycleEventResponse[];
}

export interface TradePlanDetailResponse {
  plan: TradePlanSummaryResponse;
  latest_version: TradePlanVersionResponse;
}

export interface TradePlanMutationOptions {
  correlationId?: string;
}
