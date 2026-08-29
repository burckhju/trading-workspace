import type { ApprovedModelVersion } from './proposalApproval';

export interface RuntimeActivation {
  id: string;
  model_id: string;
  model_version_id: string;
  activated_at: string;
  activated_by: string;
  correlation_id: string | null;
  model_version: ApprovedModelVersion;
}
