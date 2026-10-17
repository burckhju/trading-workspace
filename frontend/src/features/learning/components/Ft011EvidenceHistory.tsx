import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { ft011MaterializationClient } from '../services/materializationClient';
import type { Ft011EvidenceHistoryItem } from '../types/materialization';

export function Ft011EvidenceHistory({
  tradeId,
  refreshVersion = 0,
}: {
  tradeId: string;
  refreshVersion?: number;
}) {
  const [items, setItems] = useState<Ft011EvidenceHistoryItem[] | null>(null);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setItems(null);
    setError(false);
    void ft011MaterializationClient
      .history(tradeId, controller.signal)
      .then((values) => {
        if (!controller.signal.aborted) setItems(values);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      });
    return () => controller.abort();
  }, [tradeId, refreshVersion, retry]);
  return (
    <section
      aria-label="Bisherige Review-Evidence"
      className="space-y-4 rounded-xl border border-slate-700 p-5"
    >
      <h2 className="text-lg font-semibold">Bisherige Review-Evidence</h2>
      <p className="text-sm text-slate-400">
        Frühere Übergaben bleiben sichtbar, auch wenn heute keine neue Übergabe möglich ist.
        Quellenprüfung und gespeicherter Reviewstatus sind getrennt. Eine frühere Übergabe ist keine
        heutige Freigabe und kein realisierter Gewinn.
      </p>
      <button
        type="button"
        className="rounded border border-slate-600 px-3 py-2 text-sm"
        onClick={() => setRetry((value) => value + 1)}
      >
        Evidence-Historie neu laden
      </button>
      {error ? (
        <p role="alert">
          Evidence-Historie konnte nicht geladen werden. Das bedeutet nicht, dass keine frühere
          Evidence existiert.
        </p>
      ) : items === null ? (
        <p role="status">Evidence-Historie wird geladen …</p>
      ) : items.length === 0 ? (
        <p>Noch keine Review-Evidence für diesen Trade gespeichert.</p>
      ) : (
        items.map((item) => (
          <article
            key={item.learning_evidence_id}
            className="space-y-3 rounded border border-slate-700 p-4"
          >
            <h3 className="font-semibold">
              Review-Evidence · Review-Version {item.review_version ?? 'unbekannt'}
            </h3>
            <p>
              Quellenprüfung: {item.source_currentness} · geprüft {item.checked_at}
            </p>
            <p className="text-sm">
              Übergeben: {item.materialized_at} · Typ {item.evidence_type}
            </p>
            {item.superseded_by_version_id && (
              <p className="break-all text-sm text-amber-300">
                Späterer Reviewstand: {item.superseded_by_version_id}. Diese Evidence bleibt an der
                ursprünglichen Version.
              </p>
            )}
            <details className="text-sm text-slate-400">
              <summary className="cursor-pointer">
                Genaue Herkunft und gespeicherten Reviewstatus anzeigen
              </summary>
              <div className="mt-2 space-y-1 break-all">
                <p>LearningEvidence: {item.learning_evidence_id}</p>
                <p>Trade: {item.trade_id}</p>
                <p>Nachbeobachtung: {item.post_trade_observation_id}</p>
                <p>ExitReview: {item.exit_review_id}</p>
                <p>ExitReviewVersion: {item.exit_review_version_id}</p>
                <p>
                  Gespeichert: {item.review_status ?? 'UNKNOWN'} ·{' '}
                  {item.stored_review_currentness ?? 'UNKNOWN'}
                </p>
                <p>Die heutige Quellenprüfung behauptet keine damalige Datenkenntnis.</p>
              </div>
            </details>
            <h4 className="text-sm font-medium">Lesson-Verknüpfungen dieser Evidence</h4>
            {item.lesson_links.length === 0 ? (
              <p className="text-sm">Keine gespeicherten Lesson-Verknüpfungen.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {item.lesson_links.map((link) => (
                  <li key={link.link_id}>
                    <Link
                      className="text-emerald-300 underline"
                      to={`/lessons/${link.lesson_id}?lesson_version_id=${link.lesson_version_id}#lesson-history`}
                    >
                      {link.lesson_title} · Version {link.lesson_version} · {link.relation}
                      {link.is_current_version ? ' · aktueller Lesson-Stand' : ' · historisch'}
                    </Link>
                    <p className="break-all text-xs text-slate-400">
                      LessonVersion: {link.lesson_version_id} · Link: {link.link_id}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </article>
        ))
      )}
    </section>
  );
}
