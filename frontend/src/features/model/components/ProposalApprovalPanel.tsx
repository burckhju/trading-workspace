import { useEffect, useLayoutEffect, useRef, useState } from 'react';

import { ErrorNotice, LoadingNotice } from '../../market/components/ApiFeedback';
import { RuntimeActivationPanel } from './RuntimeActivationPanel';
import { proposalApprovalClient } from '../services/proposalApprovalClient';
import type { ProposalApprovalResult } from '../types/proposalApproval';

interface ProposalApprovalPanelProps {
  proposalId: string;
  proposalStatus: 'DRAFT' | 'VALIDATED' | 'APPROVED';
  modelKey?: string;
  onApproved?: () => void;
}

export function ProposalApprovalPanel(props: ProposalApprovalPanelProps) {
  return <ProposalApprovalForm key={props.proposalId} {...props} />;
}

function ProposalApprovalForm({
  proposalId,
  proposalStatus,
  modelKey,
  onApproved,
}: ProposalApprovalPanelProps) {
  const [approval, setApproval] = useState<ProposalApprovalResult | null>(null);
  const [correlationId, setCorrelationId] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [ready, setReady] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const instance = useRef<object | null>(null);
  const operation = useRef<object | null>(null);

  useLayoutEffect(() => {
    instance.current = {};
    return () => {
      instance.current = null;
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setReady(false);
    setError(null);
    proposalApprovalClient
      .getForProposal(proposalId, controller.signal)
      .then((value) => {
        if (controller.signal.aborted) return;
        if (
          value !== null &&
          (value.approval.proposal_id !== proposalId ||
            value.approval.model_version_id !== value.model_version.id)
        )
          throw new Error('Der Freigabelesestand passt nicht zum Proposal.');
        setApproval(value);
        setReady(true);
      })
      .catch((nextError: unknown) => {
        if (!controller.signal.aborted) setError(nextError);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [proposalId, refresh]);

  async function approve() {
    const visit = instance.current;
    if (
      !ready ||
      loading ||
      proposalStatus !== 'VALIDATED' ||
      approval !== null ||
      visit === null ||
      operation.current !== null
    )
      return;
    const pending = {};
    operation.current = pending;
    const ownsCommand = () => instance.current === visit && operation.current === pending;
    setSaving(true);
    setError(null);
    try {
      const created = await proposalApprovalClient.approve(
        proposalId,
        correlationId.trim() || undefined,
      );
      if (!ownsCommand()) return;
      if (
        created.approval.proposal_id !== proposalId ||
        created.approval.model_version_id !== created.model_version.id
      )
        throw new Error('Die Freigabeantwort passt nicht zum Proposal.');
      setApproval(created);
      onApproved?.();
    } catch (nextError: unknown) {
      if (ownsCommand()) {
        setError(nextError);
        setReady(false);
      }
    } finally {
      if (ownsCommand()) {
        operation.current = null;
        setSaving(false);
      }
    }
  }

  if (loading) return <LoadingNotice label="Approval-Status wird geladen …" />;
  if (!ready)
    return (
      <div className="mt-4 space-y-3">
        <ErrorNotice error={error} />
        <p className="text-sm">
          Freigabestand nicht verifiziert. Vor einer weiteren Entscheidung bewusst neu laden. Keine
          automatische Wiederholung.
        </p>
        <button
          type="button"
          disabled={saving}
          onClick={() => {
            if (operation.current === null) setRefresh((n) => n + 1);
          }}
        >
          Freigabestand neu laden
        </button>
      </div>
    );

  if (approval !== null) {
    return (
      <div className="mt-4 rounded-lg border border-slate-800 p-4">
        <p className="text-sm font-medium text-emerald-300">Proposal approved</p>
        <p className="mt-2 text-sm">
          Neue immutable ModelVersion:{' '}
          <span className="font-medium">Version {approval.model_version.version}</span>
        </p>
        <p className="mt-1 break-all text-xs text-slate-500">{approval.model_version.id}</p>
        <p className="mt-1 break-all text-xs">
          Approval {approval.approval.id} · {approval.approval.approved_at}
        </p>
        <p className="mt-1 break-all text-xs">
          Genehmigte Vorgängerversion {approval.model_version.previous_version_id ?? 'keine'}
        </p>
        <p className="mt-2 text-sm">Freigabe allein ändert die aktive Runtime-Version nicht.</p>
        {approval.approval.correlation_id && (
          <p className="mt-2 text-xs text-slate-500">
            Correlation: {approval.approval.correlation_id}
          </p>
        )}
        <RuntimeActivationPanel
          modelId={approval.model_version.model_id}
          approvedVersionId={approval.model_version.id}
          approvedVersionNumber={approval.model_version.version}
          modelKey={modelKey}
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
          <button
            type="button"
            disabled={saving}
            onClick={() => {
              if (operation.current === null) setRefresh((n) => n + 1);
            }}
          >
            Freigabestand neu laden
          </button>
          <p className="mt-2 text-sm">
            Befehlsabschluss vor einer weiteren Übermittlung bewusst prüfen. Keine automatische
            Wiederholung.
          </p>
        </div>
      )}
      <label className="mt-4 block text-sm">
        <span className="text-slate-400">Correlation ID (optional)</span>
        <input
          className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
          value={correlationId}
          disabled={saving || !ready}
          onChange={(event) => {
            if (operation.current === null) setCorrelationId(event.target.value);
          }}
          maxLength={100}
        />
      </label>
      <button
        type="button"
        disabled={saving || !ready}
        onClick={() => void approve()}
        className="mt-4 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
      >
        {saving ? 'Approval wird durchgeführt …' : 'VALIDATED Proposal approven'}
      </button>
    </div>
  );
}
