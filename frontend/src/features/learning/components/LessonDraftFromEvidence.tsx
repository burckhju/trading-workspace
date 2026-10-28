import { FormEvent, useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import { MarketApiError } from '../../market/services/http';
import { lessonDraftClient } from '../services/lessonDraftClient';

interface LessonDraftFromEvidenceProps {
  learningEvidenceId: string;
  disabled?: boolean;
  onCreated?: (lessonId: string) => void;
  onNavigationStateChange?: (state: { dirty: boolean; pending: boolean }) => void;
  discardVersion?: number;
  isContextPending?: () => boolean;
}

export function LessonDraftFromEvidence({
  learningEvidenceId,
  disabled = false,
  onCreated,
  onNavigationStateChange,
  discardVersion = 0,
  isContextPending,
}: LessonDraftFromEvidenceProps) {
  const [title, setTitle] = useState('');
  const [mainCategory, setMainCategory] = useState('');
  const [content, setContent] = useState('');
  const [boundEvidenceId, setBoundEvidenceId] = useState(learningEvidenceId);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uncertain, setUncertain] = useState(false);
  const [createdLessonId, setCreatedLessonId] = useState<string | null>(null);
  const mounted = useRef(false);
  const pending = useRef(false);
  const dirty = useRef(false);
  const unknownOutcome = useRef(false);
  const completed = useRef(false);
  const protectedContextChange = useRef(false);
  const sequence = useRef(0);
  const discardSeen = useRef(discardVersion);
  const reporter = useRef(onNavigationStateChange);
  reporter.current = onNavigationStateChange;
  const contextPending = isContextPending?.() ?? false;

  const report = useCallback(() => {
    reporter.current?.({
      dirty: dirty.current || unknownOutcome.current,
      pending: pending.current,
    });
  }, []);

  useLayoutEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      sequence.current += 1;
      reporter.current?.({ dirty: false, pending: false });
    };
  }, []);

  const reset = useCallback(
    (nextEvidenceId: string) => {
      if (pending.current || isContextPending?.()) return;
      sequence.current += 1;
      setBoundEvidenceId(nextEvidenceId);
      setTitle('');
      setMainCategory('');
      setContent('');
      setCreatedLessonId(null);
      setError(null);
      setUncertain(false);
      dirty.current = false;
      unknownOutcome.current = false;
      completed.current = false;
      protectedContextChange.current = false;
      report();
    },
    [report, isContextPending],
  );

  useEffect(() => {
    if (discardSeen.current === discardVersion) return;
    discardSeen.current = discardVersion;
    reset(learningEvidenceId);
    // A discard is a deliberate parent decision, never a readback side effect.
  }, [discardVersion, learningEvidenceId, reset]);

  useEffect(() => {
    if (learningEvidenceId !== boundEvidenceId) {
      if (dirty.current || pending.current || unknownOutcome.current)
        protectedContextChange.current = true;
      if (!protectedContextChange.current) reset(learningEvidenceId);
    }
    // Dirty forms retain their exact source until the explicit action below.
  }, [learningEvidenceId, boundEvidenceId, submitting, contextPending, reset]);

  const contextChanged = learningEvidenceId !== boundEvidenceId;
  const canSubmit =
    !disabled &&
    !submitting &&
    !uncertain &&
    !contextChanged &&
    title.trim() !== '' &&
    mainCategory.trim() !== '' &&
    content.trim() !== '';

  async function submit() {
    if (!canSubmit || pending.current || unknownOutcome.current || completed.current) return;

    pending.current = true;
    report();
    const attempt = ++sequence.current;
    const source = boundEvidenceId;
    setSubmitting(true);
    setError(null);

    try {
      const result = await lessonDraftClient.createFromEvidence(source, {
        title: title.trim(),
        main_category: mainCategory.trim(),
        content: content.trim(),
        tags: [],
      });
      if (!mounted.current || attempt !== sequence.current) return;
      completed.current = true;
      dirty.current = false;
      pending.current = false;
      report();
      setCreatedLessonId(result.lesson_id);
      onCreated?.(result.lesson_id);
    } catch (nextError: unknown) {
      if (!mounted.current || attempt !== sequence.current) return;
      const uncertainResult = !(nextError instanceof MarketApiError) || nextError.status >= 500;
      unknownOutcome.current = uncertainResult;
      setUncertain(uncertainResult);
      setError(
        uncertainResult
          ? 'Der Ausgang der Lesson-Erstellung ist unklar. Bitte die Lesson-Verweise neu lesen; dieser POST kann nicht idempotent wiederholt werden.'
          : nextError.message,
      );
    } finally {
      if (mounted.current && attempt === sequence.current) {
        pending.current = false;
        report();
        setSubmitting(false);
      }
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submit();
  }

  return (
    <section className="mt-5 rounded-lg border border-slate-700 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">Interpretation</p>
      <h3 className="mt-1 font-semibold">Lesson aus Evidence ableiten</h3>
      <p className="mt-2 text-sm text-slate-400">
        Die Evidence bleibt unverändert. Titel, Kategorie und Inhalt sind eine explizite fachliche
        Interpretation und werden nicht automatisch erzeugt.
      </p>
      {contextChanged && (
        <div role="alert" className="mt-3 space-y-2 text-sm text-amber-200">
          <p>
            Die Evidence hat sich geändert. Die Eingaben bleiben an Evidence {boundEvidenceId}
            gebunden. Die neue Evidence wird erst nach bewusstem Verwerfen geöffnet.
          </p>
          <button
            type="button"
            disabled={disabled || submitting || contextPending}
            onClick={() => reset(learningEvidenceId)}
            className="rounded-lg border border-amber-700 px-3 py-2 disabled:opacity-50"
          >
            Eingaben verwerfen und neue Evidence öffnen
          </button>
        </div>
      )}

      {createdLessonId ? (
        <div className="mt-4 rounded-lg border border-emerald-800 p-4">
          <p role="status" className="text-sm text-emerald-300">
            Lesson angelegt: LS-{createdLessonId.slice(0, 8).toUpperCase()}
          </p>
          <Link
            to={`/lessons/${encodeURIComponent(createdLessonId)}`}
            className="mt-3 inline-block rounded-lg border border-emerald-700 px-4 py-2 text-sm text-emerald-300"
          >
            Lesson öffnen
          </Link>
          <details className="mt-3 text-xs text-slate-400">
            <summary className="cursor-pointer">Technische Lesson-ID anzeigen</summary>
            <p className="mt-2 break-all">{createdLessonId}</p>
          </details>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <label className="block text-sm">
            <span className="text-slate-400">Titel</span>
            <input
              aria-label="Lesson-Titel"
              value={title}
              onChange={(event) => {
                dirty.current = Boolean(event.target.value || mainCategory || content);
                report();
                setTitle(event.target.value);
              }}
              disabled={disabled || submitting}
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            />
          </label>

          <label className="block text-sm">
            <span className="text-slate-400">Kategorie</span>
            <input
              aria-label="Lesson-Kategorie"
              value={mainCategory}
              onChange={(event) => {
                dirty.current = Boolean(title || event.target.value || content);
                report();
                setMainCategory(event.target.value);
              }}
              disabled={disabled || submitting}
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            />
          </label>

          <label className="block text-sm">
            <span className="text-slate-400">Lesson-Inhalt</span>
            <textarea
              aria-label="Lesson-Inhalt"
              value={content}
              onChange={(event) => {
                dirty.current = Boolean(title || mainCategory || event.target.value);
                report();
                setContent(event.target.value);
              }}
              disabled={disabled || submitting}
              className="mt-1 min-h-28 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            />
          </label>

          {error && (
            <p role="alert" className="text-sm text-red-300">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded-lg border border-emerald-700 px-4 py-2 disabled:opacity-50"
          >
            Lesson anlegen
          </button>
        </form>
      )}
    </section>
  );
}
