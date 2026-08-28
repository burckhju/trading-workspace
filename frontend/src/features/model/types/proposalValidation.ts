export type ValidationConclusion = 'SUPPORTS' | 'INCONCLUSIVE' | 'CONTRADICTS';

export interface ModelValidationSummary {
  id: string;
  proposal_id: string;
  method: 'RETROSPECTIVE';
  evidence_cutoff_at: string;
  conclusion: ValidationConclusion;
  metrics: Record<string, unknown>;
  notes: string | null;
  created_at: string;
  created_by: string;
}

export interface CreateModelValidationInput {
  evidence_ids: string[];
  evidence_cutoff_at: string;
  conclusion: ValidationConclusion;
  metrics: Record<string, unknown>;
  notes: string | null;
}
