import { useEffect, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { EvidenceSourceStatus } from '../components/EvidenceSourceStatus';
import {
  lessonListClient,
  type LessonListItem,
  type LessonListPageResponse,
} from '../services/lessonListClient';
import {
  lessonListDetailLink,
  lessonListPath,
  lessonStateLabel,
  previousLessonListCursor,
  rememberLessonListCursor,
  type LessonListPurpose,
} from '../services/lessonNavigation';
import { lessonReviewClient, type LessonVersionSnapshot } from '../services/lessonReviewClient';

const linkClass =
  'rounded text-sky-300 underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-300';

export function LessonListPage({ purpose = 'lessons' }: { purpose?: LessonListPurpose }) {
  const [params] = useSearchParams();
  const cursors = params.getAll('cursor');
  const cursor = cursors[0] ?? null;
  if (cursors.length > 1 || cursor === '') {
    return (
      <section role="alert" className="space-y-3 rounded-xl border border-amber-700 p-5">
        <h1 className="text-xl font-semibold">Listenausschnitt nicht eindeutig</h1>
        <p>
          Der Seitenverweis ist leer oder mehrfach angegeben. Der angeforderte Ausschnitt wurde
          nicht ersetzt.
        </p>
        <Link className={linkClass} to={lessonListPath(purpose)}>
          Zur ersten Seite
        </Link>
      </section>
    );
  }
  return <LessonListContent key={`${purpose}:${cursor ?? ''}`} purpose={purpose} cursor={cursor} />;
}

function LessonListContent({
  purpose,
  cursor,
}: {
  purpose: LessonListPurpose;
  cursor: string | null;
}) {
  const location = useLocation();
  const [page, setPage] = useState<LessonListPageResponse | null>(null);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  const models = purpose === 'models';
  useEffect(() => {
    const controller = new AbortController();
    setPage(null);
    setError(false);
    void lessonListClient
      .list(cursor, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setPage(result);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      });
    return () => controller.abort();
  }, [cursor, retry]);
  const listState: unknown = location.state;
  const previousValue =
    listState && typeof listState === 'object' && 'previousCursor' in listState
      ? listState.previousCursor
      : undefined;
  const previous =
    previousValue === null ||
    (typeof previousValue === 'string' && previousValue.length > 0 && previousValue !== cursor)
      ? previousValue
      : previousLessonListCursor(purpose, cursor);
  const pageHref = (value: string | null) =>
    `${lessonListPath(purpose)}${value === null ? '' : `?${new URLSearchParams({ cursor: value })}`}`;
  return (
    <div className="min-w-0 space-y-6">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-wide text-sky-400">Lessons Learned</p>
        <h1 className="text-2xl font-semibold">{models ? 'Modellverbesserung' : 'Erkenntnisse'}</h1>
        <p className="max-w-3xl text-sm text-slate-300">
          {models
            ? 'Wählen Sie eine konkrete Erkenntnisversion als Ausgangspunkt für Hypothesen, Änderungsvorschläge und deren kontrollierte Prüfung.'
            : 'Prüfen Sie abgeleitete Erkenntnisse, ihre Versionen und die zugrunde liegenden Quellen.'}
        </p>
        {models && (
          <p className="max-w-3xl text-sm text-slate-400">
            Die Modellarbeit bleibt an einer Erkenntnisversion gebunden. Freigabe und Aktivierung
            bleiben getrennte Schritte im vorhandenen Prüfverfahren.
          </p>
        )}
      </header>
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
        <p className="text-slate-400">
          {cursor ? 'Weiterer Listenausschnitt' : 'Erste Seite'} · bis zu 25 Erkenntnisse pro Seite
        </p>
        <Link className={linkClass} to="/learning">
          Zum Trade-basierten Lernen
        </Link>
      </div>
      {!page && !error && (
        <p role="status" className="rounded-xl border border-slate-800 p-5">
          Erkenntnisse werden geladen …
        </p>
      )}
      {error && (
        <section role="alert" className="space-y-3 rounded-xl border border-amber-700 p-5">
          <h2 className="font-semibold">Erkenntnisse nicht verfügbar</h2>
          <p>
            Der angeforderte Listenausschnitt konnte nicht geladen werden. Daraus lässt sich keine
            Aussage über vorhandene Erkenntnisse ableiten.
          </p>
          <button
            type="button"
            onClick={() => setRetry((value) => value + 1)}
            className={linkClass}
          >
            Erneut laden
          </button>
        </section>
      )}
      {page && page.items.length === 0 && (
        <section className="space-y-3 rounded-xl border border-slate-700 p-5">
          <h2 className="font-semibold">
            {cursor ? 'Keine weiteren Erkenntnisse' : 'Noch keine Erkenntnisse vorhanden'}
          </h2>
          <p className="text-sm text-slate-400">
            Erkenntnisse werden aus freigegebenen Review- oder Journalquellen bewusst abgeleitet.
            Importierte Beobachtungen bleiben zunächst eigenständige Quellen.
          </p>
          <Link className={linkClass} to="/learning">
            Nachbeobachtung und Exit Review öffnen
          </Link>
        </section>
      )}
      {page && page.items.length > 0 && (
        <>
          <p className="text-sm text-slate-400">
            Der Status beschreibt die Interpretation. Den heutigen Quellenstand können Sie je
            Erkenntnis gesondert prüfen.
          </p>
          <ul
            aria-label={
              models ? 'Erkenntnisversionen für Modellverbesserung' : 'Vorhandene Erkenntnisse'
            }
            className="space-y-4"
          >
            {page.items.map((item) => (
              <LessonListRow
                key={`${item.lesson_id}:${item.current_version_id}`}
                item={item}
                purpose={purpose}
                cursor={cursor}
              />
            ))}
          </ul>
        </>
      )}
      <nav
        aria-label="Erkenntnisliste blättern"
        className="flex flex-wrap gap-4 border-t border-slate-800 pt-4 text-sm"
      >
        {cursor !== null && (
          <Link className={linkClass} to={pageHref(null)}>
            Zur ersten Seite
          </Link>
        )}
        {cursor !== null && previous !== undefined && (
          <Link className={linkClass} to={pageHref(previous)}>
            Vorige Seite
          </Link>
        )}
        {page?.next_cursor && (
          <Link
            className={linkClass}
            to={pageHref(page.next_cursor)}
            state={{ previousCursor: cursor }}
            onClick={() => rememberLessonListCursor(purpose, page.next_cursor!, cursor)}
          >
            Weitere Erkenntnisse
          </Link>
        )}
        {page && !page.next_cursor && page.items.length > 0 && (
          <span className="text-slate-400">Ende der Liste</span>
        )}
      </nav>
    </div>
  );
}

function LessonListRow({
  item,
  purpose,
  cursor,
}: {
  item: LessonListItem;
  purpose: LessonListPurpose;
  cursor: string | null;
}) {
  const [inspectSources, setInspectSources] = useState(false);
  const href = lessonListDetailLink(item.lesson_id, item.current_version_id, purpose, cursor);
  return (
    <li className="min-w-0 space-y-4 rounded-xl border border-slate-700 bg-slate-900/30 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <h2 className="break-words text-lg font-semibold">
            <Link className={linkClass} to={href}>
              {item.title}
            </Link>
          </h2>
          <p className="text-sm text-slate-400">
            Version {item.version} · {item.main_category}
          </p>
        </div>
        <span
          className={`rounded-full border px-3 py-1 text-xs ${item.current_state === 'REVIEW_RECOMMENDED' ? 'border-amber-700 text-amber-200' : 'border-slate-600 text-slate-300'}`}
        >
          {lessonStateLabel[item.current_state]}
        </span>
      </div>
      <p className="line-clamp-3 whitespace-pre-wrap break-words text-sm text-slate-300">
        {item.content}
      </p>
      <div className="flex flex-wrap gap-4 text-sm">
        <Link className={linkClass} to={href}>
          {purpose === 'models'
            ? 'Modellverbesserung zu dieser Version'
            : 'Erkenntnis und Historie öffnen'}
        </Link>
        {purpose === 'lessons' && (
          <Link className={linkClass} to={`${href.slice(0, href.indexOf('#'))}#model-improvement`}>
            Modellverbesserung
          </Link>
        )}
      </div>
      <details
        onToggle={(event) => {
          if (event.currentTarget.open) setInspectSources(true);
        }}
        className="text-sm"
      >
        <summary className="cursor-pointer rounded text-slate-300 focus-visible:outline-2 focus-visible:outline-sky-300">
          Quellenstatus für Version {item.version} prüfen
        </summary>
        {inspectSources && (
          <LessonListSources lessonId={item.lesson_id} versionId={item.current_version_id} />
        )}
      </details>
      <details className="text-xs text-slate-500">
        <summary className="cursor-pointer rounded focus-visible:outline-2 focus-visible:outline-sky-300">
          Versionsbeleg
        </summary>
        <div className="mt-2 space-y-1 break-all">
          <p>Erkenntnis-ID: {item.lesson_id}</p>
          <p>Versions-ID: {item.current_version_id}</p>
          <p>Version erfasst: {item.created_at}</p>
        </div>
      </details>
    </li>
  );
}

function LessonListSources({ lessonId, versionId }: { lessonId: string; versionId: string }) {
  const [snapshot, setSnapshot] = useState<LessonVersionSnapshot | null>(null);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setSnapshot(null);
    setError(false);
    void lessonReviewClient
      .context(lessonId, controller.signal)
      .then((context) => {
        const exact = context.history.filter((entry) => entry.version.id === versionId);
        if (
          context.lesson.id !== lessonId ||
          exact.length !== 1 ||
          exact[0].version.lesson_id !== lessonId ||
          exact[0].evidence_links.some((entry) => entry.lesson_version_id !== versionId)
        )
          throw new Error('Die genaue Erkenntnisversion fehlt.');
        if (!controller.signal.aborted) setSnapshot(exact[0]);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      });
    return () => controller.abort();
  }, [lessonId, versionId, retry]);
  if (error)
    return (
      <p role="alert" className="mt-3 text-amber-200">
        Quellen dieser Version nicht verfügbar.{' '}
        <button type="button" className={linkClass} onClick={() => setRetry((value) => value + 1)}>
          Quellen erneut laden
        </button>
      </p>
    );
  if (!snapshot)
    return (
      <p role="status" className="mt-3">
        Quellen dieser Version werden geladen …
      </p>
    );
  if (!snapshot.evidence_links.length)
    return <p className="mt-3 text-slate-400">Für diese Version sind keine Quellen verknüpft.</p>;
  return (
    <ul className="mt-3 space-y-3">
      {snapshot.evidence_links.map((entry, index) => (
        <li key={entry.id} className="rounded-lg border border-slate-800 p-3">
          <p className="mb-2 font-medium">
            Quelle {index + 1} ·{' '}
            {
              { SUPPORTS: 'Unterstützt', CONTRADICTS: 'Widerspricht', CONTEXTUAL: 'Kontext' }[
                entry.relation
              ]
            }
          </p>
          <EvidenceSourceStatus evidenceId={entry.learning_evidence_id} />
        </li>
      ))}
    </ul>
  );
}
