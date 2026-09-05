import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { tradePlanApiClient } from '../services/client';
import type {
  CreateTradePlanRequest,
  EntryType,
  TradePlanDetailResponse,
  TradePlanVersionResponse,
} from '../types/api';

type Origin = 'MANUAL' | 'CANDIDATE_EVALUATION';

interface FormState {
  origin: Origin;
  underlyingId: string;
  candidateId: string;
  candidateEvaluationId: string;
  thesis: string;
  entryType: EntryType;
  entryPrice: string;
  entryPriceFrom: string;
  entryPriceTo: string;
  trigger: string;
  currency: string;
  stopPrice: string;
  invalidationRule: string;
  targetPrice: string;
  targetRationale: string;
  thesisRisk: string;
  maxLossAssumption: string;
  riskNotes: string;
}

function tradePlanReference(id: string): string {
  return `TP-${id.slice(0, 8).toUpperCase()}`;
}

function nextStep(status: TradePlanVersionResponse['status']): string {
  if (status === 'DRAFT') return 'Zur Prüfung einreichen';
  if (status === 'READY_FOR_REVIEW') return 'Explizit freigeben';
  if (status === 'APPROVED') return 'Produktauswahl starten';
  if (status === 'ABANDONED') return 'Kein weiterer Schritt – TradePlan wurde aufgegeben';
  return 'Aktuellen versionsgenauen Planstand prüfen';
}

function initialForm(searchParams: URLSearchParams): FormState {
  const candidateId = searchParams.get('candidate_id') ?? '';
  const candidateEvaluationId = searchParams.get('candidate_evaluation_id') ?? '';
  const candidateOrigin = candidateId !== '' && candidateEvaluationId !== '';
  return {
    origin: candidateOrigin ? 'CANDIDATE_EVALUATION' : 'MANUAL',
    underlyingId: searchParams.get('underlying_id') ?? '',
    candidateId,
    candidateEvaluationId,
    thesis: '',
    entryType: 'PRICE',
    entryPrice: '',
    entryPriceFrom: '',
    entryPriceTo: '',
    trigger: '',
    currency: 'EUR',
    stopPrice: '',
    invalidationRule: '',
    targetPrice: '',
    targetRationale: '',
    thesisRisk: '',
    maxLossAssumption: '',
    riskNotes: '',
  };
}

function buildRequest(form: FormState): CreateTradePlanRequest {
  const common = {
    thesis: form.thesis.trim(),
    entry: {
      type: form.entryType,
      currency: form.currency.trim(),
      price: form.entryType === 'PRICE' && form.entryPrice ? form.entryPrice : null,
      price_from:
        form.entryType === 'PRICE_RANGE' && form.entryPriceFrom ? form.entryPriceFrom : null,
      price_to: form.entryType === 'PRICE_RANGE' && form.entryPriceTo ? form.entryPriceTo : null,
      trigger: form.entryType === 'TRIGGER' && form.trigger ? form.trigger.trim() : null,
    },
    invalidation: {
      stop_price: form.stopPrice || null,
      invalidation_rule: form.invalidationRule.trim() || null,
    },
    targets: [
      {
        sequence: 1,
        price: form.targetPrice,
        rationale: form.targetRationale.trim() || null,
      },
    ],
    risk_assumptions: {
      thesis_risk: form.thesisRisk.trim(),
      max_loss_assumption: form.maxLossAssumption.trim() || null,
      notes: form.riskNotes.trim() || null,
    },
  };

  if (form.origin === 'CANDIDATE_EVALUATION') {
    return {
      ...common,
      origin_type: 'CANDIDATE_EVALUATION',
      candidate_id: form.candidateId.trim(),
      candidate_evaluation_id: form.candidateEvaluationId.trim(),
    };
  }

  return {
    ...common,
    origin_type: 'MANUAL',
    underlying_id: form.underlyingId.trim(),
  };
}

function CandidateProvenance({ version }: { version: TradePlanVersionResponse }) {
  const provenance = version.candidate_evaluation;
  if (!provenance) {
    return (
      <section className="rounded-xl border border-slate-800 p-5">
        <h3 className="font-semibold">Provenance</h3>
        <p className="mt-2 text-sm text-slate-400">
          Manueller Ursprung · Underlying wurde direkt für den TradePlan gewählt.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-slate-800 p-5">
      <h3 className="font-semibold">CandidateEvaluation-Provenance</h3>
      <p className="mt-1 text-xs text-slate-500">
        Versionsgenaue, immutable Übergabe. Es wird niemals automatisch auf eine spätere Evaluation
        gewechselt.
      </p>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-slate-500">Candidate</dt>
          <dd className="break-all">{provenance.candidate_id}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Evaluation</dt>
          <dd className="break-all">
            {provenance.evaluation_id} · v{provenance.evaluation_version}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Modell</dt>
          <dd>
            {provenance.model_id} · {provenance.model_version}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Qualifikation</dt>
          <dd>
            {provenance.qualification} · {provenance.quality_status}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-slate-500">Evaluated at</dt>
          <dd>{new Date(provenance.evaluated_at).toLocaleString('de-DE')}</dd>
        </div>
      </dl>
      <div className="mt-4">
        <p className="text-xs uppercase tracking-wide text-slate-500">Source Snapshots</p>
        <ul className="mt-2 space-y-2 text-sm">
          {provenance.sources.map((source) => (
            <li
              key={`${source.role}-${source.source_id}-${source.source_version}`}
              className="rounded-lg border border-slate-800 p-3"
            >
              <span className="font-medium">{source.role}</span> · {source.source_type} · v
              {source.source_version}
              <span className="mt-1 block break-all text-xs text-slate-500">
                {source.source_id} · {source.model_id}/{source.model_version}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function AuditTrail({ version }: { version: TradePlanVersionResponse }) {
  return (
    <section className="rounded-xl border border-slate-800 p-5">
      <h3 className="font-semibold">Audit / Lifecycle</h3>
      <p className="mt-1 text-xs text-slate-500">
        Append-only Ereignisse für genau Version {version.version}.
      </p>
      {version.events.length === 0 ? (
        <p className="mt-4 text-sm text-slate-400">Noch keine Lifecycle-Ereignisse.</p>
      ) : (
        <ol className="mt-4 space-y-3">
          {version.events.map((event) => (
            <li key={event.id} className="rounded-lg border border-slate-800 p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium">{event.event_type}</span>
                <time className="text-xs text-slate-500">
                  {new Date(event.occurred_at).toLocaleString('de-DE')}
                </time>
              </div>
              <p className="mt-1 text-slate-300">
                {event.from_status ?? '—'} → {event.to_status}
              </p>
              <p className="mt-1 break-all text-xs text-slate-500">
                Actor {event.actor}
                {event.correlation_id ? ` · Correlation ${event.correlation_id}` : ''}
              </p>
              {event.reason && <p className="mt-2 text-sm text-slate-400">{event.reason}</p>}
            </li>
          ))}
        </ol>
      )}
      {version.approval && (
        <div className="mt-4 rounded-lg border border-emerald-800 bg-emerald-950/30 p-3 text-sm">
          <p className="font-medium">Approval-Nachweis</p>
          <p className="mt-1">
            Version {version.approval.version} ·{' '}
            {new Date(version.approval.approved_at).toLocaleString('de-DE')}
          </p>
          <p className="mt-1 break-all text-xs text-slate-400">
            Approval {version.approval.approval_id} · Actor {version.approval.actor}
            {version.approval.correlation_id
              ? ` · Correlation ${version.approval.correlation_id}`
              : ''}
          </p>
        </div>
      )}
    </section>
  );
}

function VersionCard({ version }: { version: TradePlanVersionResponse }) {
  return (
    <section className="rounded-xl border border-slate-800 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Version {version.version}
          </p>
          <h3 className="mt-1 text-lg font-semibold">{version.status}</h3>
        </div>
        <span className="rounded-full border border-slate-700 px-3 py-1 text-xs">
          {version.direction}
        </span>
      </div>
      <p className="mt-4 whitespace-pre-wrap text-sm text-slate-200">{version.thesis}</p>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-slate-500">Entry</dt>
          <dd>{version.entry.type}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Stop</dt>
          <dd>{version.invalidation.stop_price ?? '—'}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Target 1</dt>
          <dd>{version.targets[0]?.price ?? '—'}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Plan-Risiko</dt>
          <dd>{version.risk_assumptions.thesis_risk}</dd>
        </div>
      </dl>
      {version.approval && (
        <p className="mt-4 rounded-lg border border-emerald-800 bg-emerald-950/30 p-3 text-sm">
          Freigegeben am {new Date(version.approval.approved_at).toLocaleString('de-DE')} · Actor{' '}
          {version.approval.actor}
        </p>
      )}
    </section>
  );
}

export function TradePlanPage() {
  const [searchParams] = useSearchParams();
  const tradePlanId = searchParams.get('trade_plan_id')?.trim() ?? '';
  const [form, setForm] = useState<FormState>(() => initialForm(searchParams));
  const [detail, setDetail] = useState<TradePlanDetailResponse | null>(null);
  const [versions, setVersions] = useState<TradePlanVersionResponse[]>([]);
  const [lookupId, setLookupId] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const current = detail?.latest_version ?? null;
  const canSubmit = current?.status === 'DRAFT';
  const canApprove = current?.status === 'READY_FOR_REVIEW';
  const canReturnDraft = current?.status === 'READY_FOR_REVIEW';
  const canAbandon = current?.status === 'DRAFT' || current?.status === 'READY_FOR_REVIEW';

  const originHint = useMemo(() => {
    if (form.origin === 'CANDIDATE_EVALUATION') {
      return 'Das Underlying wird serverseitig ausschließlich aus der konkreten CandidateEvaluation aufgelöst.';
    }
    return 'Manueller Ursprung referenziert direkt ein Underlying.';
  }, [form.origin]);

  async function refresh(planId: string) {
    const [nextDetail, history] = await Promise.all([
      tradePlanApiClient.get(planId),
      tradePlanApiClient.versions(planId),
    ]);
    setDetail(nextDetail);
    setVersions(history);
    setLookupId(planId);
  }

  useEffect(() => {
    if (!tradePlanId) return;
    let active = true;
    setBusy(true);
    setMessage(null);
    Promise.all([tradePlanApiClient.get(tradePlanId), tradePlanApiClient.versions(tradePlanId)])
      .then(([nextDetail, history]) => {
        if (!active) return;
        setDetail(nextDetail);
        setVersions(history);
        setLookupId(tradePlanId);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setMessage(
          error instanceof Error ? error.message : 'TradePlan konnte nicht geladen werden.',
        );
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, [tradePlanId]);

  async function createPlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const created = await tradePlanApiClient.create(buildRequest(form));
      setDetail(created);
      setVersions([created.latest_version]);
      setLookupId(created.plan.id);
      setMessage('TradePlan wurde als DRAFT erstellt.');
    } catch (error: unknown) {
      setMessage(
        error instanceof Error ? error.message : 'TradePlan konnte nicht erstellt werden.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function lookupPlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!lookupId.trim()) return;
    setBusy(true);
    setMessage(null);
    try {
      await refresh(lookupId.trim());
    } catch (error: unknown) {
      setMessage(error instanceof Error ? error.message : 'TradePlan konnte nicht geladen werden.');
    } finally {
      setBusy(false);
    }
  }

  function applyVersion(nextVersion: TradePlanVersionResponse) {
    setDetail((currentDetail) =>
      currentDetail ? { ...currentDetail, latest_version: nextVersion } : currentDetail,
    );
    setVersions((currentVersions) => {
      const remaining = currentVersions.filter((item) => item.id !== nextVersion.id);
      return [...remaining, nextVersion].sort((left, right) => left.version - right.version);
    });
  }

  async function mutate(action: 'submit' | 'approve' | 'return' | 'abandon') {
    if (!detail || !current) return;
    setBusy(true);
    setMessage(null);
    try {
      let nextVersion: TradePlanVersionResponse;
      if (action === 'submit') {
        nextVersion = await tradePlanApiClient.submitForReview(detail.plan.id, current.id);
      } else if (action === 'approve') {
        nextVersion = await tradePlanApiClient.approve(detail.plan.id, current.id);
      } else if (action === 'return') {
        nextVersion = await tradePlanApiClient.returnToDraft(detail.plan.id, current.id);
      } else {
        nextVersion = await tradePlanApiClient.abandon(detail.plan.id, current.id);
      }
      applyVersion(nextVersion);
    } catch (error: unknown) {
      setMessage(error instanceof Error ? error.message : 'Statusänderung fehlgeschlagen.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="w-full space-y-8">
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-500">FT-007</p>
        <h1 className="mt-1 text-2xl font-semibold">TradePlan</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Produktneutrale, versionierte Trade-Planung. Freigaben sind explizite
          Benutzerentscheidungen; Position Sizing, Ordermenge und Execution sind nicht Bestandteil
          dieses Workflows.
        </p>
      </div>

      {message && <p className="rounded-lg border border-slate-700 p-3 text-sm">{message}</p>}

      <div className="grid gap-8 xl:grid-cols-[1.1fr_0.9fr]">
        <form
          onSubmit={(event) => void createPlan(event)}
          className="space-y-5 rounded-xl border border-slate-800 p-5"
        >
          <div>
            <h2 className="text-lg font-semibold">Neuen TradePlan anlegen</h2>
            <p className="mt-1 text-sm text-slate-500">V1 ist vollständig LONG-only.</p>
          </div>

          <label className="block text-sm">
            <span className="text-slate-400">Ursprung</span>
            <select
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
              value={form.origin}
              onChange={(event) => setForm({ ...form, origin: event.target.value as Origin })}
            >
              <option value="MANUAL">Manuell gewähltes Underlying</option>
              <option value="CANDIDATE_EVALUATION">CandidateEvaluation</option>
            </select>
          </label>
          <p className="text-xs text-slate-500">{originHint}</p>

          {form.origin === 'MANUAL' ? (
            <label className="block text-sm">
              <span className="text-slate-400">Underlying-ID</span>
              <input
                required
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                value={form.underlyingId}
                onChange={(event) => setForm({ ...form, underlyingId: event.target.value })}
              />
            </label>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm">
                <span className="text-slate-400">Candidate-ID</span>
                <input
                  required
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                  value={form.candidateId}
                  onChange={(event) => setForm({ ...form, candidateId: event.target.value })}
                />
              </label>
              <label className="block text-sm">
                <span className="text-slate-400">CandidateEvaluation-ID</span>
                <input
                  required
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                  value={form.candidateEvaluationId}
                  onChange={(event) =>
                    setForm({ ...form, candidateEvaluationId: event.target.value })
                  }
                />
              </label>
            </div>
          )}

          <label className="block text-sm">
            <span className="text-slate-400">Trade Thesis</span>
            <textarea
              required
              rows={4}
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
              value={form.thesis}
              onChange={(event) => setForm({ ...form, thesis: event.target.value })}
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="text-slate-400">Entry-Art</span>
              <select
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                value={form.entryType}
                onChange={(event) =>
                  setForm({ ...form, entryType: event.target.value as EntryType })
                }
              >
                <option value="PRICE">Preis</option>
                <option value="PRICE_RANGE">Preisbereich</option>
                <option value="TRIGGER">Trigger</option>
              </select>
            </label>
            <label className="block text-sm">
              <span className="text-slate-400">Währung</span>
              <input
                required
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                value={form.currency}
                onChange={(event) => setForm({ ...form, currency: event.target.value })}
              />
            </label>
          </div>
          {form.entryType === 'PRICE' && (
            <label className="block text-sm">
              <span className="text-slate-400">Entry-Preis</span>
              <input
                required
                inputMode="decimal"
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                value={form.entryPrice}
                onChange={(event) => setForm({ ...form, entryPrice: event.target.value })}
              />
            </label>
          )}
          {form.entryType === 'PRICE_RANGE' && (
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm">
                <span className="text-slate-400">Preis von</span>
                <input
                  required
                  inputMode="decimal"
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                  value={form.entryPriceFrom}
                  onChange={(event) => setForm({ ...form, entryPriceFrom: event.target.value })}
                />
              </label>
              <label className="block text-sm">
                <span className="text-slate-400">Preis bis</span>
                <input
                  required
                  inputMode="decimal"
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                  value={form.entryPriceTo}
                  onChange={(event) => setForm({ ...form, entryPriceTo: event.target.value })}
                />
              </label>
            </div>
          )}
          {form.entryType === 'TRIGGER' && (
            <label className="block text-sm">
              <span className="text-slate-400">Trigger</span>
              <input
                required
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                value={form.trigger}
                onChange={(event) => setForm({ ...form, trigger: event.target.value })}
              />
            </label>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="text-slate-400">Technischer Stop</span>
              <input
                inputMode="decimal"
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                value={form.stopPrice}
                onChange={(event) => setForm({ ...form, stopPrice: event.target.value })}
              />
            </label>
            <label className="block text-sm">
              <span className="text-slate-400">Invalidierungsregel</span>
              <input
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                value={form.invalidationRule}
                onChange={(event) => setForm({ ...form, invalidationRule: event.target.value })}
              />
            </label>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="text-slate-400">Target 1</span>
              <input
                required
                inputMode="decimal"
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                value={form.targetPrice}
                onChange={(event) => setForm({ ...form, targetPrice: event.target.value })}
              />
            </label>
            <label className="block text-sm">
              <span className="text-slate-400">Target-Begründung</span>
              <input
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                value={form.targetRationale}
                onChange={(event) => setForm({ ...form, targetRationale: event.target.value })}
              />
            </label>
          </div>

          <label className="block text-sm">
            <span className="text-slate-400">Plan-Risiko / Annahme</span>
            <textarea
              required
              rows={2}
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
              value={form.thesisRisk}
              onChange={(event) => setForm({ ...form, thesisRisk: event.target.value })}
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="text-slate-400">Max-Loss-Annahme (optional)</span>
              <input
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                value={form.maxLossAssumption}
                onChange={(event) => setForm({ ...form, maxLossAssumption: event.target.value })}
              />
            </label>
            <label className="block text-sm">
              <span className="text-slate-400">Risk Notes</span>
              <input
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                value={form.riskNotes}
                onChange={(event) => setForm({ ...form, riskNotes: event.target.value })}
              />
            </label>
          </div>

          <button
            disabled={busy}
            className="rounded-lg border border-sky-700 px-4 py-2 text-sm disabled:opacity-50"
            type="submit"
          >
            TradePlan als DRAFT erstellen
          </button>
        </form>

        <div className="space-y-5">
          <form
            onSubmit={(event) => void lookupPlan(event)}
            className="rounded-xl border border-slate-800 p-5"
          >
            <h2 className="font-semibold">TradePlan laden</h2>
            <div className="mt-3 flex gap-2">
              <input
                aria-label="TradePlan-ID"
                className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 p-2 text-sm"
                value={lookupId}
                onChange={(event) => setLookupId(event.target.value)}
                placeholder="TradePlan UUID"
              />
              <button
                disabled={busy}
                className="rounded-lg border border-slate-700 px-3 text-sm disabled:opacity-50"
                type="submit"
              >
                Laden
              </button>
            </div>
          </form>

          {detail && current ? (
            <>
              <section className="rounded-xl border border-sky-900 bg-sky-950/20 p-5">
                <p className="text-xs uppercase tracking-wide text-slate-500">Aktiver TradePlan</p>
                <h2 className="mt-1 text-xl font-semibold">{tradePlanReference(detail.plan.id)}</h2>
                <p className="mt-1 text-sm text-slate-400">
                  Erstellt {new Date(detail.plan.created_at).toLocaleString('de-DE')}
                </p>
                <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
                  <div>
                    <dt className="text-slate-500">Status</dt>
                    <dd className="mt-1 font-medium">{current.status}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Version</dt>
                    <dd className="mt-1 font-medium">{current.version}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Nächster Schritt</dt>
                    <dd className="mt-1 font-medium">{nextStep(current.status)}</dd>
                  </div>
                </dl>
                <details className="mt-4 text-xs text-slate-500">
                  <summary className="cursor-pointer">Technische Referenz anzeigen</summary>
                  <p className="mt-2 break-all">{detail.plan.id}</p>
                </details>
              </section>
              <VersionCard version={current} />
              <CandidateProvenance version={current} />
              <AuditTrail version={current} />
              <section className="rounded-xl border border-slate-800 p-5">
                <h3 className="font-semibold">Benutzeraktionen</h3>
                <p className="mt-1 text-xs text-slate-500">
                  Approval ist eine separate, explizite Entscheidung für genau diese Version.
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy || !canSubmit}
                    onClick={() => void mutate('submit')}
                    className="rounded-lg border border-sky-700 px-3 py-2 text-sm disabled:opacity-40"
                  >
                    Zur Prüfung
                  </button>
                  <button
                    type="button"
                    disabled={busy || !canApprove}
                    onClick={() => void mutate('approve')}
                    className="rounded-lg border border-emerald-700 px-3 py-2 text-sm disabled:opacity-40"
                  >
                    Explizit freigeben
                  </button>
                  <button
                    type="button"
                    disabled={busy || !canReturnDraft}
                    onClick={() => void mutate('return')}
                    className="rounded-lg border border-slate-700 px-3 py-2 text-sm disabled:opacity-40"
                  >
                    Zurück zu DRAFT
                  </button>
                  <button
                    type="button"
                    disabled={busy || !canAbandon}
                    onClick={() => void mutate('abandon')}
                    className="rounded-lg border border-rose-800 px-3 py-2 text-sm disabled:opacity-40"
                  >
                    Aufgeben
                  </button>
                  {current.status === 'APPROVED' && (
                    <Link
                      to={{
                        pathname: '/product-selection',
                        search: new URLSearchParams({
                          trade_plan_id: detail.plan.id,
                          trade_plan_version_id: current.id,
                        }).toString(),
                      }}
                      className="rounded-lg border border-violet-700 px-3 py-2 text-sm"
                    >
                      Produktauswahl starten
                    </Link>
                  )}
                </div>
              </section>
              <section>
                <h3 className="font-semibold">Versionshistorie</h3>
                <ul className="mt-3 space-y-2 text-sm">
                  {versions.map((version) => (
                    <li key={version.id} className="rounded-lg border border-slate-800 p-3">
                      Version {version.version} · {version.status} ·{' '}
                      {new Date(version.created_at).toLocaleString('de-DE')}
                      {version.change_reason ? ` · ${version.change_reason}` : ''}
                    </li>
                  ))}
                </ul>
              </section>
            </>
          ) : (
            <p className="rounded-xl border border-slate-800 p-5 text-sm text-slate-400">
              Nach dem Erstellen oder Laden erscheint hier der versionsgenaue Planstand mit
              Lifecycle-Aktionen.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
