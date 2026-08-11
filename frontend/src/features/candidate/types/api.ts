export type Candidate = {
  id: string;
  underlying_id: string;
  status: string;
  created_at: string;
  created_by: string;
};

export type CandidateCriterion = {
  criterion_id: string;
  group: 'MARKET' | 'SECTOR' | 'UNDERLYING';
  severity: 'REQUIRED' | 'WARNING' | 'INFORMATIONAL';
  evaluation: 'FULFILLED' | 'NOT_FULFILLED' | 'NOT_EVALUABLE' | 'SKIPPED';
  source: string;
  actual_value: string | null;
  expected_value: string | null;
  numeric_value: string | null;
  explanation: string;
};

export type CandidateEvaluation = {
  id: string;
  version: number;
  direction: string;
  model_id: string;
  model_version: string;
  qualification: 'QUALIFIED' | 'NOT_QUALIFIED' | 'NOT_EVALUABLE';
  quality_status: string;
  warnings: string[];
  evaluated_at: string;
  criteria: CandidateCriterion[];
};

export type CandidateLiveWorkflowStep = {
  code: string;
  label: string;
  status: 'COMPLETE' | 'BLOCKED';
  detail: string;
  action: string | null;
  resource_id: string | null;
  action_params: Record<string, string> | null;
};

export type CandidateLiveWorkflow = {
  candidate_id: string;
  underlying_id: string;
  as_of: string;
  ready: boolean;
  can_evaluate: boolean;
  next_action: string | null;
  steps: CandidateLiveWorkflowStep[];
};
