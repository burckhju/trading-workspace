export interface GovernedModelSummary {
  id: string;
  model_key: string;
  name: string;
  purpose: string;
  created_at: string;
  created_by: string;
}

export interface GovernedModelVersion {
  id: string;
  model_id: string;
  version: number;
  status: 'DRAFT' | 'APPROVED';
  definition: Record<string, unknown>;
  change_summary: string;
  created_at: string;
  created_by: string;
  previous_version_id: string | null;
}

export interface ModelChangeProposalSummary {
  id: string;
  model_id: string;
  base_model_version_id: string;
  hypothesis_id: string;
  status: 'DRAFT' | 'VALIDATED' | 'APPROVED';
  proposed_definition: Record<string, unknown>;
  rationale: string;
  created_at: string;
  created_by: string;
}

export interface CreateModelChangeProposalInput {
  model_id: string;
  base_model_version_id: string;
  hypothesis_id: string;
  proposed_definition: Record<string, unknown>;
  rationale: string;
}
