import { useEffect, useState } from 'react';

import { ErrorNotice, LoadingNotice } from '../../market/components/ApiFeedback';
import { RuntimeActivationPanel } from './RuntimeActivationPanel';
import { proposalApprovalClient } from '../services/proposalApprovalClient';
import type { ProposalApprovalResult } from '../types/proposalApproval';

interface ProposalApprovalPanelProps {
  proposalId: string;
  proposalStatus: 'DRAFT' | 'VALIDATED' | 'APPROVED';
}

export function ProposalApprovalPanel({ proposalId, proposalStatus }: ProposalApprovalPanelProps) {
  const [approval, setApproval] = useState<ProposalApprovalResult | null>(null);
  const [correlationId, setCorrelationId] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    proposalApprovalClient
      .getForProposal(proposalId, controller.signal)
      .then(setApproval)
      .catch((nextError: unknown) => {
        if (!controller.signal.aborted) setError(nextError);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [proposalId]);

  async function approve() {
    setSaving(true);
    setError(null);
    try {
      const created = await proposalApprovalClient.approve(
        proposalId,
        correlationId.trim() || undefined,
      );
      setApproval(created);
    } catch (nextError: unknown) {
      setError(nextError);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingNotice label="Approval-Status wird geladen …" />;

  if (approval !== null) {
    return (
      <div className="mt-4 rounded-lg border border-slate-800 p-4">
        <p className="text-sm font-medium text-emerald-300">Proposal approved</p>
        <p className="mt-2 text-sm">
          Neue immutable ModelVersion:{' '}
          <span className="font-medium">Version {approval.model_version.version}</span>
        </p>
        <p className="mt-1 break-all text-xs text-slate-500">{approval.model_version.id}</p>
        {approval.approval.correlation_id && (
          <p className="mt-2 text-xs text-slate-500">
            Correlation: {approval.approval.correlation_id}
          </p>
        )}
        <RuntimeActivationPanel
          modelId={approval.model_version.model_id}
          approvedVersionId={approval.model_version.id}
          approvedVersionNumber={approval.model_version.version}
        />
      </div>
    );
  }

  if (proposalStatus !== 'VALIDATED') return null;

  return (
    <div className="mt-4 rounded-lg border border-slate-800 p-4">
      <h4 className="font-medium">Proposal freigeben</h4>
      <p className="mt-1 text-sm text-slate-400">
        Approval erzeugt eine neue immutable APPROVED ModelVersion und schließt die Hypothese. Die
        Runtime-Aktivierung bleibt ein separater, expliziter Schritt.
      </p>
      {error !== null && (
        <div className="mt-3">
          <ErrorNotice error={error} />
        </div>
      )}
      <label className="mt-4 block text-sm">
        <span className="text-slate-400">Correlation ID (optional)</span>
        <input
          className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
          value={correlationId}
          onChange={(event) => setCorrelationId(event.target.value)}
          maxLength={100}
        />
      </label>
      <button
        type="button"
        disabled={saving}
        onClick={() => void approve()}
        className="mt-4 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
      >
        {saving ? 'Approval wird durchgeführt …' : 'VALIDATED Proposal approven'}
      </button>
    </div>
  );
}
