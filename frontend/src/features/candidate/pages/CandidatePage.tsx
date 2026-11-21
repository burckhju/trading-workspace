import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { candidateApiClient } from '../services/client';
import { marketApiClient } from '../../market';
import { analysisDetailUrl } from '../../analysis/services/analysisWorkflowContext';
import type {
  Candidate,
  CandidateCriterion,
  CandidateEvaluation,
  CandidateLiveWorkflow,
  CandidateLiveWorkflowStep,
} from '../types/api';

const groups = ['MARKET', 'SECTOR', 'UNDERLYING'] as const;
const runtimeStepCode = 'CANDIDATE_RUNTIME_MODEL';
const labels: Record<string, string> = {
  MARKET: 'Markt',
  SECTOR: 'Sektor',
  UNDERLYING: 'Basiswert',
  UNDER_REVIEW: 'In Prüfung',
  WATCHING: 'In Beobachtung',
  IDENTIFIED: 'Identifiziert',
  READY_FOR_PLANNING: 'Bereit zur Planung',
  REJECTED: 'Verworfen',
  QUALIFIED: 'Kriterien erfüllt',
  NOT_QUALIFIED: 'Kriterien nicht erfüllt',
  NOT_EVALUABLE: 'Nicht bewertbar',
  FULFILLED: 'Erfüllt',
  NOT_FULFILLED: 'Nicht erfüllt',
  SKIPPED: 'Nicht geprüft',
  REQUIRED: 'Erforderlich',
  WARNING: 'Hinweis',
  INFORMATIONAL: 'Information',
  GOOD: 'Gut',
  COMPLETE: 'Erfüllt',
  BLOCKED: 'Offen',
};
const readable = (value: string) => labels[value] ?? value;

function resultClasses(result: string) {
  if (result === 'FULFILLED' || result === 'QUALIFIED')
    return 'border-emerald-700 bg-emerald-950/40';
  if (result === 'NOT_FULFILLED' || result === 'NOT_QUALIFIED')
    return 'border-rose-700 bg-rose-950/40';
  if (result === 'NOT_EVALUABLE') return 'border-amber-700 bg-amber-950/40';
  return 'border-slate-700 bg-slate-900';
}

function workflowActionLabel(action: string | null) {
  switch (action) {
    case 'ACTIVATE_CANDIDATE_MODEL':
      return 'Kandidatenmodell aktivieren';
    case 'ACTIVATE_COMPATIBLE_CANDIDATE_MODEL':
      return 'Kompatible Kandidatenmodellversion aktivieren';
    default:
      return action;
  }
}

function RuntimeModelStep({ step }: { step: CandidateLiveWorkflowStep }) {
  const blockedSummary =
    step.action === 'ACTIVATE_CANDIDATE_MODEL'
      ? 'Keine aktive Kandidatenmodellversion vorhanden.'
      : step.action === 'ACTIVATE_COMPATIBLE_CANDIDATE_MODEL'
        ? 'Eine Kandidatenmodellversion ist aktiviert, aber aktuell nicht ausführbar.'
        : null;

  return (
    <li className="rounded-lg border border-slate-800 p-3 text-sm">
      <div className="flex flex-wrap justify-between gap-2">
        <span className="font-medium">Aktives Kandidatenmodell</span>
        <span className={step.status === 'COMPLETE' ? 'text-emerald-400' : 'text-amber-400'}>
          {step.status === 'COMPLETE' ? 'Aktiv und verwendbar' : 'Blockiert'}
        </span>
      </div>
      {blockedSummary && <p className="mt-2 font-medium text-amber-200">{blockedSummary}</p>}
      <p className="mt-1 text-slate-400">{step.detail}</p>
      {step.status === 'BLOCKED' && step.action && (
        <div className="mt-3 space-y-2 text-sm text-slate-300">
          <p>
            Nächste Aktion: {workflowActionLabel(step.action)}. Änderungen, Freigabe und Aktivierung
            bleiben getrennte Schritte.
          </p>
          <Link
            to="/model-improvements"
            className="inline-block rounded text-sky-300 underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-300"
          >
            Modellverbesserung und Aktivierung öffnen
          </Link>
        </div>
      )}
    </li>
  );
}

function Criterion({ item }: { item: CandidateCriterion }) {
  return (
    <li className={`rounded-lg border p-3 ${resultClasses(item.evaluation)}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium">{item.criterion_id}</span>
        <span className="text-xs text-slate-300">
          {readable(item.severity)} · {readable(item.evaluation)}
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-300">{item.explanation}</p>
      <p className="mt-1 text-xs text-slate-400">
        Ist: {item.actual_value ?? '—'} · Erwartet: {item.expected_value ?? 'informativ'}
      </p>
    </li>
  );
}

function EvaluationDetail({
  evaluation,
  candidateId,
}: {
  evaluation: CandidateEvaluation;
  candidateId: string;
}) {
  return (
    <section className="min-w-0 space-y-5" aria-label={`Evaluation ${evaluation.id}`}>
      <div className={`rounded-xl border p-5 ${resultClasses(evaluation.qualification)}`}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Systemqualifikation</p>
            <h2 className="mt-1 text-2xl font-semibold">{readable(evaluation.qualification)}</h2>
          </div>
          <div className="break-all text-sm text-slate-300">
            <div>{evaluation.model_id}</div>
            <div>Version {evaluation.model_version}</div>
            <div>Qualität {readable(evaluation.quality_status)}</div>
          </div>
        </div>
        <p className="mt-3 break-all text-xs">
          Evaluation {evaluation.id} · Bewertungsstand {evaluation.version} ·{' '}
          {evaluation.evaluated_at}
        </p>
        <p className="mt-2 text-xs">
          Die angezeigte Modellversion wurde bei dieser Ausführung verwendet. Eine spätere
          Aktivierung verändert dieses Ergebnis nicht.
        </p>
        {evaluation.warnings.length > 0 && (
          <div className="mt-4 rounded-lg border border-amber-800 bg-amber-950/30 p-3 text-sm">
            {evaluation.warnings.map((warning) => (
              <p key={warning}>⚠ {warning}</p>
            ))}
          </div>
        )}
      </div>

      <details className="min-w-0 rounded-lg border border-slate-800 p-3 text-sm">
        <summary>Gespeicherte Analysequellen dieser Evaluation</summary>
        {evaluation.sources ? (
          evaluation.sources.map((source) => (
            <p className="mt-2 break-all" key={source.role}>
              {source.role} · {source.source_type} · {source.source_id} · Quellversion{' '}
              {source.source_version} · Modell {source.model_id} / {source.model_version}
              {source.source_type === 'ANALYSIS' &&
                /^[A-Za-z0-9][A-Za-z0-9_.:-]*$/.test(source.source_id) &&
                Number.isSafeInteger(source.source_version) &&
                source.source_version > 0 && (
                  <Link
                    className="ml-3 inline-block underline text-sky-300"
                    to={analysisDetailUrl(source.source_id, source.source_version, {
                      candidateId,
                      evaluationId: evaluation.id,
                    })}
                  >
                    {source.role}: Analyseversion {source.source_version} öffnen
                  </Link>
                )}
            </p>
          ))
        ) : (
          <p className="mt-2">Konkrete Quellen sind in diesem Lesestand nicht enthalten.</p>
        )}
      </details>

      {groups.map((group, index) => {
        const criteria = evaluation.criteria.filter((item) => item.group === group);
        return (
          <div key={group}>
            <div className="mb-2 flex items-center gap-3">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-800 text-sm">
                {index + 1}
              </span>
              <h3 className="text-lg font-semibold">{readable(group)}</h3>
            </div>
            {criteria.length === 0 ? (
              <p className="pl-10 text-sm text-slate-500">Keine Kriterien vorhanden.</p>
            ) : (
              <ul className="space-y-2 pl-10">
                {criteria.map((item) => (
                  <Criterion key={item.criterion_id} item={item} />
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </section>
  );
}

export function CandidatePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedCandidateId = searchParams.get('candidate') ?? '';
  const requestedEvaluationId = searchParams.get('evaluation') ?? '';
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [underlyingNames, setUnderlyingNames] = useState<Record<string, string>>({});
  const nameCache = useRef<Record<string, string>>({});
  const [nameRevision, setNameRevision] = useState(0);
  const [namesIncomplete, setNamesIncomplete] = useState(false);
  const [selectedId, setSelectedId] = useState('');
  const [evaluations, setEvaluations] = useState<CandidateEvaluation[]>([]);
  const [workflow, setWorkflow] = useState<CandidateLiveWorkflow | null>(null);
  const [workflowLoading, setWorkflowLoading] = useState(false);
  const [workflowError, setWorkflowError] = useState<unknown>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [evaluating, setEvaluating] = useState(false);
  const evaluationOperation = useRef<object | null>(null);
  const instance = useRef<object | null>(null);
  const selectedRef = useRef('');

  useLayoutEffect(() => {
    instance.current = {};
    return () => {
      instance.current = null;
    };
  }, []);
  useLayoutEffect(() => {
    if (requestedCandidateId) selectedRef.current = requestedCandidateId;
  }, [requestedCandidateId]);

  useEffect(() => {
    const controller = new AbortController();
    candidateApiClient
      .list(controller.signal)
      .then((items) => {
        if (controller.signal.aborted) return;
        setCandidates(items);
        setSelectedId((current) => {
          const next = requestedCandidateId
            ? items.some((item) => item.id === requestedCandidateId)
              ? requestedCandidateId
              : ''
            : current || items[0]?.id || '';
          selectedRef.current = next;
          return next;
        });
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          setMessage(
            error instanceof Error ? error.message : 'Kandidaten konnten nicht geladen werden.',
          );
        }
      });
    return () => controller.abort();
  }, [requestedCandidateId]);

  useEffect(() => {
    const controller = new AbortController();
    const ids = [...new Set(candidates.map((item) => item.underlying_id))];
    const missing = ids.filter((id) => !nameCache.current[id]);
    if (missing.length === 0) {
      setNamesIncomplete(false);
      return () => controller.abort();
    }
    void Promise.all(
      missing.map(async (id) => {
        try {
          const value = await marketApiClient.getUnderlying(id, controller.signal);
          const name = value.name?.trim();
          return value.id === id && name ? ([id, name] as const) : null;
        } catch {
          return null;
        }
      }),
    ).then((values) => {
      if (controller.signal.aborted) return;
      for (const value of values) if (value) nameCache.current[value[0]] = value[1];
      setUnderlyingNames({ ...nameCache.current });
      setNamesIncomplete(ids.some((id) => !nameCache.current[id]));
    });
    return () => controller.abort();
  }, [candidates, nameRevision]);

  useEffect(() => {
    if (!selectedId) {
      setEvaluations([]);
      setWorkflow(null);
      setWorkflowLoading(false);
      setWorkflowError(null);
      return;
    }

    const controller = new AbortController();
    setEvaluations([]);
    setWorkflow(null);
    setWorkflowLoading(true);
    setWorkflowError(null);

    candidateApiClient
      .evaluations(selectedId, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setEvaluations(value);
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          setMessage(
            error instanceof Error
              ? error.message
              : 'Candidate-Daten konnten nicht geladen werden.',
          );
        }
      });

    candidateApiClient
      .liveWorkflow(selectedId, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setWorkflow(value);
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          setWorkflowError(error);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setWorkflowLoading(false);
      });

    return () => controller.abort();
  }, [selectedId]);

  async function refreshWorkflow() {
    const visit = instance.current;
    if (!selectedId || visit === null || selectedRef.current !== selectedId) return;
    const ownsRead = () => instance.current === visit && selectedRef.current === selectedId;
    setWorkflow(null);
    setWorkflowLoading(true);
    setWorkflowError(null);
    try {
      const value = await candidateApiClient.liveWorkflow(selectedId);
      if (ownsRead()) setWorkflow(value);
    } catch (error: unknown) {
      if (ownsRead()) setWorkflowError(error);
    } finally {
      if (ownsRead()) setWorkflowLoading(false);
    }
  }

  async function evaluateSelected() {
    const visit = instance.current;
    if (
      !selectedId ||
      selectedRef.current !== selectedId ||
      evaluating ||
      workflowLoading ||
      workflowError !== null ||
      workflow?.can_evaluate !== true ||
      visit === null ||
      evaluationOperation.current !== null
    )
      return;
    const pending = {};
    evaluationOperation.current = pending;
    const ownsCommand = () =>
      instance.current === visit &&
      evaluationOperation.current === pending &&
      selectedRef.current === selectedId;
    setEvaluating(true);
    setMessage(null);
    try {
      await candidateApiClient.evaluateAuto(selectedId);
      if (!ownsCommand()) return;
      const evaluationItems = await candidateApiClient.evaluations(selectedId);
      if (!ownsCommand()) return;
      setEvaluations(evaluationItems);
      setSearchParams({ candidate: selectedId });
      await refreshWorkflow();
    } catch (error: unknown) {
      if (!ownsCommand()) return;
      setMessage(
        error instanceof Error
          ? `${error.message} Voraussetzungen werden neu geprüft.`
          : 'Top-down-Bewertung fehlgeschlagen. Voraussetzungen werden neu geprüft.',
      );
      await refreshWorkflow();
    } finally {
      if (instance.current === visit && evaluationOperation.current === pending) {
        evaluationOperation.current = null;
        setEvaluating(false);
      }
    }
  }

  const selected = useMemo(
    () => candidates.find((candidate) => candidate.id === selectedId) ?? null,
    [candidates, selectedId],
  );
  const latest = evaluations[0] ?? null;
  const viewed = requestedEvaluationId
    ? (evaluations.find((evaluation) => evaluation.id === requestedEvaluationId) ?? null)
    : latest;
  const canEvaluate =
    workflow?.can_evaluate === true &&
    !workflowLoading &&
    workflowError === null &&
    (!requestedCandidateId || requestedCandidateId === selectedId);

  return (
    <div className="grid w-full gap-8 lg:grid-cols-[20rem_1fr]">
      <aside>
        <p className="text-xs uppercase tracking-wide text-slate-500">
          Marktanalyse · Handelsideen
        </p>
        <h1 className="mt-1 text-2xl font-semibold">Kandidaten</h1>
        <p className="mt-2 text-sm text-slate-400">
          Untersuche bestehende Handelsideen und ihre Voraussetzungen. Eine Bewertung verändert
          deinen dokumentierten Benutzerstatus nicht.
        </p>
        <div className="mt-5 space-y-2">
          {candidates.map((candidate, index) => (
            <button
              key={candidate.id}
              type="button"
              disabled={evaluating}
              onClick={() => {
                if (evaluationOperation.current !== null) return;
                selectedRef.current = candidate.id;
                setSelectedId(candidate.id);
                setSearchParams({ candidate: candidate.id });
              }}
              className={`w-full rounded-lg border p-3 text-left ${
                candidate.id === selectedId
                  ? 'border-sky-600 bg-sky-950/30'
                  : 'border-slate-800 bg-slate-900 hover:border-slate-700'
              }`}
            >
              <div className="break-words font-medium">
                {underlyingNames[candidate.underlying_id] ??
                  `Kandidat ${index + 1} · Name nicht verfügbar`}
              </div>
              <div className="mt-1 text-xs text-slate-400">
                Benutzerstatus: {readable(candidate.status)}
              </div>
            </button>
          ))}
          {candidates.length === 0 && (
            <p className="text-sm text-slate-500">Noch keine Kandidaten.</p>
          )}
        </div>
      </aside>

      <div className="min-w-0">
        {namesIncomplete && (
          <p role="status" className="mb-4 rounded-lg border border-amber-800 p-3 text-sm">
            Einige Basiswertnamen sind nicht verfügbar. Die gespeicherten Kandidaten und Bewertungen
            bleiben unverändert.{' '}
            <button
              type="button"
              onClick={() => setNameRevision((value) => value + 1)}
              className="underline"
            >
              Bezeichnungen erneut laden
            </button>
          </p>
        )}
        {message && <p className="mb-4 rounded-lg border border-rose-800 p-3 text-sm">{message}</p>}
        {selected ? (
          <>
            <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
              <div>
                <h2 className="break-words text-xl font-semibold">
                  {underlyingNames[selected.underlying_id] ?? 'Basiswertname nicht verfügbar'}
                </h2>
                <details className="mt-2 text-xs text-slate-500">
                  <summary className="cursor-pointer">Technische Referenzen</summary>
                  <p className="break-all">
                    Kandidat {selected.id} · Basiswert {selected.underlying_id}
                  </p>
                </details>
                <Link
                  className="text-sm text-sky-300 underline"
                  to={`/market-charts?underlying=${selected.underlying_id}`}
                >
                  Kursdiagramm und Vergleich
                </Link>
                <p className="mt-2 text-sm text-slate-400">Markt, Sektor und Basiswert</p>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => void evaluateSelected()}
                  disabled={evaluating || !canEvaluate}
                  aria-describedby="candidate-readiness-status"
                  className="rounded-lg border border-sky-700 px-3 py-2 text-sm disabled:opacity-50"
                >
                  {evaluating ? 'Bewertung läuft …' : 'Kandidaten neu bewerten'}
                </button>
                <span className="rounded-full border border-slate-700 px-3 py-1 text-sm">
                  {readable(selected.status)}
                </span>
              </div>
            </div>

            <section className="mb-6 rounded-xl border border-slate-800 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">
                    Aktuelle Voraussetzungen
                  </p>
                  <h3
                    id="candidate-readiness-status"
                    className="mt-1 font-semibold"
                    aria-live="polite"
                  >
                    {workflowLoading
                      ? 'Voraussetzungen werden geprüft …'
                      : workflowError !== null
                        ? 'Voraussetzungen konnten nicht geprüft werden'
                        : workflow?.ready
                          ? 'Bereit für automatische Bewertung'
                          : 'Konfiguration unvollständig'}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => void refreshWorkflow()}
                  disabled={workflowLoading}
                  className="rounded border border-slate-700 px-3 py-1.5 text-xs disabled:opacity-50"
                >
                  Voraussetzungen aktualisieren
                </button>
              </div>

              {workflowLoading && (
                <p className="mt-4 text-sm text-slate-400">
                  Die Kandidatenbewertung bleibt deaktiviert, bis die aktuellen Voraussetzungen
                  geladen sind.
                </p>
              )}

              {workflowError !== null && !workflowLoading && (
                <div className="mt-4 rounded-lg border border-rose-800 p-3 text-sm">
                  <p>
                    Voraussetzungen konnten nicht geprüft werden. Candidate Evaluation bleibt
                    deaktiviert.
                  </p>
                  <button
                    type="button"
                    onClick={() => void refreshWorkflow()}
                    className="mt-3 rounded border border-sky-700 px-3 py-1.5 text-xs"
                  >
                    Erneut prüfen
                  </button>
                </div>
              )}

              {workflow && !workflowLoading && workflowError === null && (
                <>
                  {workflow.next_action && (
                    <p className="mt-3 text-xs text-amber-300">
                      Nächster Schritt: {workflowActionLabel(workflow.next_action)}
                    </p>
                  )}
                  <details className="mt-4" open={!workflow.ready}>
                    <summary className="cursor-pointer rounded text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-300">
                      Voraussetzungen im Detail ·{' '}
                      {workflow.steps.filter((step) => step.status === 'COMPLETE').length} von{' '}
                      {workflow.steps.length} erfüllt
                    </summary>
                    <ul className="mt-3 space-y-2">
                      {workflow.steps.map((step) =>
                        step.code === runtimeStepCode ? (
                          <RuntimeModelStep key={step.code} step={step} />
                        ) : (
                          <li
                            key={step.code}
                            className="rounded-lg border border-slate-800 p-3 text-sm"
                          >
                            <div className="flex flex-wrap justify-between gap-2">
                              <span className="font-medium">{step.label}</span>
                              <span
                                className={
                                  step.status === 'COMPLETE' ? 'text-emerald-400' : 'text-amber-400'
                                }
                              >
                                {readable(step.status)}
                              </span>
                            </div>
                            <p className="mt-1 text-slate-400">{step.detail}</p>
                            {step.status === 'BLOCKED' && step.action && (
                              <Link
                                to={{
                                  pathname: '/top-down-admin',
                                  search: new URLSearchParams({
                                    action: step.action,
                                    ...(step.action === 'RUN_MARKET_ANALYSIS'
                                      ? { step_code: step.code }
                                      : {}),
                                    candidate_id: selected.id,
                                    resource_id: step.resource_id ?? '',
                                    ...Object.fromEntries(Object.entries(step.action_params ?? {})),
                                  }).toString(),
                                }}
                                className="mt-3 inline-block rounded border border-sky-700 px-3 py-1.5 text-xs"
                              >
                                Schritt bearbeiten
                              </Link>
                            )}
                          </li>
                        ),
                      )}
                    </ul>
                  </details>
                </>
              )}
            </section>

            {viewed ? (
              <>
                <div className="mb-5 flex justify-end">
                  <Link
                    to={{
                      pathname: '/trade-plans',
                      search: new URLSearchParams({
                        candidate_id: selected.id,
                        candidate_evaluation_id: viewed.id,
                      }).toString(),
                    }}
                    className="rounded-lg border border-sky-700 px-3 py-2 text-sm"
                  >
                    Tradeplan aus dieser Bewertung erstellen
                  </Link>
                </div>
                <EvaluationDetail evaluation={viewed} candidateId={selected.id} />
              </>
            ) : (
              <p className="rounded-xl border border-slate-800 p-5 text-slate-400">
                {requestedEvaluationId
                  ? 'Die angeforderte Evaluation ist für diesen Kandidaten nicht im Lesestand vorhanden. Keine andere Evaluation wurde eingesetzt.'
                  : 'Für diesen Kandidaten liegt noch keine Evaluation vor.'}
              </p>
            )}
            {evaluations.length > 0 && (
              <div className="mt-8">
                <h3 className="font-semibold">Bewertungshistorie</h3>
                <ul className="mt-3 space-y-2 text-sm text-slate-300">
                  {evaluations.map((evaluation) => (
                    <li
                      key={evaluation.id}
                      className="break-all rounded-lg border border-slate-800 p-3"
                    >
                      <Link
                        className="text-sky-300 underline"
                        to={`/candidates?candidate=${selected.id}&evaluation=${evaluation.id}`}
                      >
                        Bewertungsstand {evaluation.version} · {readable(evaluation.qualification)}{' '}
                        · {new Date(evaluation.evaluated_at).toLocaleString('de-DE')}
                      </Link>
                      <p className="mt-1">
                        Verwendetes Modell {evaluation.model_id} · Version{' '}
                        {evaluation.model_version}
                      </p>
                      <p className="mt-1 text-xs">Evaluation {evaluation.id}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        ) : (
          <p className="text-slate-400">Kandidaten werden nach expliziter Übernahme angezeigt.</p>
        )}
      </div>
    </div>
  );
}
