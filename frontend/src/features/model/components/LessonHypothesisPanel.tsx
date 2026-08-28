import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';

import { ErrorNotice, LoadingNotice } from '../../market/components/ApiFeedback';
import { lessonHypothesisClient } from '../services/lessonHypothesisClient';
import type { LessonHypothesis } from '../types/lessonHypothesis';

interface LessonHypothesisPanelProps {
  lessonVersionId: string;
}

export function LessonHypothesisPanel({ lessonVersionId }: LessonHypothesisPanelProps) {
  const [hypotheses, setHypotheses] = useState<LessonHypothesis[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [title, setTitle] = useState('');
  const [statement, setStatement] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    lessonHypothesisClient
      .listForLessonVersion(lessonVersionId, controller.signal)
      .then(setHypotheses)
      .catch((nextError: unknown) => {
        if (!controller.signal.aborted) setError(nextError);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [lessonVersionId]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const created = await lessonHypothesisClient.createFromLessonVersion(lessonVersionId, {
        title,
        statement,
      });
      setHypotheses((current) => [...current, created]);
      setTitle('');
      setStatement('');
    } catch (nextError: unknown) {
      setError(nextError);
    } finally {
      setSaving(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    void submit(event);
  }

  if (loading) return <LoadingNotice label="FT-013-Hypothesen werden geladen …" />;

  return (
    <section className="rounded-xl border border-slate-800 p-5">
      <h2 className="font-semibold">FT-013 Hypothesen</h2>
      <p className="mt-2 text-sm text-slate-400">
        Eine Hypothese ist eine explizite Interpretation dieser Lesson-Version. Sie aktiviert keine
        Modelländerung und startet keine Validierung automatisch.
      </p>

      {error !== null && (
        <div className="mt-4">
          <ErrorNotice error={error} />
        </div>
      )}

      {hypotheses.length > 0 ? (
        <div className="mt-4 space-y-3">
          <p className="text-sm font-medium text-emerald-300">Bereits an FT-013 übergeben</p>
          {hypotheses.map((hypothesis) => (
            <article key={hypothesis.id} className="rounded-lg border border-slate-800 p-4">
              <div className="flex items-center justify-between gap-4">
                <h3 className="font-medium">{hypothesis.title}</h3>
                <span className="text-xs text-slate-400">{hypothesis.status}</span>
              </div>
              <p className="mt-2 whitespace-pre-wrap text-sm text-slate-300">
                {hypothesis.statement}
              </p>
              <p className="mt-2 break-all text-xs text-slate-500">{hypothesis.id}</p>
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
              onChange={(event) => setTitle(event.target.value)}
              required
              maxLength={240}
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate-400">Hypothese</span>
            <textarea
              className="mt-1 min-h-28 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
              value={statement}
              onChange={(event) => setStatement(event.target.value)}
              required
            />
          </label>
          <button
            type="submit"
            disabled={saving}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            {saving ? 'Wird übergeben …' : 'Hypothese für FT-013 anlegen'}
          </button>
        </form>
      )}
    </section>
  );
}
