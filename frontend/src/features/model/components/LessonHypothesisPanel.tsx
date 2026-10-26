import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';

import { ErrorNotice, LoadingNotice } from '../../market/components/ApiFeedback';
import { HypothesisProposalPanel } from './HypothesisProposalPanel';
import { lessonHypothesisClient } from '../services/lessonHypothesisClient';
import type { LessonHypothesis } from '../types/lessonHypothesis';

export interface LessonHypothesisNavigationState {
  dirty: boolean;
  busy: boolean;
}

interface LessonHypothesisPanelProps {
  lessonVersionId: string;
  actionsDisabled?: boolean;
  isActionsDisabled?: () => boolean;
  onNavigationStateChange?: (state: LessonHypothesisNavigationState) => void;
}

export function LessonHypothesisPanel(props: LessonHypothesisPanelProps) {
  return <LessonHypothesisForm key={props.lessonVersionId} {...props} />;
}

function LessonHypothesisForm({
  lessonVersionId,
  actionsDisabled = false,
  isActionsDisabled,
  onNavigationStateChange,
}: LessonHypothesisPanelProps) {
  const [hypotheses, setHypotheses] = useState<LessonHypothesis[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [title, setTitle] = useState('');
  const [statement, setStatement] = useState('');
  const [ready, setReady] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const instance = useRef<object | null>(null);
  const operation = useRef<object | null>(null);
  const read = useRef<AbortController | null>(null);
  const requiredHypothesisIds = useRef(new Set<string>());
  const draft = useRef({ title: '', statement: '' });
  const navigationListener = useRef(onNavigationStateChange);
  navigationListener.current = onNavigationStateChange;

  function reportNavigationState() {
    navigationListener.current?.({
      dirty: draft.current.title.length > 0 || draft.current.statement.length > 0,
      busy: operation.current !== null,
    });
  }

  function actionsAreDisabled() {
    return actionsDisabled || isActionsDisabled?.() === true;
  }

  useLayoutEffect(() => {
    instance.current = {};
    navigationListener.current?.({
      dirty: draft.current.title.length > 0 || draft.current.statement.length > 0,
      busy: operation.current !== null,
    });
    return () => {
      instance.current = null;
      read.current?.abort();
      navigationListener.current?.({ dirty: false, busy: false });
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const visit = instance.current;
    read.current = controller;
    const isCurrent = () =>
      visit !== null &&
      instance.current === visit &&
      read.current === controller &&
      !controller.signal.aborted;
    setLoading(true);
    setReady(false);
    setError(null);

    lessonHypothesisClient
      .listForLessonVersion(lessonVersionId, controller.signal)
      .then((items) => {
        if (!isCurrent()) return;
        if (items.some((item) => item.source_lesson_version_id !== lessonVersionId))
          throw new Error('Die Hypothesen gehören nicht zur gewählten Lesson-Version.');
        if ([...requiredHypothesisIds.current].some((id) => !items.some((item) => item.id === id)))
          throw new Error('Die bestätigte Hypothese fehlt im aktuellen Lesestand.');
        setHypotheses(items);
        requiredHypothesisIds.current.clear();
        setReady(true);
      })
      .catch((nextError: unknown) => {
        if (isCurrent()) setError(nextError);
      })
      .finally(() => {
        if (isCurrent()) setLoading(false);
      });

    return () => controller.abort();
  }, [lessonVersionId, refresh]);

  function reloadHypotheses(hypothesisId?: string) {
    if (instance.current === null || operation.current !== null) return;
    if (hypothesisId) requiredHypothesisIds.current.add(hypothesisId);
    // Invalidate synchronously; a completed transport may settle before effect cleanup.
    read.current?.abort();
    setReady(false);
    setLoading(true);
    setError(null);
    setRefresh((n) => n + 1);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const visit = instance.current;
    if (
      !ready ||
      loading ||
      actionsAreDisabled() ||
      !title.trim() ||
      !statement.trim() ||
      hypotheses.length > 0 ||
      visit === null ||
      operation.current !== null
    )
      return;
    const pending = {};
    operation.current = pending;
    // The page guard must see pending work before React commits the next render.
    reportNavigationState();
    const ownsCommand = () => instance.current === visit && operation.current === pending;
    setSaving(true);
    setError(null);
    try {
      const created = await lessonHypothesisClient.createFromLessonVersion(lessonVersionId, {
        title,
        statement,
      });
      if (!ownsCommand()) return;
      if (created.source_lesson_version_id !== lessonVersionId || !created.id)
        throw new Error('Die Hypothesenantwort gehört nicht zur gewählten Lesson-Version.');
      setHypotheses((current) => [...current, created]);
      draft.current = { title: '', statement: '' };
      setTitle('');
      setStatement('');
    } catch (nextError: unknown) {
      if (ownsCommand()) {
        setError(nextError);
        setReady(false);
      }
    } finally {
      if (ownsCommand()) {
        operation.current = null;
        reportNavigationState();
        setSaving(false);
      }
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    void submit(event);
  }

  if (loading && hypotheses.length === 0)
    return <LoadingNotice label="FT-013-Hypothesen werden geladen …" />;

  return (
    <section className="rounded-xl border border-slate-800 p-5">
      <h2 className="font-semibold">FT-013 Hypothesen</h2>
      <p className="mt-2 text-sm text-slate-400">
        Eine Hypothese ist eine explizite Interpretation dieser Lesson-Version. Sie aktiviert keine
        Modelländerung und startet keine Validierung automatisch.
      </p>
      <p className="mt-2 break-all text-xs">Quell-LessonVersion {lessonVersionId}</p>

      {actionsDisabled && (
        <p className="mt-2 text-sm text-amber-300" role="status">
          Lesson-Kontext wird geprüft. Eingaben bleiben erhalten; neue Governance-Aktionen sind
          vorübergehend gesperrt.
        </p>
      )}

      {error !== null && (
        <div className="mt-4">
          <ErrorNotice error={error} />
          <button type="button" disabled={saving} onClick={() => reloadHypotheses()}>
            Hypothesenstand neu laden
          </button>
          <p className="mt-2 text-sm">
            Befehlsabschluss vor einer weiteren Übermittlung bewusst prüfen. Keine automatische
            Wiederholung.
          </p>
        </div>
      )}

      {hypotheses.length > 0 ? (
        <div className="mt-4 space-y-3">
          <p className="text-sm font-medium text-emerald-300">Bereits an FT-013 übergeben</p>
          {hypotheses.map((hypothesis) => (
            <article key={hypothesis.id} className="rounded-lg border border-slate-800 p-4">
              <div className="flex items-center justify-between gap-4">
                <h3 className="font-medium">{hypothesis.title}</h3>
                <span className="text-xs text-slate-400">
                  {loading
                    ? 'Status wird geprüft …'
                    : ready
                      ? hypothesis.status
                      : 'Status nicht verifiziert'}
                </span>
              </div>
              <p className="mt-2 whitespace-pre-wrap text-sm text-slate-300">
                {hypothesis.statement}
              </p>
              <p className="mt-2 break-all text-xs text-slate-500">{hypothesis.id}</p>
              <p className="mt-1 break-all text-xs text-slate-500">
                Gebundene Quellversion {hypothesis.source_lesson_version_id}
              </p>
              <fieldset
                disabled={actionsDisabled}
                className="min-w-0 border-0 p-0"
                onClickCapture={(event) => {
                  if (!actionsAreDisabled()) return;
                  if (event.target instanceof Element && event.target.closest('button')) {
                    event.preventDefault();
                    event.stopPropagation();
                  }
                }}
                onSubmitCapture={(event) => {
                  if (!actionsAreDisabled()) return;
                  event.preventDefault();
                  event.stopPropagation();
                }}
              >
                <HypothesisProposalPanel
                  hypothesisId={hypothesis.id}
                  onHypothesisChanged={() => reloadHypotheses(hypothesis.id)}
                />
              </fieldset>
            </article>
          ))}
        </div>
      ) : (
        <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
          <label className="block text-sm">
            <span className="text-slate-400">Titel</span>
            <input
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
              value={title}
              onChange={(event) => {
                if (operation.current !== null || !ready || actionsAreDisabled()) return;
                draft.current.title = event.target.value;
                reportNavigationState();
                setTitle(event.target.value);
              }}
              required
              disabled={saving || !ready || actionsDisabled}
              maxLength={240}
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate-400">Hypothese</span>
            <textarea
              className="mt-1 min-h-28 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
              value={statement}
              onChange={(event) => {
                if (operation.current !== null || !ready || actionsAreDisabled()) return;
                draft.current.statement = event.target.value;
                reportNavigationState();
                setStatement(event.target.value);
              }}
              required
              disabled={saving || !ready || actionsDisabled}
            />
          </label>
          <button
            type="submit"
            disabled={saving || !ready || actionsDisabled}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            {saving ? 'Wird übergeben …' : 'Hypothese für FT-013 anlegen'}
          </button>
        </form>
      )}
    </section>
  );
}
