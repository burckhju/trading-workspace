import { useEffect, useState } from 'react';
import { lessonReviewClient, type SourceInspection } from '../services/lessonReviewClient';

type Props = {
  evidenceId: string;
  showSourceIdentity?: boolean;
  expectedSource?: { type: string; versionId: string };
};

const currentnessLabel: Record<string, string> = {
  CURRENT: 'Aktuell',
  STALE: 'Veraltet – erneute Prüfung nötig',
  SUPERSEDED: 'Durch neuere Version ersetzt',
  UNKNOWN: 'Ungeklärt',
};

export function EvidenceSourceStatus(props: Props) {
  const { evidenceId, expectedSource } = props;
  return (
    <EvidenceSourceStatusContext
      key={`${evidenceId}:${expectedSource?.type ?? ''}:${expectedSource?.versionId ?? ''}`}
      {...props}
    />
  );
}

function EvidenceSourceStatusContext({
  evidenceId,
  showSourceIdentity = true,
  expectedSource,
}: Props) {
  const expectedType = expectedSource?.type;
  const expectedVersionId = expectedSource?.versionId;
  const [result, setResult] = useState<SourceInspection | null>(null);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setResult(null);
    setError(false);
    void lessonReviewClient
      .source(evidenceId, controller.signal)
      .then((value) => {
        if (
          value.evidence_id !== evidenceId ||
          !value.source_version_id ||
          (expectedType !== undefined &&
            (value.source_type !== expectedType || value.source_version_id !== expectedVersionId))
        ) {
          throw new Error('Source inspection does not match the requested evidence');
        }
        if (!controller.signal.aborted) setResult(value);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      });
    return () => controller.abort();
  }, [evidenceId, expectedType, expectedVersionId, retry]);
  if (error)
    return (
      <p role="alert">
        Quellenprüfung nicht verfügbar.{' '}
        <button type="button" onClick={() => setRetry((n) => n + 1)}>
          Quellenprüfung erneut laden
        </button>
      </p>
    );
  if (!result) return <p>Quellenstand wird geprüft …</p>;
  return (
    <div className="space-y-1 break-words text-sm text-slate-400">
      {showSourceIdentity && (
        <>
          <p>Quellentyp: {result.source_type}</p>
          <p className="break-all">Konkrete Quellversion: {result.source_version_id}</p>
        </>
      )}
      <p>Quellversion jetzt: {currentnessLabel[result.source_currentness] ?? 'Ungeklärt'}</p>
      {result.review_currentness !== null && (
        <p>Review-Quelle jetzt: {currentnessLabel[result.review_currentness] ?? 'Ungeklärt'}</p>
      )}
      {result.superseded_by_version_id && (
        <p className="break-all">
          Spätere Quellversion: {result.superseded_by_version_id} (nicht automatisch übernommen)
        </p>
      )}
      <p>Geprüft: {result.checked_at}. Heutiger Lesestand, keine Aussage über damaliges Wissen.</p>
      <details className="text-xs">
        <summary>Technische Statuskennungen</summary>
        <p>
          Quellversion: {result.source_currentness}
          {result.review_currentness !== null
            ? ` · Reviewquelle: ${result.review_currentness}`
            : ''}
        </p>
      </details>
    </div>
  );
}
