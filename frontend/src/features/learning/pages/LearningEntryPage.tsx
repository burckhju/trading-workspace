import { useState, type FormEvent, type ReactNode } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const linkClass =
  'inline-flex min-h-11 items-center rounded-lg border border-slate-600 px-4 py-2 text-sky-200 hover:border-sky-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-300';

export function LearningEntryPage({
  view,
  children,
}: {
  view: 'observation' | 'journal';
  children?: ReactNode;
}) {
  const navigate = useNavigate();
  const [tradeId, setTradeId] = useState('');
  const journal = view === 'journal';
  function openTrade(event: FormEvent) {
    event.preventDefault();
    if (!tradeId.trim()) return;
    const params = new URLSearchParams({ trade_id: tradeId.trim() });
    void navigate(`/post-trade?${params}#${journal ? 'trade-journal' : 'post-trade-review'}`);
  }
  return (
    <div className="min-w-0 space-y-6">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-wide text-sky-400">Lessons Learned</p>
        <h1 className="text-2xl font-semibold">
          {journal ? 'Journal' : 'Nachbeobachtung & Exit Review'}
        </h1>
        <p className="max-w-3xl text-sm text-slate-300">
          {journal
            ? 'Die persönliche Reflexion bleibt am abgeschlossenen Trade und seiner Reviewquelle. Öffnen Sie einen Trade, um Journalstände zu lesen oder einen zulässigen Entwurf zu bearbeiten.'
            : 'Beobachten Sie abgeschlossene Trades weiter und bewerten Sie die Exit-Entscheidung anhand ihrer Belege.'}
        </p>
      </header>
      <section
        aria-labelledby="learning-entry-title"
        className="space-y-4 rounded-xl border border-slate-700 bg-slate-900/40 p-5"
      >
        <h2 id="learning-entry-title" className="text-lg font-semibold">
          Mit einem Trade beginnen
        </h2>
        <p className="max-w-3xl text-sm text-slate-400">
          Die Vollabschlüsse im Zeitraum führen zu den vorhandenen Trade-Details. Dort bleiben
          Nachbeobachtung, Journal und abgeleitete Erkenntnisse miteinander verknüpft.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link className={linkClass} to="/performance/closed-trades">
            Vollabschlüsse im Zeitraum
          </Link>
          <Link className={linkClass} to="/lessons">
            Erkenntnisse ansehen
          </Link>
        </div>
        <p className="text-xs text-slate-400">
          Die Abschlussliste umfasst den bestehenden qualifizierten EUR-Bericht. Eine vollständige
          Liste aller Journale ist derzeit nicht verfügbar.
        </p>
      </section>
      {children}
      <section className="rounded-xl border border-slate-800 p-5">
        <h2 className="font-semibold">
          {journal ? 'Reflexion und Erkenntnis' : 'Beobachtung und Bewertung'}
        </h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          {journal
            ? 'Im Journal dokumentieren Sie Ihre Entscheidung. Eine Erkenntnis entsteht erst durch die bewusste Interpretation einer freigegebenen Quelle; sie wird separat geprüft und versioniert.'
            : 'Die Nachbeobachtung beschreibt den Kursverlauf nach dem tatsächlichen Verkauf. Der Exit Review bewertet Ihre Entscheidung. Ein Wechsel zwischen diesen Aufgaben löst keine neue Bewertung aus.'}
        </p>
      </section>
      <details className="rounded-xl border border-slate-800 p-5">
        <summary className="cursor-pointer rounded focus-visible:outline-2 focus-visible:outline-sky-300">
          Bekannte Trade-ID direkt öffnen
        </summary>
        <form onSubmit={openTrade} className="mt-4 space-y-3">
          <label htmlFor={`learning-trade-${view}`} className="block text-sm">
            Trade-ID
          </label>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              id={`learning-trade-${view}`}
              value={tradeId}
              onChange={(event) => setTradeId(event.target.value)}
              className="min-w-0 flex-1 rounded-lg border border-slate-600 bg-slate-950 p-3 focus-visible:outline-2 focus-visible:outline-sky-300"
            />
            <button
              type="submit"
              disabled={!tradeId.trim()}
              className={`${linkClass} disabled:opacity-50`}
            >
              Trade öffnen
            </button>
          </div>
        </form>
      </details>
    </div>
  );
}
