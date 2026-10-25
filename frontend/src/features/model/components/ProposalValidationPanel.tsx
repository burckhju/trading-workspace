import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';

import { ErrorNotice, LoadingNotice } from '../../market/components/ApiFeedback';
import { ProposalApprovalPanel } from './ProposalApprovalPanel';
import { proposalValidationClient } from '../services/proposalValidationClient';
import type { ModelValidationSummary, ValidationConclusion } from '../types/proposalValidation';

interface ProposalValidationPanelProps {
  proposalId: string;
  proposalStatus: 'DRAFT' | 'VALIDATED' | 'APPROVED';
  modelKey?: string;
  onStatusChange?: (status: 'VALIDATED' | 'APPROVED') => void;
}

function parseEvidenceIds(value: string): string[] {
  return value
    .split(/[\s,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function ProposalValidationPanel(props: ProposalValidationPanelProps) {
  return <ProposalValidationForm key={props.proposalId} {...props} />;
}

function ProposalValidationForm({
  proposalId,
  proposalStatus,
  modelKey,
  onStatusChange,
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
    proposalValidationClient
      .listForProposal(proposalId, controller.signal)
      .then((items) => {
        if (controller.signal.aborted) return;
        if (items.some((item) => item.proposal_id !== proposalId))
          throw new Error('Der Validierungslesestand gehört nicht zu diesem Proposal.');
        setValidations(items);
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

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const visit = instance.current;
    if (
      !ready ||
      loading ||
      proposalStatus !== 'DRAFT' ||
      validations.length > 0 ||
      !parseEvidenceIds(evidenceIds).length ||
      !cutoff ||
      visit === null ||
      operation.current !== null
    )
      return;
    const pending = {};
    operation.current = pending;
    const ownsCommand = () => instance.current === visit && operation.current === pending;
    setSaving(true);
    setError(null);
    let sent = false;
    try {
      const parsedMetrics = JSON.parse(metrics) as unknown;
      if (
        parsedMetrics === null ||
        typeof parsedMetrics !== 'object' ||
        Array.isArray(parsedMetrics)
      )
        throw new Error('Metrics müssen ein JSON-Objekt sein.');
      const input = {
        evidence_ids: parseEvidenceIds(evidenceIds),
        evidence_cutoff_at: new Date(cutoff).toISOString(),
        conclusion,
        metrics: parsedMetrics as Record<string, unknown>,
        notes: notes.trim() || null,
      };
      sent = true;
      const created = await proposalValidationClient.create(proposalId, input);
      if (!ownsCommand()) return;
      if (created.proposal_id !== proposalId || !created.id)
        throw new Error('Die Validierungsantwort gehört nicht zum Proposal.');
      setValidations((current) => [...current, created]);
      onStatusChange?.('VALIDATED');
    } catch (nextError: unknown) {
      if (ownsCommand()) {
        setError(nextError);
        if (sent) setReady(false);
      }
    } finally {
      if (ownsCommand()) {
        operation.current = null;
        setSaving(false);
      }
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    void submit(event);
  }

  if (loading) return <LoadingNotice label="Validierungen werden geladen …" />;
  if (!ready)
    return (
      <div className="mt-4 space-y-3">
        <ErrorNotice error={error} />
        <p className="text-sm">
          Validierungsstand nicht verifiziert. Befund und Quellen vor einer weiteren Entscheidung
          bewusst neu laden. Keine automatische Wiederholung.
        </p>
        <button
          type="button"
          disabled={saving}
          onClick={() => {
            if (operation.current === null) setRefresh((n) => n + 1);
          }}
        >
          Validierungsstand neu laden
        </button>
      </div>
    );

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
            <p className="mt-1 break-all text-xs">
              Gespeicherter Cutoff: {validation.evidence_cutoff_at}
            </p>
            <p className="mt-1 break-all text-xs">
              Validation {validation.id} · Proposal {validation.proposal_id}
            </p>
            <p className="mt-1 break-all text-xs">
              Gewählte Evidence:{' '}
              {validation.evidence_ids?.join(', ') ?? 'Nicht im Lesestand enthalten'}
            </p>
            <pre className="mt-2 whitespace-pre-wrap break-all text-xs">
              Metrics: {JSON.stringify(validation.metrics)}
            </pre>
            {validation.notes && <p className="mt-2 whitespace-pre-wrap">{validation.notes}</p>}
          </div>
        ))}
        <ProposalApprovalPanel
          proposalId={proposalId}
          proposalStatus={proposalStatus === 'APPROVED' ? 'APPROVED' : 'VALIDATED'}
          modelKey={modelKey}
          onApproved={() => onStatusChange?.('APPROVED')}
        />
      </div>
    );
  }

  if (proposalStatus !== 'DRAFT') {
    return (
      <ProposalApprovalPanel
        proposalId={proposalId}
        proposalStatus={proposalStatus}
        modelKey={modelKey}
        onApproved={() => onStatusChange?.('APPROVED')}
      />
    );
  }

  return (
    <div className="mt-4 rounded-lg border border-slate-800 p-4">
      <h4 className="font-medium">Retrospektive Validation erfassen</h4>
      <p className="mt-1 text-sm text-slate-400">
        Evidence muss vor oder am Cutoff entstanden sein. Dieser Schritt erzeugt kein Approval. Der
        gespeicherte Befund führt keinen automatischen Backtest aus und bestätigt keine
        wirtschaftliche Überlegenheit.
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
            Validierungsstand neu laden
          </button>
          <p className="mt-2 text-sm">
            Befehlsabschluss vor einer weiteren Übermittlung bewusst prüfen. Keine automatische
            Wiederholung.
          </p>
        </div>
      )}
      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm">
          <span className="text-slate-400">LearningEvidence IDs</span>
          <textarea
            disabled={saving || !ready}
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
            disabled={saving || !ready}
            type="datetime-local"
            step="any"
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
            value={cutoff}
            onChange={(event) => setCutoff(event.target.value)}
            required
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-400">Conclusion</span>
          <select
            disabled={saving || !ready}
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
            disabled={saving || !ready}
            className="mt-1 min-h-28 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs"
            value={metrics}
            onChange={(event) => setMetrics(event.target.value)}
            required
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-400">Notes</span>
          <textarea
            disabled={saving || !ready}
            className="mt-1 min-h-20 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
          />
        </label>
        <button
          type="submit"
          disabled={saving || !ready}
          className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          {saving ? 'Validation wird gespeichert …' : 'Proposal retrospektiv validieren'}
        </button>
      </form>
    </div>
  );
}
