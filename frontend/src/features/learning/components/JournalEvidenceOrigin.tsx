import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import { journalClient, type JournalHistory } from '../services/journalClient';
import type { EvidenceSummary } from '../services/lessonReviewClient';
import { EvidenceSourceStatus } from './EvidenceSourceStatus';

function sourceVersionId(source: EvidenceSummary['source']): string | undefined {
  switch (source.type) {
    case 'TRADE_JOURNAL_VERSION':
      return source.trade_journal_version_id;
    case 'FT011':
      return source.exit_review_version_id;
    case 'EXTERNAL_OBSERVATION':
      return source.external_observation_version_id;
    case 'EXTERNAL_OBSERVATION_JOURNAL_VERSION':
      return source.external_observation_journal_version_id;
    default:
      return undefined;
  }
}

export function JournalEvidenceOrigin({ evidenceId }: { evidenceId: string }) {
  return <EvidenceOriginContext key={evidenceId} evidenceId={evidenceId} />;
}

function EvidenceOriginContext({ evidenceId }: { evidenceId: string }) {
  const [history, setHistory] = useState<JournalHistory | null>(null);
  const [source, setSource] = useState<EvidenceSummary | null>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setHistory(null);
    setSource(null);
    setState('loading');
    void (async () => {
      try {
        const evidence = await requestJson<EvidenceSummary>(
          `${environment.apiBaseUrl}/api/v1/learning/learning-evidence/${evidenceId}`,
          { signal: controller.signal },
        );
        if (controller.signal.aborted) return;
        const sourceId = sourceVersionId(evidence.source);
        if (
          evidence.evidence_id !== evidenceId ||
          evidence.source_type !== evidence.source.type ||
          !sourceId
        ) {
          throw new Error('Evidence source identity was not returned');
        }
        const journal =
          evidence.source.type === 'TRADE_JOURNAL_VERSION'
            ? await journalClient.version(sourceId, controller.signal)
            : null;
        if (journal) {
          const exact = journal.versions.filter((entry) => entry.version.id === sourceId);
          if (
            !journal.trade_id ||
            !journal.journal_id ||
            exact.length !== 1 ||
            exact[0].version.trade_journal_id !== journal.journal_id ||
            exact[0].version.status !== 'FINALIZED' ||
            exact[0].learning_evidence_id !== evidenceId
          ) {
            throw new Error('Exact materialized journal source version was not returned');
          }
        } else if (evidence.source.type === 'TRADE_JOURNAL_VERSION') {
          throw new Error('Exact journal source was not returned');
        }
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
  if (state === 'error' || !source)
    return (
      <div role="alert">
        Quellenherkunft nicht geladen oder nicht eindeutig zugeordnet.
        <button type="button" onClick={() => setRetry((n) => n + 1)}>
          Quellenherkunft erneut laden
        </button>
      </div>
    );
  const sourceId = sourceVersionId(source.source)!;
  const entry = history?.versions.find((item) => item.version.id === sourceId);
  return (
    <div className="mt-3 space-y-2 break-words text-sm">
      <p>Quellentyp: {source.source.type}</p>
      <p className="break-all">Konkrete Quellversion: {sourceId}</p>
      <p>Materialisiert: {source.created_at}</p>
      {entry && history && (
        <>
          <p>
            Persönliches Trade-Journal · Version {entry.version.version} · finalisiert:{' '}
            {entry.version.finalized_at ?? 'Zeitpunkt unbekannt'}
          </p>
          <Link
            className="text-emerald-300 underline"
            to={`/post-trade?${new URLSearchParams({
              trade_id: history.trade_id,
              journal_version_id: entry.version.id,
            })}`}
          >
            Genau diese Journalversion öffnen
          </Link>
          <details className="text-xs text-slate-400">
            <summary>Gespeicherte Journalherkunft</summary>
            <p className="break-all">
              ExitReviewVersion:{' '}
              {entry.version.source_exit_review_version_id ?? 'Unbekannt (historischer Altstand)'}
            </p>
            <p>Erfasst: {entry.version.created_at}</p>
            <p className="break-all">
              Finalisiert durch: {entry.version.finalized_by ?? 'Unbekannt'}
            </p>
          </details>
        </>
      )}
      <EvidenceSourceStatus
        evidenceId={evidenceId}
        showSourceIdentity={false}
        expectedSource={{ type: source.source.type, versionId: sourceId }}
      />
      <p className="text-xs text-slate-400">
        Die heutige Quellenprüfung ändert diese gespeicherte Lesson-Version nicht.
      </p>
    </div>
  );
}
