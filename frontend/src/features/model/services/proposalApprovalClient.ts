import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { ProposalApprovalResult } from '../types/proposalApproval';

const baseUrl = `${environment.apiBaseUrl}/api/v1/model-governance`;

export const proposalApprovalClient = {
  getForProposal: (proposalId: string, signal?: AbortSignal): Promise<ProposalApprovalResult | null> =>
    requestJson<ProposalApprovalResult | null>(`${baseUrl}/proposals/${proposalId}/approval`, {
      signal,
    }),

  approve: (proposalId: string, correlationId?: string): Promise<ProposalApprovalResult> =>
    requestJson<ProposalApprovalResult>(`${baseUrl}/proposals/${proposalId}/approve`, {
      method: 'POST',
      correlationId,
    }),
};
