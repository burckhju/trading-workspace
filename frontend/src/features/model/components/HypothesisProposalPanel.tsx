import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
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
  onHypothesisChanged?: () => void;
}

interface ModelSelection {
  modelId: string;
}

interface ProposalBase {
  selection: ModelSelection;
  version: GovernedModelVersion;
}

function isDefinition(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function HypothesisProposalPanel(props: HypothesisProposalPanelProps) {
  // Returning to the same ID is a new visit, not the previous hypothesis instance.
  return <HypothesisProposalForm key={props.hypothesisId} {...props} />;
}

function HypothesisProposalForm({
  hypothesisId,
  onHypothesisChanged,
}: HypothesisProposalPanelProps) {
  const [proposals, setProposals] = useState<ModelChangeProposalSummary[]>([]);
  const [models, setModels] = useState<GovernedModelSummary[]>([]);
  const [versions, setVersions] = useState<GovernedModelVersion[]>([]);
  const [selection, setSelection] = useState<ModelSelection>({ modelId: '' });
  const selectionRef = useRef(selection);
  const [loadedSelection, setLoadedSelection] = useState<ModelSelection | null>(null);
  const [base, setBase] = useState<ProposalBase | null>(null);
  const baseRef = useRef(base);
  const [definition, setDefinition] = useState('');
  const [candidatePolicy, setCandidatePolicy] = useState<CandidateMarketContextPolicy | ''>('');
  const [rationale, setRationale] = useState('');
  const [loading, setLoading] = useState(true);
  const [ready, setReady] = useState(false);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const instanceRef = useRef<object | null>(null);
  const saveRef = useRef<object | null>(null);
  const modelId = selection.modelId;
  const selectedVersion = base?.version;
  const baseVersionId = selectedVersion?.id ?? '';

  useLayoutEffect(() => {
    instanceRef.current = {};
    return () => {
      // Invalidate before passive cleanup; an already completed transport can still settle.
      instanceRef.current = null;
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const instance = instanceRef.current;
    const isCurrent = () =>
      instance !== null && instanceRef.current === instance && !controller.signal.aborted;
    setLoading(true);
    setReady(false);
    setError(null);
    if (!hypothesisId.trim()) {
      setError(new Error('Für einen Proposal fehlt die aktuelle Hypothese.'));
      setLoading(false);
      return () => controller.abort();
    }
    Promise.all([
      hypothesisProposalClient.listForHypothesis(hypothesisId, controller.signal),
      hypothesisProposalClient.listModels(controller.signal),
    ])
      .then(([nextProposals, nextModels]) => {
        if (!isCurrent()) return;
        if (nextProposals.some((proposal) => proposal.hypothesis_id !== hypothesisId)) {
          throw new Error('Die geladenen Proposals gehören nicht zur aktuellen Hypothese.');
        }
        setProposals(nextProposals);
        setModels(nextModels);
        setReady(true);
      })
      .catch((nextError: unknown) => {
        if (isCurrent()) setError(nextError);
      })
      .finally(() => {
        if (isCurrent()) setLoading(false);
      });
    return () => controller.abort();
  }, [hypothesisId]);

  const selectedModel = useMemo(
    () => models.find((model) => model.id === modelId),
    [models, modelId],
  );
  const isCandidateModel = selectedModel?.model_key === CANDIDATE_MODEL_KEY;

  useEffect(() => {
    if (!ready || !modelId || proposals.length > 0) return;
    const controller = new AbortController();
    const instance = instanceRef.current;
    const isCurrent = () =>
      instance !== null &&
      instanceRef.current === instance &&
      selectionRef.current === selection &&
      !controller.signal.aborted;
    setLoadingVersions(true);
    setError(null);
    hypothesisProposalClient
      .listVersions(modelId, controller.signal)
      .then((nextVersions) => {
        if (!isCurrent()) return;
        if (
          nextVersions.some((version) => version.model_id !== modelId) ||
          new Set(nextVersions.map((version) => version.id)).size !== nextVersions.length
        ) {
          throw new Error(
            'Die geladenen Basisversionen passen nicht eindeutig zum gewählten Model.',
          );
        }
        const approved = nextVersions.filter((version) => version.status === 'APPROVED');
        const latest = approved.at(-1);
        const nextBase = latest ? { selection, version: latest } : null;
        const config =
          latest && isDefinition(latest.definition)
            ? readCandidateConfiguration(latest.definition)
            : null;
        setVersions(approved);
        setLoadedSelection(selection);
        baseRef.current = nextBase;
        setBase(nextBase);
        setDefinition(latest ? JSON.stringify(latest.definition, null, 2) : '');
        setCandidatePolicy(config?.policy ?? '');
      })
      .catch((nextError: unknown) => {
        if (isCurrent()) setError(nextError);
      })
      .finally(() => {
        if (isCurrent()) setLoadingVersions(false);
      });
    return () => controller.abort();
  }, [modelId, selection, ready, proposals.length]);

  const candidateCurrent =
    isCandidateModel && selectedVersion && isDefinition(selectedVersion.definition)
      ? readCandidateConfiguration(selectedVersion.definition)
      : null;
  const candidateImpact =
    candidateCurrent && candidatePolicy
      ? candidatePolicyImpact(candidateCurrent.policy, candidatePolicy)
      : null;
  const candidateNoOp = candidateCurrent !== null && candidatePolicy === candidateCurrent.policy;
  const candidateUnsupported =
    isCandidateModel && selectedVersion !== undefined && candidateCurrent === null;
  const versionsReady = ready && loadedSelection === selection && !loadingVersions;
  const baseReady =
    versionsReady &&
    selectedModel !== undefined &&
    base?.selection === selection &&
    selectedVersion !== undefined &&
    versions.includes(selectedVersion) &&
    selectedVersion.model_id === modelId &&
    selectedVersion.status === 'APPROVED' &&
    isDefinition(selectedVersion.definition);
  const submitDisabled =
    saving ||
    !hypothesisId.trim() ||
    !modelId ||
    !baseVersionId ||
    !baseReady ||
    proposals.length > 0 ||
    !rationale.trim() ||
    (isCandidateModel
      ? !candidateCurrent || !candidatePolicy || candidateNoOp
      : !definition.trim());

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const instance = instanceRef.current;
    if (
      submitDisabled ||
      instance === null ||
      selectionRef.current !== selection ||
      baseRef.current !== base ||
      saveRef.current !== null
    )
      return;
    const operation = {};
    saveRef.current = operation;
    const ownsOperation = () =>
      instanceRef.current === instance &&
      selectionRef.current === selection &&
      baseRef.current === base &&
      saveRef.current === operation;
    setSaving(true);
    setError(null);
    try {
      const proposedDefinition = isCandidateModel
        ? proposedCandidateDefinition(candidatePolicy as CandidateMarketContextPolicy)
        : (JSON.parse(definition) as unknown);
      if (!isDefinition(proposedDefinition)) {
        throw new Error('Die vorgeschlagene Definition muss ein JSON-Objekt sein.');
      }
      const snapshot = {
        model_id: modelId,
        base_model_version_id: baseVersionId,
        hypothesis_id: hypothesisId,
        proposed_definition: proposedDefinition,
        rationale,
      };
      const created = await hypothesisProposalClient.create(snapshot);
      if (!ownsOperation()) return;
      if (
        created.hypothesis_id !== snapshot.hypothesis_id ||
        created.model_id !== snapshot.model_id ||
        created.base_model_version_id !== snapshot.base_model_version_id ||
        created.status !== 'DRAFT'
      ) {
        throw new Error('Die Speicherantwort passt nicht zum abgesendeten DRAFT-Proposal.');
      }
      setProposals([created]);
      onHypothesisChanged?.();
    } catch (nextError: unknown) {
      if (ownsOperation()) setError(nextError);
    } finally {
      if (ownsOperation()) {
        saveRef.current = null;
        setSaving(false);
      }
    }
  }

  function changeModel(nextId: string) {
    if (saveRef.current !== null || !ready || nextId === selectionRef.current.modelId) return;
    // Invalidate synchronously, including M1 -> M2 -> M1 before the next effect runs.
    const nextSelection = { modelId: nextId };
    selectionRef.current = nextSelection;
    baseRef.current = null;
    setSelection(nextSelection);
    setLoadedSelection(null);
    setVersions([]);
    setBase(null);
    setDefinition('');
    setCandidatePolicy('');
    setRationale('');
    setLoadingVersions(Boolean(nextId));
    setError(null);
  }

  function changeBase(nextId: string) {
    if (
      saveRef.current !== null ||
      !versionsReady ||
      selectionRef.current !== selection ||
      nextId === (baseRef.current?.version.id ?? '')
    )
      return;
    const version = versions.find((item) => item.id === nextId);
    const nextBase = version ? { selection, version } : null;
    baseRef.current = nextBase;
    setBase(nextBase);
    setDefinition(version ? JSON.stringify(version.definition, null, 2) : '');
    setCandidatePolicy(
      version && isDefinition(version.definition)
        ? (readCandidateConfiguration(version.definition)?.policy ?? '')
        : '',
    );
    setRationale('');
    setError(null);
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
            <p className="mt-1 break-all text-slate-400">Hypothese {proposal.hypothesis_id}</p>
            <p className="mt-1 break-all text-slate-400">Modell {proposal.model_id}</p>
            <p className="mt-1 break-all text-slate-400">
              Genehmigte Proposal-Basis {proposal.base_model_version_id}
            </p>
            <details className="mt-2">
              <summary>Gespeicherte vorgeschlagene Definition</summary>
              <pre className="mt-2 whitespace-pre-wrap break-all text-xs">
                {JSON.stringify(proposal.proposed_definition, null, 2)}
              </pre>
            </details>
            <p className="mt-2 whitespace-pre-wrap text-slate-300">{proposal.rationale}</p>
            <ProposalValidationPanel
              proposalId={proposal.id}
              proposalStatus={proposal.status}
              modelKey={models.find((model) => model.id === proposal.model_id)?.model_key}
              onStatusChange={(status) => {
                if (instanceRef.current === null) return;
                setProposals((current) =>
                  current.map((item) => (item.id === proposal.id ? { ...item, status } : item)),
                );
                if (status === 'APPROVED') onHypothesisChanged?.();
              }}
            />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="mt-4 rounded-lg border border-slate-800 p-4">
      <h4 className="font-medium">ModelChangeProposal erstellen</h4>
      <p className="mt-1 text-sm text-slate-400">
        Erstellt nur einen DRAFT. Validation, Approval und Aktivierung erfolgen nicht automatisch.
      </p>
      <p className="mt-1 text-sm text-slate-400">
        Ein Wechsel von Model oder Basisversion setzt Definition, Policy und Rationale zurück.
        Während des Speicherns sind die Eingaben gesperrt.
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
            onChange={(event) => changeModel(event.target.value)}
            required
            disabled={!ready || saving}
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
            onChange={(event) => changeBase(event.target.value)}
            required
            disabled={!versionsReady || saving}
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

        {ready && models.length === 0 && (
          <p className="text-sm text-amber-300">Keine Governed Models verfügbar.</p>
        )}
        {modelId && versionsReady && versions.length === 0 && (
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
                  <p className="font-medium">Current / Base · genehmigte Proposal-Basis</p>
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
                <fieldset className="rounded-md border border-slate-700 p-3" disabled={saving}>
                  <legend className="px-1 text-sm font-medium">
                    Proposed Candidate Policy · Schema 2.0
                  </legend>
                  <label className="mt-2 flex gap-2 text-sm">
                    <input
                      type="radio"
                      name="candidate-policy"
                      value="FAVORABLE_AND_CAUTIOUS"
                      checked={candidatePolicy === 'FAVORABLE_AND_CAUTIOUS'}
                      onChange={() => {
                        if (saveRef.current === null) setCandidatePolicy('FAVORABLE_AND_CAUTIOUS');
                      }}
                    />
                    FAVORABLE + CAUTIOUS
                  </label>
                  <label className="mt-2 flex gap-2 text-sm">
                    <input
                      type="radio"
                      name="candidate-policy"
                      value="FAVORABLE_ONLY"
                      checked={candidatePolicy === 'FAVORABLE_ONLY'}
                      onChange={() => {
                        if (saveRef.current === null) setCandidatePolicy('FAVORABLE_ONLY');
                      }}
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
              onChange={(event) => {
                if (saveRef.current === null) setDefinition(event.target.value);
              }}
              required
              disabled={!baseReady || saving}
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
            onChange={(event) => {
              if (saveRef.current === null) setRationale(event.target.value);
            }}
            required
            disabled={!baseReady || saving}
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
