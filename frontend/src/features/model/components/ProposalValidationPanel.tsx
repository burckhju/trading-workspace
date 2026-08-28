import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';

import { ErrorNotice, LoadingNotice } from '../../market/components/ApiFeedback';
import { ProposalApprovalPanel } from './ProposalApprovalPanel';
import { proposalValidationClient } from '../services/proposalValidationClient';
import type { ModelValidationSummary, ValidationConclusion } from '../types/proposalValidation';

interface ProposalValidationPanelProps {
  proposalId: string;
  proposalStatus: 'DRAFT' | 'VALIDATED' | 'APPROVED';
}

function parseEvidenceIds(value: string): string[] {
  return value
    .split(/[\s,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function ProposalValidationPanel({
  proposalId,
  proposalStatus,
}: ProposalValidationPanelProps) {
  const [validations, setValidations] = useState<ModelValidationSummary[]>([]);
  const [evidenceIds, setEvidenceIds] = useState('');
  const [cutoff, setCutoff] = useState('');
  const [conclusion, setConclusion] = useState<ValidationConclusion>('INCONCLUSIVE');
  const [metrics, setMetrics] = useState('{}');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    proposalValidationClient
      .listForProposal(proposalId, controller.signal)
      .then(setValidations)
      .catch((nextError: unknown) => {
        if (!controller.signal.aborted) setError(nextError);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [proposalId]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const parsedMetrics = JSON.parse(metrics) as Record<string, unknown>;
      const created = await proposalValidationClient.create(proposalId, {
        evidence_ids: parseEvidenceIds(evidenceIds),
        evidence_cutoff_at: new Date(cutoff).toISOString(),
        conclusion,
        metrics: parsedMetrics,
        notes: notes.trim() || null,
      });
      setValidations((current) => [...current, created]);
    } catch (nextError: unknown) {
      setError(nextError);
    } finally {
      setSaving(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    void submit(event);
  }

  if (loading) return <LoadingNotice label="Validierungen werden geladen …" />;

  if (validations.length > 0) {
    return (
      <div className="mt-4 rounded-lg border border-slate-800 p-4">
        <p className="text-sm font-medium text-emerald-300">Retrospektiv validiert</p>
        {validations.map((validation) => (
          <div key={validation.id} className="mt-3 text-sm">
            <p>
              Ergebnis: <span className="font-medium">{validation.conclusion}</span>
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Cutoff: {new Date(validation.evidence_cutoff_at).toLocaleString()}
            </p>
            {validation.notes && <p className="mt-2 whitespace-pre-wrap">{validation.notes}</p>}
          </div>
        ))}
        <ProposalApprovalPanel
          proposalId={proposalId}
          proposalStatus={proposalStatus === 'APPROVED' ? 'APPROVED' : 'VALIDATED'}
        />
      </div>
    );
  }

  if (proposalStatus !== 'DRAFT') {
    return <ProposalApprovalPanel proposalId={proposalId} proposalStatus={proposalStatus} />;
  }

  return (
    <div className="mt-4 rounded-lg border border-slate-800 p-4">
      <h4 className="font-medium">Retrospektive Validation erfassen</h4>
      <p className="mt-1 text-sm text-slate-400">
        Evidence muss vor oder am Cutoff entstanden sein. Dieser Schritt erzeugt kein Approval.
      </p>
      {error !== null && (
        <div className="mt-3">
          <ErrorNotice error={error} />
        </div>
      )}
      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm">
          <span className="text-slate-400">LearningEvidence IDs</span>
          <textarea
            className="mt-1 min-h-20 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs"
            value={evidenceIds}
            onChange={(event) => setEvidenceIds(event.target.value)}
            placeholder="UUIDs durch Komma oder Zeilenumbruch trennen"
            required
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-400">Evidence Cutoff</span>
          <input
            type="datetime-local"
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
            value={cutoff}
            onChange={(event) => setCutoff(event.target.value)}
            required
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-400">Conclusion</span>
          <select
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
            value={conclusion}
            onChange={(event) => setConclusion(event.target.value as ValidationConclusion)}
          >
            <option value="SUPPORTS">SUPPORTS</option>
            <option value="INCONCLUSIVE">INCONCLUSIVE</option>
            <option value="CONTRADICTS">CONTRADICTS</option>
          </select>
        </label>
        <label className="block text-sm">
          <span className="text-slate-400">Metrics (JSON)</span>
          <textarea
            className="mt-1 min-h-28 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs"
            value={metrics}
            onChange={(event) => setMetrics(event.target.value)}
            required
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-400">Notes</span>
          <textarea
            className="mt-1 min-h-20 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
          />
        </label>
        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          {saving ? 'Validation wird gespeichert …' : 'Proposal retrospektiv validieren'}
        </button>
      </form>
    </div>
  );
}
