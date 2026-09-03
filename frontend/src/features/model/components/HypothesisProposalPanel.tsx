import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';

import { ErrorNotice, LoadingNotice } from '../../market/components/ApiFeedback';
import { ProposalValidationPanel } from './ProposalValidationPanel';
import { hypothesisProposalClient } from '../services/hypothesisProposalClient';
import {
  CANDIDATE_MODEL_KEY,
  CANDIDATE_SCHEMA_V1,
  candidatePolicyImpact,
  candidatePolicyLabel,
  proposedCandidateDefinition,
  readCandidateConfiguration,
} from '../types/candidateConfiguration';
import type { CandidateMarketContextPolicy } from '../types/candidateConfiguration';
import type {
  GovernedModelSummary,
  GovernedModelVersion,
  ModelChangeProposalSummary,
} from '../types/hypothesisProposal';

interface HypothesisProposalPanelProps {
  hypothesisId: string;
}

export function HypothesisProposalPanel({ hypothesisId }: HypothesisProposalPanelProps) {
  const [proposals, setProposals] = useState<ModelChangeProposalSummary[]>([]);
  const [models, setModels] = useState<GovernedModelSummary[]>([]);
  const [versions, setVersions] = useState<GovernedModelVersion[]>([]);
  const [modelId, setModelId] = useState('');
  const [baseVersionId, setBaseVersionId] = useState('');
  const [definition, setDefinition] = useState('');
  const [candidatePolicy, setCandidatePolicy] = useState<CandidateMarketContextPolicy | ''>('');
  const [rationale, setRationale] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    Promise.all([
      hypothesisProposalClient.listForHypothesis(hypothesisId, controller.signal),
      hypothesisProposalClient.listModels(controller.signal),
    ])
      .then(([nextProposals, nextModels]) => {
        setProposals(nextProposals);
        setModels(nextModels);
      })
      .catch((nextError: unknown) => {
        if (!controller.signal.aborted) setError(nextError);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [hypothesisId]);

  const selectedModel = useMemo(
    () => models.find((model) => model.id === modelId),
    [models, modelId],
  );
  const isCandidateModel = selectedModel?.model_key === CANDIDATE_MODEL_KEY;

  useEffect(() => {
    if (!modelId || proposals.length > 0) {
      setVersions([]);
      setBaseVersionId('');
      return;
    }
    const controller = new AbortController();
    setLoadingVersions(true);
    setError(null);
    hypothesisProposalClient
      .listVersions(modelId, controller.signal)
      .then((nextVersions) => {
        const approved = nextVersions.filter((version) => version.status === 'APPROVED');
        setVersions(approved);
        const latest = approved.at(-1);
        setBaseVersionId(latest?.id ?? '');
        setDefinition(latest ? JSON.stringify(latest.definition, null, 2) : '');
        const config = latest ? readCandidateConfiguration(latest.definition) : null;
        setCandidatePolicy(config?.policy ?? '');
      })
      .catch((nextError: unknown) => {
        if (!controller.signal.aborted) setError(nextError);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingVersions(false);
      });
    return () => controller.abort();
  }, [modelId, proposals.length]);

  const selectedVersion = useMemo(
    () => versions.find((version) => version.id === baseVersionId),
    [versions, baseVersionId],
  );
  const candidateCurrent =
    isCandidateModel && selectedVersion
      ? readCandidateConfiguration(selectedVersion.definition)
      : null;
  const candidateImpact =
    candidateCurrent && candidatePolicy
      ? candidatePolicyImpact(candidateCurrent.policy, candidatePolicy)
      : null;
  const candidateNoOp = candidateCurrent !== null && candidatePolicy === candidateCurrent.policy;
  const candidateUnsupported =
    isCandidateModel && selectedVersion !== undefined && candidateCurrent === null;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isCandidateModel && (!candidateCurrent || !candidatePolicy || candidateNoOp)) return;
    setSaving(true);
    setError(null);
    try {
      const proposedDefinition = isCandidateModel
        ? proposedCandidateDefinition(candidatePolicy as CandidateMarketContextPolicy)
        : (JSON.parse(definition) as Record<string, unknown>);
      const created = await hypothesisProposalClient.create({
        model_id: modelId,
        base_model_version_id: baseVersionId,
        hypothesis_id: hypothesisId,
        proposed_definition: proposedDefinition,
        rationale,
      });
      setProposals([created]);
    } catch (nextError: unknown) {
      setError(nextError);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingNotice label="FT-013-Proposals werden geladen …" />;

  if (proposals.length > 0) {
    return (
      <div className="mt-4 rounded-lg border border-slate-800 p-4">
        <p className="text-sm font-medium text-emerald-300">ModelChangeProposal vorhanden</p>
        {proposals.map((proposal) => (
          <div key={proposal.id} className="mt-3 text-sm">
            <p>
              Status: <span className="font-medium">{proposal.status}</span>
            </p>
            <p className="mt-1 break-all text-slate-500">Proposal {proposal.id}</p>
            <p className="mt-2 whitespace-pre-wrap text-slate-300">{proposal.rationale}</p>
            <ProposalValidationPanel proposalId={proposal.id} proposalStatus={proposal.status} />
          </div>
        ))}
      </div>
    );
  }

  const submitDisabled =
    saving ||
    !modelId ||
    !baseVersionId ||
    (isCandidateModel && (!candidateCurrent || !candidatePolicy || candidateNoOp));

  return (
    <div className="mt-4 rounded-lg border border-slate-800 p-4">
      <h4 className="font-medium">ModelChangeProposal erstellen</h4>
      <p className="mt-1 text-sm text-slate-400">
        Erstellt nur einen DRAFT. Validation, Approval und Aktivierung erfolgen nicht automatisch.
      </p>
      {error !== null && (
        <div className="mt-3">
          <ErrorNotice error={error} />
        </div>
      )}

      <form className="mt-4 space-y-4" onSubmit={(event) => void submit(event)}>
        <label className="block text-sm">
          <span className="text-slate-400">Governed Model</span>
          <select
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
            value={modelId}
            onChange={(event) => {
              setModelId(event.target.value);
              setCandidatePolicy('');
            }}
            required
          >
            <option value="">Model auswählen</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.model_key} · {model.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <span className="text-slate-400">APPROVED Base-Version</span>
          <select
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
            value={baseVersionId}
            onChange={(event) => {
              const nextId = event.target.value;
              setBaseVersionId(nextId);
              const nextVersion = versions.find((version) => version.id === nextId);
              if (nextVersion) {
                setDefinition(JSON.stringify(nextVersion.definition, null, 2));
                setCandidatePolicy(
                  readCandidateConfiguration(nextVersion.definition)?.policy ?? '',
                );
              }
            }}
            required
            disabled={!modelId || loadingVersions}
          >
            <option value="">
              {loadingVersions ? 'Versionen werden geladen …' : 'Version auswählen'}
            </option>
            {versions.map((version) => (
              <option key={version.id} value={version.id}>
                Version {version.version}
              </option>
            ))}
          </select>
        </label>

        {modelId && !loadingVersions && versions.length === 0 && (
          <p className="text-sm text-amber-300">Dieses Model hat keine APPROVED Version.</p>
        )}

        {isCandidateModel ? (
          <div className="space-y-4" aria-live="polite">
            {candidateUnsupported ? (
              <div
                className="rounded-md border border-amber-700 p-3 text-sm text-amber-200"
                role="alert"
              >
                Diese Candidate Definition wird vom spezialisierten Editor nicht vollständig
                verstanden und kann hier nicht verlustfrei geändert werden.
              </div>
            ) : candidateCurrent && selectedVersion ? (
              <>
                <div className="rounded-md border border-slate-700 p-3 text-sm">
                  <p className="font-medium">Current / Base</p>
                  <p className="mt-1">
                    Model-Version {selectedVersion.version} · {candidateCurrent.schema}
                  </p>
                  <p className="mt-1">
                    Candidate market context policy: {candidatePolicyLabel(candidateCurrent.policy)}
                  </p>
                  {candidateCurrent.schema === CANDIDATE_SCHEMA_V1 && (
                    <p className="mt-2 text-slate-400">
                      Legacy 1.0 bleibt unverändert. Eine vorgeschlagene Policy-Änderung erzeugt
                      ausdrücklich eine neue 2.0-Definition.
                    </p>
                  )}
                </div>
                <fieldset className="rounded-md border border-slate-700 p-3">
                  <legend className="px-1 text-sm font-medium">
                    Proposed Candidate Policy · Schema 2.0
                  </legend>
                  <label className="mt-2 flex gap-2 text-sm">
                    <input
                      type="radio"
                      name="candidate-policy"
                      value="FAVORABLE_AND_CAUTIOUS"
                      checked={candidatePolicy === 'FAVORABLE_AND_CAUTIOUS'}
                      onChange={() => setCandidatePolicy('FAVORABLE_AND_CAUTIOUS')}
                    />
                    FAVORABLE + CAUTIOUS
                  </label>
                  <label className="mt-2 flex gap-2 text-sm">
                    <input
                      type="radio"
                      name="candidate-policy"
                      value="FAVORABLE_ONLY"
                      checked={candidatePolicy === 'FAVORABLE_ONLY'}
                      onChange={() => setCandidatePolicy('FAVORABLE_ONLY')}
                    />
                    FAVORABLE only
                  </label>
                </fieldset>
                <div className="rounded-md border border-slate-700 p-3 text-sm">
                  <p className="font-medium">Proposed</p>
                  <p className="mt-1">
                    Candidate market context policy:{' '}
                    {candidatePolicy ? candidatePolicyLabel(candidatePolicy) : 'Keine Auswahl'}
                  </p>
                  {candidateNoOp && <p className="mt-2 text-amber-300">Keine Änderung.</p>}
                  {candidateImpact && (
                    <>
                      <p className="mt-2">{candidateImpact}</p>
                      <p className="mt-2 text-xs text-slate-500">
                        Direkte definitorische Auswirkung; keine retrospective Validation,
                        Performance-Prognose oder Empfehlung.
                      </p>
                    </>
                  )}
                </div>
              </>
            ) : null}
          </div>
        ) : (
          <label className="block text-sm">
            <span className="text-slate-400">Proposed Definition (JSON)</span>
            <textarea
              className="mt-1 min-h-48 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs"
              value={definition}
              onChange={(event) => setDefinition(event.target.value)}
              required
            />
          </label>
        )}

        {selectedVersion && (
          <p className="text-xs text-slate-500">
            Ausgangspunkt: Model-Version {selectedVersion.version} · {selectedVersion.id}
          </p>
        )}
        <label className="block text-sm">
          <span className="text-slate-400">Rationale</span>
          <textarea
            className="mt-1 min-h-24 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
            value={rationale}
            onChange={(event) => setRationale(event.target.value)}
            required
          />
        </label>
        <button
          type="submit"
          disabled={submitDisabled}
          className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          {saving ? 'Proposal wird angelegt …' : 'ModelChangeProposal als DRAFT anlegen'}
        </button>
      </form>
    </div>
  );
}
