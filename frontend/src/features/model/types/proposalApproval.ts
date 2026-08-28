export interface ApprovedModelVersion {
  id: string;
  model_id: string;
  version: number;
  status: 'APPROVED';
  definition: Record<string, unknown>;
  change_summary: string;
  created_at: string;
  created_by: string;
  previous_version_id: string | null;
}

export interface ModelApprovalSummary {
  id: string;
  proposal_id: string | null;
  model_version_id: string;
  approved_at: string;
  approved_by: string;
  correlation_id: string | null;
}

export interface ProposalApprovalResult {
  model_version: ApprovedModelVersion;
  approval: ModelApprovalSummary;
}
