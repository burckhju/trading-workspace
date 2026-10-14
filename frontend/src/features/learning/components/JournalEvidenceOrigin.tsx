import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import { journalClient, type JournalHistory } from '../services/journalClient';
import { JournalVersionSource } from './TradeJournalPanel';

type Source = {
  source: { type: string; trade_journal_version_id?: string };
  created_at: string;
};
export function JournalEvidenceOrigin({ evidenceId }: { evidenceId: string }) {
  const [history, setHistory] = useState<JournalHistory | null>(null);
  const [source, setSource] = useState<Source | null>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setHistory(null);
    setSource(null);
    setState('loading');
    void (async () => {
      try {
        const evidence = await requestJson<Source>(
          `${environment.apiBaseUrl}/api/v1/learning/learning-evidence/${evidenceId}`,
          { signal: controller.signal },
        );
        const sourceId = evidence.source.trade_journal_version_id;
        const journal =
          evidence.source.type === 'TRADE_JOURNAL_VERSION' && sourceId
            ? await journalClient.version(sourceId, controller.signal)
            : null;
        if (!controller.signal.aborted) {
          setSource(evidence);
          setHistory(journal);
          setState('ready');
        }
      } catch {
        if (!controller.signal.aborted) setState('error');
      }
    })();
    return () => controller.abort();
  }, [evidenceId, retry]);
  if (state === 'loading') return <p>Quellenherkunft wird geladen …</p>;
  if (state === 'error')
    return (
      <div role="alert">
        Quellenherkunft nicht geladen.
        <button onClick={() => setRetry((n) => n + 1)}>Quellenherkunft erneut laden</button>
      </div>
    );
  const entry = history?.versions[0];
  return (
    <div className="mt-3 space-y-2">
      <p>
        Quellentyp: {source?.source.type} · Materialisiert: {source?.created_at}
      </p>
      {entry && (
        <>
          <JournalVersionSource entry={entry} />
          <p>Die heutige Quellenprüfung ändert diese gespeicherte Lesson-Version nicht.</p>
          <dl>
            <dt>Was lief gut?</dt>
            <dd className="whitespace-pre-wrap">
              {entry.version.what_went_well ?? 'Nicht ausgefüllt'}
            </dd>
            <dt>Was würde ich anders machen?</dt>
            <dd className="whitespace-pre-wrap">
              {entry.version.would_do_differently ?? 'Nicht ausgefüllt'}
            </dd>
            <dt>Weitere Notizen</dt>
            <dd className="whitespace-pre-wrap">
              {entry.version.additional_notes ?? 'Nicht ausgefüllt'}
            </dd>
          </dl>
          <Link
            className="text-emerald-300 underline"
            to={`/post-trade?trade_id=${history.trade_id}&journal_version_id=${entry.version.id}`}
          >
            Genau diese Journalversion öffnen
          </Link>
        </>
      )}
    </div>
  );
}
