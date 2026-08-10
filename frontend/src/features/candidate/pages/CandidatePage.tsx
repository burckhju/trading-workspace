import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { candidateApiClient } from '../services/client';
import type {
  Candidate,
  CandidateCriterion,
  CandidateEvaluation,
  CandidateLiveWorkflow,
} from '../types/api';

const groups = ['MARKET', 'SECTOR', 'UNDERLYING'] as const;

function resultClasses(result: string) {
  if (result === 'FULFILLED' || result === 'QUALIFIED')
    return 'border-emerald-700 bg-emerald-950/40';
  if (result === 'NOT_FULFILLED' || result === 'NOT_QUALIFIED')
    return 'border-rose-700 bg-rose-950/40';
  if (result === 'NOT_EVALUABLE') return 'border-amber-700 bg-amber-950/40';
  return 'border-slate-700 bg-slate-900';
}

function Criterion({ item }: { item: CandidateCriterion }) {
  return (
    <li className={`rounded-lg border p-3 ${resultClasses(item.evaluation)}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium">{item.criterion_id}</span>
        <span className="text-xs text-slate-300">
          {item.severity} · {item.evaluation}
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-300">{item.explanation}</p>
      <p className="mt-1 text-xs text-slate-400">
        Ist: {item.actual_value ?? '—'} · Erwartet: {item.expected_value ?? 'informativ'}
      </p>
    </li>
  );
}

function EvaluationDetail({ evaluation }: { evaluation: CandidateEvaluation }) {
  return (
    <section className="space-y-5">
      <div className={`rounded-xl border p-5 ${resultClasses(evaluation.qualification)}`}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Systemqualifikation</p>
            <h2 className="mt-1 text-2xl font-semibold">{evaluation.qualification}</h2>
          </div>
          <div className="text-right text-sm text-slate-300">
            <div>{evaluation.model_id}</div>
            <div>Version {evaluation.model_version}</div>
            <div>Qualität {evaluation.quality_status}</div>
          </div>
        </div>
        {evaluation.warnings.length > 0 && (
          <div className="mt-4 rounded-lg border border-amber-800 bg-amber-950/30 p-3 text-sm">
            {evaluation.warnings.map((warning) => (
              <p key={warning}>⚠ {warning}</p>
            ))}
          </div>
        )}
      </div>

      {groups.map((group, index) => {
        const criteria = evaluation.criteria.filter((item) => item.group === group);
        return (
          <div key={group}>
            <div className="mb-2 flex items-center gap-3">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-800 text-sm">
                {index + 1}
              </span>
              <h3 className="text-lg font-semibold">{group}</h3>
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
  const [searchParams] = useSearchParams();
  const requestedCandidateId = searchParams.get('candidate') ?? '';
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [evaluations, setEvaluations] = useState<CandidateEvaluation[]>([]);
  const [workflow, setWorkflow] = useState<CandidateLiveWorkflow | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [evaluating, setEvaluating] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    candidateApiClient
      .list(controller.signal)
      .then((items) => {
        setCandidates(items);
        setSelectedId((current) => current || (requestedCandidateId && items.some((item) => item.id === requestedCandidateId) ? requestedCandidateId : items[0]?.id || ''));
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
    if (!selectedId) {
      setEvaluations([]);
      setWorkflow(null);
      return;
    }
    const controller = new AbortController();
    Promise.all([
      candidateApiClient.evaluations(selectedId, controller.signal),
      candidateApiClient.liveWorkflow(selectedId, controller.signal),
    ])
      .then(([evaluationItems, workflowValue]) => {
        setEvaluations(evaluationItems);
        setWorkflow(workflowValue);
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          setMessage(
            error instanceof Error ? error.message : 'Candidate-Daten konnten nicht geladen werden.',
          );
        }
      });
    return () => controller.abort();
  }, [selectedId]);


  async function evaluateSelected() {
    if (!selectedId || evaluating) return;
    setEvaluating(true);
    setMessage(null);
    try {
      await candidateApiClient.evaluateAuto(selectedId);
      const [evaluationItems, workflowValue] = await Promise.all([
        candidateApiClient.evaluations(selectedId),
        candidateApiClient.liveWorkflow(selectedId),
      ]);
      setEvaluations(evaluationItems);
      setWorkflow(workflowValue);
    } catch (error: unknown) {
      setMessage(error instanceof Error ? error.message : 'Top-down-Bewertung fehlgeschlagen.');
    } finally {
      setEvaluating(false);
    }
  }

  const selected = useMemo(
    () => candidates.find((candidate) => candidate.id === selectedId) ?? null,
    [candidates, selectedId],
  );
  const latest = evaluations[0] ?? null;

  return (
    <div className="grid w-full gap-8 lg:grid-cols-[20rem_1fr]">
      <aside>
        <p className="text-xs uppercase tracking-wide text-slate-500">FT-005</p>
        <h1 className="mt-1 text-2xl font-semibold">Kandidaten</h1>
        <p className="mt-2 text-sm text-slate-400">
          Systemqualifikation und Benutzerstatus bleiben bewusst getrennt.
        </p>
        <div className="mt-5 space-y-2">
          {candidates.map((candidate) => (
            <button
              key={candidate.id}
              type="button"
              onClick={() => setSelectedId(candidate.id)}
              className={`w-full rounded-lg border p-3 text-left ${
                candidate.id === selectedId
                  ? 'border-sky-600 bg-sky-950/30'
                  : 'border-slate-800 bg-slate-900 hover:border-slate-700'
              }`}
            >
              <div className="font-medium">{candidate.underlying_id}</div>
              <div className="mt-1 text-xs text-slate-400">Benutzerstatus: {candidate.status}</div>
            </button>
          ))}
          {candidates.length === 0 && (
            <p className="text-sm text-slate-500">Noch keine Kandidaten.</p>
          )}
        </div>
      </aside>

      <div>
        {message && <p className="mb-4 rounded-lg border border-rose-800 p-3 text-sm">{message}</p>}
        {selected ? (
          <>
            <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-sm text-slate-400">Basiswert {selected.underlying_id}</p>
                <h2 className="text-xl font-semibold">Top-down Candidate</h2>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => void evaluateSelected()}
                  disabled={evaluating || workflow?.can_evaluate === false}
                  className="rounded-lg border border-sky-700 px-3 py-2 text-sm disabled:opacity-50"
                >
                  {evaluating ? 'Bewertung läuft …' : 'Top-down neu bewerten'}
                </button>
                <span className="rounded-full border border-slate-700 px-3 py-1 text-sm">
                  {selected.status}
                </span>
              </div>
            </div>
            {workflow && (
              <section className="mb-6 rounded-xl border border-slate-800 p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Live-Konfiguration</p>
                    <h3 className="mt-1 font-semibold">{workflow.ready ? 'Bereit für automatische Bewertung' : 'Konfiguration unvollständig'}</h3>
                  </div>
                  {workflow.next_action && (
                    <span className="rounded-full border border-amber-700 px-3 py-1 text-xs">
                      Nächster Schritt: {workflow.next_action}
                    </span>
                  )}
                </div>
                <ul className="mt-4 space-y-2">
                  {workflow.steps.map((step) => (
                    <li key={step.code} className="rounded-lg border border-slate-800 p-3 text-sm">
                      <div className="flex flex-wrap justify-between gap-2">
                        <span className="font-medium">{step.label}</span>
                        <span className={step.status === 'COMPLETE' ? 'text-emerald-400' : 'text-amber-400'}>
                          {step.status}
                        </span>
                      </div>
                      <p className="mt-1 text-slate-400">{step.detail}</p>
                      {step.status === 'BLOCKED' && step.action && (
                        <Link
                          to={{
                            pathname: '/top-down-admin',
                            search: new URLSearchParams({
                              action: step.action,
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
                  ))}
                </ul>
              </section>
            )}

            {latest ? (
              <EvaluationDetail evaluation={latest} />
            ) : (
              <p className="rounded-xl border border-slate-800 p-5 text-slate-400">
                Für diesen Kandidaten liegt noch keine Evaluation vor.
              </p>
            )}
            {evaluations.length > 1 && (
              <div className="mt-8">
                <h3 className="font-semibold">Bewertungshistorie</h3>
                <ul className="mt-3 space-y-2 text-sm text-slate-300">
                  {evaluations.map((evaluation) => (
                    <li key={evaluation.id} className="rounded-lg border border-slate-800 p-3">
                      Version {evaluation.version} · {evaluation.qualification} ·{' '}
                      {new Date(evaluation.evaluated_at).toLocaleString('de-DE')}
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
