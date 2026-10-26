import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';

import { marketApiClient } from '../../market/services/client';
import { MarketApiError } from '../../market/services/http';
import type { UnderlyingDetailResponse } from '../../market/types/api';
import { PendingNavigationGuard } from '../../../components/PendingNavigationGuard';
import {
  TradePlanProvenance,
  TradePlanVersionContent,
} from '../components/TradePlanVersionContent';
import { tradePlanContentFromVersion } from '../forms/content';
import { TradePlanContentForm } from '../forms/TradePlanContentForm';
import { tradePlanApiClient } from '../services/client';
import {
  planOriginHintError,
  planOriginHintQuery,
  planViewContextKey,
} from '../services/planViewContext';
import { isTradePlanDetailResponse, isTradePlanVersionResponse } from '../services/responseContext';
import type {
  TradePlanContentRequest,
  TradePlanDetailResponse,
  TradePlanVersionResponse,
} from '../types/api';

interface PlanSnapshot {
  contextKey: string;
  detail: TradePlanDetailResponse;
  versions: TradePlanVersionResponse[];
  current: TradePlanVersionResponse;
  underlying: UnderlyingDetailResponse | null;
}

interface AmendmentDraft {
  contextKey: string;
  planId: string;
  baseVersion: TradePlanVersionResponse;
  original: TradePlanContentRequest;
  content: TradePlanContentRequest;
  changeReason: string;
}

interface ContextMessage {
  contextKey: string;
  text: string;
}

function tradePlanReference(id: string): string {
  return `TP-${id.slice(0, 8).toUpperCase()}`;
}

function nextStep(status: TradePlanVersionResponse['status']): string {
  if (status === 'DRAFT') return 'Zur Prüfung einreichen';
  if (status === 'READY_FOR_REVIEW') return 'Explizit freigeben';
  if (status === 'APPROVED') return 'Produktauswahl starten oder neue Planversion erstellen';
  if (status === 'ABANDONED') return 'Kein weiterer Schritt – TradePlan wurde aufgegeben';
  return 'Historischer, abgelöster Versionsstand';
}

function confirmedCreation(state: unknown, planId: string, versionId: string) {
  if (!state || typeof state !== 'object' || !('confirmedTradePlan' in state)) return null;
  const detail = state.confirmedTradePlan;
  if (
    !isTradePlanDetailResponse(detail) ||
    detail.plan.id !== planId ||
    detail.latest_version.trade_plan_id !== planId ||
    !versionId ||
    detail.latest_version.id !== versionId
  )
    return null;
  return detail;
}

function confirmationText(state: unknown): string {
  return state &&
    typeof state === 'object' &&
    'confirmationMessage' in state &&
    typeof state.confirmationMessage === 'string'
    ? state.confirmationMessage
    : 'TradePlan wurde als DRAFT erstellt.';
}

async function readSnapshot(
  planId: string,
  versionId: string,
  contextKey: string,
  signal: AbortSignal,
  originHints: string,
): Promise<PlanSnapshot> {
  const [detail, versions, exact] = await Promise.all([
    tradePlanApiClient.get(planId, signal),
    tradePlanApiClient.versions(planId, signal),
    versionId ? tradePlanApiClient.version(planId, versionId, signal) : Promise.resolve(null),
  ]);
  if (
    !isTradePlanDetailResponse(detail) ||
    !Array.isArray(versions) ||
    !versions.every(isTradePlanVersionResponse) ||
    (exact !== null && !isTradePlanVersionResponse(exact))
  ) {
    throw new Error(
      'Der geladene Planstand ist unvollständig und kann nicht sicher angezeigt werden.',
    );
  }
  const hintError = planOriginHintError(originHints, detail.plan);
  if (hintError) throw new Error(hintError);
  if (
    detail.plan.id !== planId ||
    detail.latest_version.trade_plan_id !== planId ||
    versions.some((version) => version.trade_plan_id !== planId) ||
    !versions.some((version) => version.id === detail.latest_version.id)
  )
    throw new Error('Der geladene Plan- und Versionskontext ist widersprüchlich.');
  const current = versionId ? exact : detail.latest_version;
  if (
    !current ||
    current.trade_plan_id !== planId ||
    (versionId && current.id !== versionId) ||
    !versions.some((version) => version.id === current.id)
  )
    throw new Error(
      'Die angeforderte Planversion ist nicht verfügbar. Bitte bewusst eine andere Version öffnen.',
    );
  if (
    detail.plan.origin_type === 'CANDIDATE_EVALUATION' &&
    (!detail.plan.candidate_id ||
      !detail.plan.candidate_evaluation_id ||
      current.candidate_evaluation?.candidate_id !== detail.plan.candidate_id ||
      current.candidate_evaluation.evaluation_id !== detail.plan.candidate_evaluation_id)
  )
    throw new Error('Der gespeicherte Kandidatenursprung passt nicht zur Planversion.');
  if (
    detail.plan.origin_type === 'MANUAL' &&
    (detail.plan.candidate_id !== null || detail.plan.candidate_evaluation_id !== null)
  ) {
    throw new Error('Der manuelle Plan enthält widersprüchliche Kandidatenreferenzen.');
  }
  let underlying: UnderlyingDetailResponse | null = null;
  try {
    const resolved = await marketApiClient.getUnderlying(detail.plan.underlying_id, signal);
    if (resolved.id === detail.plan.underlying_id) underlying = resolved;
  } catch {
    // Current master-data labels are optional; plan content keeps its stored identity.
  }
  return { contextKey, detail, versions, current, underlying };
}

export function ExistingTradePlanPage({
  tradePlanId,
  tradePlanVersionId,
}: {
  tradePlanId: string;
  tradePlanVersionId?: string;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedVersionId = tradePlanVersionId ?? searchParams.get('trade_plan_version_id') ?? '';
  const invalidVersionParameter =
    ((tradePlanVersionId !== undefined || searchParams.has('trade_plan_version_id')) &&
      !requestedVersionId.trim()) ||
    searchParams.getAll('trade_plan_version_id').length > 1;
  const originHints = planOriginHintQuery(searchParams);
  const parameterError = invalidVersionParameter
    ? 'Die angeforderte Planversion ist unvollständig oder mehrdeutig.'
    : planOriginHintError(originHints);
  const contextKey = planViewContextKey(tradePlanId, requestedVersionId, searchParams);
  const confirmed = confirmedCreation(location.state, tradePlanId, requestedVersionId);
  const initialConfirmed =
    confirmed && !parameterError && !planOriginHintError(originHints, confirmed.plan)
      ? confirmed
      : null;
  const [snapshot, setSnapshot] = useState<PlanSnapshot | null>(() =>
    initialConfirmed
      ? {
          contextKey,
          detail: initialConfirmed,
          versions: [initialConfirmed.latest_version],
          current: initialConfirmed.latest_version,
          underlying: null,
        }
      : null,
  );
  const [notice, setNotice] = useState<ContextMessage | null>(() =>
    initialConfirmed
      ? {
          contextKey,
          text: confirmationText(location.state),
        }
      : null,
  );
  const [message, setMessage] = useState<ContextMessage | null>(null);
  const [loadingKey, setLoadingKey] = useState<string | null>(null);
  const [operation, setOperation] = useState<object | null>(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState('');
  const [editor, setEditor] = useState<AmendmentDraft | null>(null);
  const activeContext = useRef({ key: contextKey, revision: 0 });
  const mounted = useRef(false);
  const readSequence = useRef(0);
  const mutation = useRef<object | null>(null);
  const dirty = useRef(false);
  if (activeContext.current.key !== contextKey) {
    activeContext.current = { key: contextKey, revision: activeContext.current.revision + 1 };
  }
  const activeSnapshot = !parameterError && snapshot?.contextKey === contextKey ? snapshot : null;
  const activeEditor = editor?.contextKey === contextKey ? editor : null;
  dirty.current = Boolean(
    activeEditor &&
      (activeEditor.changeReason !== '' ||
        JSON.stringify(activeEditor.content) !== JSON.stringify(activeEditor.original)),
  );
  const current = activeSnapshot?.current ?? null;
  const detail = activeSnapshot?.detail ?? null;
  const busy = loadingKey === contextKey || operation !== null;
  const reference = detail ? tradePlanReference(detail.plan.id) : '';
  const canAbandon = current?.status === 'DRAFT' || current?.status === 'READY_FOR_REVIEW';
  const shouldBlockNavigation = useCallback(() => dirty.current || mutation.current !== null, []);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const refresh = useCallback(
    async (key: string, planId: string, versionId: string, signal: AbortSignal) => {
      const sequence = ++readSequence.current;
      const revision = activeContext.current.revision;
      setLoadingKey(key);
      setMessage(null);
      try {
        const next = await readSnapshot(planId, versionId, key, signal, originHints);
        if (
          mounted.current &&
          !signal.aborted &&
          activeContext.current.key === key &&
          activeContext.current.revision === revision &&
          sequence === readSequence.current
        ) {
          setSnapshot(next);
        }
      } catch (error: unknown) {
        if (
          mounted.current &&
          !signal.aborted &&
          activeContext.current.key === key &&
          activeContext.current.revision === revision &&
          sequence === readSequence.current
        ) {
          setMessage({
            contextKey: key,
            text: `Planansicht konnte nicht aktualisiert werden: ${error instanceof Error ? error.message : 'Unbekannter Lesefehler.'}`,
          });
        }
      } finally {
        if (
          mounted.current &&
          !signal.aborted &&
          activeContext.current.key === key &&
          activeContext.current.revision === revision &&
          sequence === readSequence.current
        )
          setLoadingKey(null);
      }
    },
    [originHints],
  );

  useEffect(() => {
    const controller = new AbortController();
    setDeleteConfirmation('');
    if (parameterError) {
      setSnapshot(null);
      setMessage({
        contextKey,
        text: parameterError,
      });
      return () => controller.abort();
    }
    void refresh(contextKey, tradePlanId, requestedVersionId, controller.signal);
    return () => controller.abort();
  }, [contextKey, tradePlanId, requestedVersionId, parameterError, refresh]);

  function selectVersion(versionId: string) {
    if (mutation.current || busy) return;
    const next = new URLSearchParams(searchParams);
    next.set('trade_plan_id', tradePlanId);
    next.set('trade_plan_version_id', versionId);
    setSearchParams(next);
  }

  function mergeConfirmedVersion(
    version: TradePlanVersionResponse,
    key = contextKey,
  ): PlanSnapshot {
    if (!activeSnapshot) throw new Error('Planansicht fehlt.');
    return {
      ...activeSnapshot,
      contextKey: key,
      current: version,
      detail: {
        ...activeSnapshot.detail,
        latest_version:
          version.version >= activeSnapshot.detail.latest_version.version
            ? version
            : activeSnapshot.detail.latest_version,
      },
      versions: [...activeSnapshot.versions.filter((item) => item.id !== version.id), version],
    };
  }

  async function mutate(action: 'submit' | 'approve' | 'return' | 'abandon') {
    if (!detail || !current || mutation.current || busy || activeEditor) return;
    const token = {};
    const key = contextKey;
    const revision = activeContext.current.revision;
    mutation.current = token;
    setOperation(token);
    setMessage(null);
    setNotice(null);
    try {
      let result: TradePlanVersionResponse;
      if (action === 'submit')
        result = await tradePlanApiClient.submitForReview(detail.plan.id, current.id);
      else if (action === 'approve')
        result = await tradePlanApiClient.approve(detail.plan.id, current.id);
      else if (action === 'return')
        result = await tradePlanApiClient.returnToDraft(detail.plan.id, current.id);
      else result = await tradePlanApiClient.abandon(detail.plan.id, current.id);
      if (
        !mounted.current ||
        activeContext.current.key !== key ||
        activeContext.current.revision !== revision
      )
        return;
      if (
        !isTradePlanVersionResponse(result) ||
        result.trade_plan_id !== detail.plan.id ||
        result.id !== current.id
      )
        throw new Error(
          'Die Speicherantwort gehört nicht zur ausgewählten Planversion. Bitte den gespeicherten Stand prüfen.',
        );
      setSnapshot(mergeConfirmedVersion(result));
      setNotice({
        contextKey: key,
        text: `Statusänderung gespeichert: Version ${result.version} · ${result.status}.`,
      });
      await refresh(key, detail.plan.id, current.id, new AbortController().signal);
    } catch (error: unknown) {
      if (
        mounted.current &&
        activeContext.current.key === key &&
        activeContext.current.revision === revision
      )
        setMessage({
          contextKey: key,
          text:
            error instanceof Error
              ? error.message
              : 'Statusänderung konnte nicht bestätigt werden. Gespeicherten Stand vor einer erneuten Aktion prüfen.',
        });
    } finally {
      if (mutation.current === token) {
        mutation.current = null;
        if (mounted.current) setOperation(null);
      }
    }
  }

  function startAmendment() {
    if (!detail || !current || current.status !== 'APPROVED' || mutation.current || busy) return;
    const content = tradePlanContentFromVersion(current);
    setEditor({
      contextKey,
      planId: detail.plan.id,
      baseVersion: current,
      original: content,
      content,
      changeReason: '',
    });
    setMessage(null);
    setNotice(null);
  }

  function cancelAmendment() {
    if (mutation.current) return;
    if (dirty.current && !window.confirm('Ungespeicherte Planänderungen verwerfen?')) return;
    dirty.current = false;
    setEditor(null);
  }

  async function saveAmendment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !activeEditor ||
      !activeSnapshot ||
      !activeEditor.changeReason.trim() ||
      mutation.current ||
      busy
    )
      return;
    const draft = activeEditor;
    const key = contextKey;
    const revision = activeContext.current.revision;
    const token = {};
    mutation.current = token;
    setOperation(token);
    setMessage(null);
    setNotice(null);
    try {
      const created = await tradePlanApiClient.amend(draft.planId, draft.baseVersion.id, {
        ...draft.content,
        change_reason: draft.changeReason,
      });
      if (
        !mounted.current ||
        activeContext.current.key !== key ||
        activeContext.current.revision !== revision
      )
        return;
      if (
        !isTradePlanVersionResponse(created) ||
        !created.id.trim() ||
        created.trade_plan_id !== draft.planId ||
        created.previous_version_id !== draft.baseVersion.id ||
        created.status !== 'DRAFT' ||
        created.version <= draft.baseVersion.version
      ) {
        setMessage({
          contextKey: key,
          text: 'Der Abschluss der Speicherung ist unklar. Die Antwort bestätigt keine vollständige neue Planversion für die gewählte Basis. Die Eingaben bleiben erhalten. Bitte die gespeicherten Versionen prüfen, bevor du erneut speicherst.',
        });
        return;
      }
      const next = new URLSearchParams(searchParams);
      next.set('trade_plan_id', draft.planId);
      next.set('trade_plan_version_id', created.id);
      const nextKey = planViewContextKey(draft.planId, created.id, next);
      const confirmed = mergeConfirmedVersion(created, nextKey);
      const confirmationMessage = `Neue Version ${created.version} wurde als DRAFT gespeichert. Die Freigabe erfolgt separat.`;
      setSnapshot(confirmed);
      setNotice({
        contextKey: nextKey,
        text: confirmationMessage,
      });
      dirty.current = false;
      mutation.current = null;
      setOperation(null);
      setEditor(null);
      setSearchParams(next, {
        state: { confirmedTradePlan: confirmed.detail, confirmationMessage },
      });
    } catch (error: unknown) {
      if (
        mounted.current &&
        activeContext.current.key === key &&
        activeContext.current.revision === revision
      )
        setMessage({
          contextKey: key,
          text:
            error instanceof MarketApiError && error.status < 500
              ? error.message
              : `Der Abschluss der Speicherung ist unklar${error instanceof Error && !(error instanceof TypeError) ? `: ${error.message}` : '.'} Die Eingaben bleiben erhalten. Bitte die gespeicherten Versionen prüfen, bevor du erneut speicherst.`,
        });
    } finally {
      if (mutation.current === token) {
        mutation.current = null;
        if (mounted.current) setOperation(null);
      }
    }
  }

  async function hardDelete() {
    if (!detail || mutation.current || busy || activeEditor || deleteConfirmation !== reference)
      return;
    const token = {};
    const key = contextKey;
    const revision = activeContext.current.revision;
    mutation.current = token;
    setOperation(token);
    setMessage(null);
    try {
      await tradePlanApiClient.delete(detail.plan.id);
      if (
        !mounted.current ||
        activeContext.current.key !== key ||
        activeContext.current.revision !== revision
      )
        return;
      mutation.current = null;
      setOperation(null);
      void navigate('/trade-plans/overview', { replace: true });
    } catch (error: unknown) {
      if (
        mounted.current &&
        activeContext.current.key === key &&
        activeContext.current.revision === revision
      )
        setMessage({
          contextKey: key,
          text: error instanceof Error ? error.message : 'TradePlan konnte nicht gelöscht werden.',
        });
    } finally {
      if (mutation.current === token) {
        mutation.current = null;
        if (mounted.current) setOperation(null);
      }
    }
  }

  return (
    <main className="w-full min-w-0 space-y-6">
      <PendingNavigationGuard
        shouldBlock={shouldBlockNavigation}
        busy={operation !== null}
        onDiscard={() => {
          dirty.current = false;
          setEditor(null);
        }}
      />
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wide text-slate-500">FT-007 · TradePlan</p>
          <h1 className="mt-1 break-words text-2xl font-semibold">
            {detail ? reference : 'TradePlan'}
          </h1>
          {activeSnapshot?.underlying ? (
            <p className="mt-2 break-words text-sm text-slate-400">
              {[
                activeSnapshot.underlying.name,
                activeSnapshot.underlying.primary_listing?.ticker,
                activeSnapshot.underlying.isin,
                activeSnapshot.underlying.wkn,
              ]
                .filter(Boolean)
                .join(' · ')}
            </p>
          ) : (
            detail && (
              <p className="mt-2 text-sm text-slate-400">
                Basiswertbezeichnung derzeit nicht verfügbar.
              </p>
            )
          )}
          {detail && (
            <p className="mt-2 text-sm text-slate-400">
              {detail.plan.origin_type === 'MANUAL' ? 'Manueller Ursprung' : 'Kandidatenursprung'} ·
              LONG
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-3">
          {activeSnapshot && (
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                void refresh(
                  contextKey,
                  tradePlanId,
                  current?.id ?? requestedVersionId,
                  new AbortController().signal,
                )
              }
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm disabled:opacity-50"
            >
              Planansicht aktualisieren
            </button>
          )}
          <Link
            to="/trade-plans/overview"
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm"
          >
            Zur Übersicht
          </Link>
        </div>
      </header>
      {notice?.contextKey === contextKey && (
        <p role="status" className="rounded-lg border border-emerald-800 p-3 text-sm">
          {notice.text}
        </p>
      )}
      {message?.contextKey === contextKey && (
        <p role="alert" className="rounded-lg border border-amber-800 p-3 text-sm">
          {message.text}
        </p>
      )}
      {loadingKey === contextKey && !activeSnapshot && (
        <p className="text-sm text-slate-400">TradePlan wird geladen …</p>
      )}
      {message?.contextKey === contextKey && !parameterError && (
        <button
          type="button"
          disabled={busy}
          onClick={() =>
            void refresh(
              contextKey,
              tradePlanId,
              current?.id ?? requestedVersionId,
              new AbortController().signal,
            )
          }
          className="rounded-lg border border-slate-700 px-3 py-2 text-sm disabled:opacity-50"
        >
          Planansicht erneut laden
        </button>
      )}
      {detail && current && activeSnapshot && (
        <>
          <section className="space-y-5 rounded-xl border border-sky-900 bg-sky-950/20 p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-sky-400">Ausgewählter Stand</p>
                <h2 className="mt-1 text-xl font-semibold">
                  Version {current.version} · {current.status}
                </h2>
                <p className="mt-2 text-sm text-slate-400">
                  Neueste Version: {detail.latest_version.version} · {detail.latest_version.status}
                </p>
              </div>
              <label className="block text-sm">
                <span className="mb-1 block">Planversion</span>
                <select
                  value={current.id}
                  disabled={busy}
                  onChange={(event) => selectVersion(event.target.value)}
                  className="max-w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
                >
                  {[...activeSnapshot.versions]
                    .sort((a, b) => b.version - a.version)
                    .map((version) => (
                      <option key={version.id} value={version.id}>
                        Version {version.version} · {version.status}
                      </option>
                    ))}
                </select>
              </label>
            </div>
            {!activeEditor && (
              <>
                <TradePlanVersionContent version={current} />
                <p className="text-sm text-slate-300">
                  Nächster Schritt: {nextStep(current.status)}
                </p>
                <div className="flex flex-wrap gap-3">
                  {current.status === 'DRAFT' && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void mutate('submit')}
                      className="rounded-lg border border-sky-700 px-4 py-2 text-sm disabled:opacity-50"
                    >
                      Zur Prüfung einreichen
                    </button>
                  )}
                  {current.status === 'READY_FOR_REVIEW' && (
                    <>
                      <button
                        type="button"
                        disabled={busy || current.id !== detail.latest_version.id}
                        onClick={() => void mutate('approve')}
                        className="rounded-lg border border-emerald-700 px-4 py-2 text-sm disabled:opacity-50"
                      >
                        Explizit freigeben
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void mutate('return')}
                        className="rounded-lg border border-slate-700 px-4 py-2 text-sm disabled:opacity-50"
                      >
                        Zurück zu DRAFT
                      </button>
                    </>
                  )}
                  {canAbandon && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void mutate('abandon')}
                      className="rounded-lg border border-rose-800 px-4 py-2 text-sm text-rose-200 disabled:opacity-50"
                    >
                      TradePlan aufgeben
                    </button>
                  )}
                  {current.status === 'APPROVED' && (
                    <>
                      <Link
                        to={`/product-selection?trade_plan_id=${encodeURIComponent(detail.plan.id)}&trade_plan_version_id=${encodeURIComponent(current.id)}`}
                        className="rounded-lg border border-emerald-700 px-4 py-2 text-sm"
                      >
                        Produktauswahl starten
                      </Link>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={startAmendment}
                        className="rounded-lg border border-sky-700 px-4 py-2 text-sm disabled:opacity-50"
                      >
                        Neue Planversion erstellen
                      </button>
                    </>
                  )}
                </div>
                {canAbandon && (
                  <p className="text-xs text-slate-400">
                    Gespeicherte Entwürfe können derzeit nicht inhaltlich revidiert werden. Eine
                    Statusrückkehr zu DRAFT ändert daran nichts.
                  </p>
                )}
                {current.status === 'READY_FOR_REVIEW' &&
                  current.id !== detail.latest_version.id && (
                    <p className="text-sm text-amber-300">
                      Nur die neueste Planversion kann freigegeben werden.
                    </p>
                  )}
              </>
            )}
            {activeEditor && (
              <form
                onSubmit={(event) => void saveAmendment(event)}
                className="space-y-5"
                aria-label="Planversion ändern"
              >
                <h2 className="text-xl font-semibold">
                  Neue Planversion aus Version {activeEditor.baseVersion.version}
                </h2>
                <p className="text-sm text-slate-400">
                  Die freigegebene Ausgangsversion bleibt erhalten. Gespeichert wird ein neuer
                  Entwurf für diesen Plan.
                </p>
                <TradePlanContentForm
                  value={activeEditor.content}
                  disabled={busy}
                  onChange={(content) => setEditor({ ...activeEditor, content })}
                />
                <label className="block text-sm">
                  <span>Änderungsgrund</span>
                  <textarea
                    required
                    value={activeEditor.changeReason}
                    disabled={busy}
                    onChange={(event) =>
                      setEditor({ ...activeEditor, changeReason: event.target.value })
                    }
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                  />
                </label>
                <div className="flex flex-wrap gap-3">
                  <button
                    type="submit"
                    disabled={busy || !activeEditor.changeReason.trim()}
                    className="rounded-lg border border-sky-700 px-4 py-2 text-sm disabled:opacity-50"
                  >
                    Neue DRAFT-Version speichern
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={cancelAmendment}
                    className="rounded-lg border border-slate-700 px-4 py-2 text-sm disabled:opacity-50"
                  >
                    Abbrechen
                  </button>
                </div>
              </form>
            )}
          </section>
          <details className="rounded-xl border border-slate-800 p-5">
            <summary className="cursor-pointer font-semibold">Versionshistorie</summary>
            <ol className="mt-4 space-y-2">
              {[...activeSnapshot.versions]
                .sort((a, b) => b.version - a.version)
                .map((version) => (
                  <li key={version.id} className="rounded-lg border border-slate-800 p-3 text-sm">
                    <button
                      type="button"
                      disabled={busy || version.id === current.id}
                      onClick={() => selectVersion(version.id)}
                      className="rounded px-2 py-1 font-medium underline disabled:no-underline"
                    >
                      Version {version.version} · {version.status}
                    </button>
                    <span className="ml-2 text-slate-400">
                      {new Date(version.created_at).toLocaleString('de-DE')}
                    </span>
                    {version.change_reason && (
                      <p className="mt-1 whitespace-pre-wrap text-slate-300">
                        {version.change_reason}
                      </p>
                    )}
                  </li>
                ))}
            </ol>
          </details>
          <TradePlanProvenance plan={detail.plan} version={current} />
          <section className="rounded-xl border border-rose-900 bg-rose-950/20 p-5">
            <h2 className="text-lg font-semibold text-rose-200">TradePlan dauerhaft löschen</h2>
            <p className="mt-2 text-sm text-rose-100/80">
              Diese Aktion löscht den TradePlan und seine abhängige Auswahl-, Trade-, Positions-,
              Monitoring-, Post-Trade- und Lernhistorie dauerhaft. Gemeinsame Referenzdaten wie
              Underlying, Warrant, Emittent oder Handelsplatz werden nicht gelöscht.
            </p>
            <label className="mt-4 block text-sm text-slate-300" htmlFor="delete-confirmation">
              Zur Bestätigung <strong>{reference}</strong> eingeben
            </label>
            <div className="mt-2 flex flex-wrap gap-3">
              <input
                id="delete-confirmation"
                value={deleteConfirmation}
                onChange={(event) => setDeleteConfirmation(event.target.value)}
                disabled={busy || Boolean(activeEditor)}
                autoComplete="off"
                className="min-w-0 max-w-full rounded-lg border border-rose-900 bg-slate-950 px-3 py-2 text-sm"
              />
              <button
                type="button"
                disabled={busy || Boolean(activeEditor) || deleteConfirmation !== reference}
                onClick={() => void hardDelete()}
                className="rounded-lg border border-rose-700 px-4 py-2 text-sm font-medium text-rose-200 disabled:opacity-40"
              >
                TradePlan unwiderruflich löschen
              </button>
            </div>
          </section>
        </>
      )}
    </main>
  );
}
