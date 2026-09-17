import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';

import { lessonDraftClient } from '../services/lessonDraftClient';

interface LessonDraftFromEvidenceProps {
  learningEvidenceId: string;
  disabled?: boolean;
  onCreated?: (lessonId: string) => void;
}

function lessonReference(id: string): string {
  return `LS-${id.slice(0, 8).toUpperCase()}`;
}

export function LessonDraftFromEvidence({
  learningEvidenceId,
  disabled = false,
  onCreated,
}: LessonDraftFromEvidenceProps) {
  const [title, setTitle] = useState('');
  const [mainCategory, setMainCategory] = useState('');
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdLessonId, setCreatedLessonId] = useState<string | null>(null);

  const canSubmit =
    !disabled &&
    !submitting &&
    title.trim() !== '' &&
    mainCategory.trim() !== '' &&
    content.trim() !== '';

  async function submit() {
    if (!canSubmit) return;

    setSubmitting(true);
    setError(null);

    try {
      const result = await lessonDraftClient.createFromEvidence(learningEvidenceId, {
        title: title.trim(),
        main_category: mainCategory.trim(),
        content: content.trim(),
        tags: [],
      });
      setCreatedLessonId(result.lesson_id);
      onCreated?.(result.lesson_id);
    } catch (nextError: unknown) {
      setError(
        nextError instanceof Error ? nextError.message : 'Lesson konnte nicht angelegt werden.',
      );
    } finally {
      setSubmitting(false);
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

      {createdLessonId ? (
        <div role="status" className="mt-4 rounded-lg border border-emerald-800 p-4">
          <p className="text-sm text-emerald-300">
            Lesson {lessonReference(createdLessonId)} wurde angelegt.
          </p>
          <Link
            to={`/lessons/${createdLessonId}`}
            className="mt-3 inline-block rounded-lg border border-emerald-700 px-4 py-2 text-sm text-emerald-300"
          >
            Lesson öffnen
          </Link>
          <details className="mt-3 text-xs text-slate-500">
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
              onChange={(event) => setTitle(event.target.value)}
              disabled={disabled || submitting}
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            />
          </label>

          <label className="block text-sm">
            <span className="text-slate-400">Kategorie</span>
            <input
              aria-label="Lesson-Kategorie"
              value={mainCategory}
              onChange={(event) => setMainCategory(event.target.value)}
              disabled={disabled || submitting}
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            />
          </label>

          <label className="block text-sm">
            <span className="text-slate-400">Lesson-Inhalt</span>
            <textarea
              aria-label="Lesson-Inhalt"
              value={content}
              onChange={(event) => setContent(event.target.value)}
              disabled={disabled || submitting}
              className="mt-1 min-h-28 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            />
          </label>

          {error && <p className="text-sm text-red-300">{error}</p>}

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
