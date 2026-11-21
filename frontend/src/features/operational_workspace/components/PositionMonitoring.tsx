import { useCallback, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useHebeltraderQualificationSessions } from '../hooks/useHebeltraderQualificationSessions';
import { HebeltraderEvidenceCoverage } from './HebeltraderEvidenceCoverage';
import { HebeltraderLoss } from './HebeltraderLoss';
import { HebeltraderOriginalBid } from './HebeltraderOriginalBid';
import { HebeltraderSessions } from './HebeltraderSessions';
import { HebeltraderTargetHistory } from './HebeltraderTargetHistory';
import { IndicativeEntryObservation } from './IndicativeEntryObservation';

/** Host navigation contract only; the existing monitoring owners keep all facts and commands. */
export interface PositionMonitoringPending {
  isDirty: () => boolean;
  isBusy: () => boolean;
  discard: () => void;
}

export interface PositionMonitoringProps {
  tradeId: string;
  positionId: string;
  reloadToken?: number | string;
  productDetailsHref: string;
  onPendingChange?: (participant: PositionMonitoringPending | null) => void;
  isContextPending?: () => boolean;
}

/** Public composition for the canonical position detail. No duplicate positions or valuation read. */
export function PositionMonitoring({
  tradeId,
  positionId,
  reloadToken,
  productDetailsHref,
  onPendingChange,
  isContextPending,
}: PositionMonitoringProps) {
  const sessions = useHebeltraderQualificationSessions();
  const { getSnapshot, update } = sessions;
  const busyRef = useRef(false);
  const [busy, setBusy] = useState(false);
  const reportBusy = useCallback((next: boolean) => {
    busyRef.current = next;
    setBusy(next);
  }, []);
  const participant = useMemo<PositionMonitoringPending>(
    () => ({
      isDirty: () =>
        Object.values(getSnapshot()).some((session) => {
          if (session.command?.phase === 'UNKNOWN') return true;
          const savedReference =
            session.command?.phase === 'CONFIRMED'
              ? (session.command.payload.qualification?.evidence_reference ?? '')
              : '';
          return session.reference.trim() !== savedReference;
        }),
      isBusy: () =>
        busyRef.current ||
        Object.values(getSnapshot()).some((session) => session.command?.phase === 'PENDING'),
      discard: () => {
        for (const key of Object.keys(getSnapshot()))
          update(key, (session) => ({
            ...session,
            reference:
              session.command?.phase === 'CONFIRMED'
                ? (session.command.payload.qualification?.evidence_reference ?? '')
                : '',
            referenceBasisId: null,
          }));
      },
    }),
    [getSnapshot, update],
  );
  useLayoutEffect(() => {
    onPendingChange?.(participant);
  }, [onPendingChange, participant, sessions.values, busy]);
  useLayoutEffect(() => () => onPendingChange?.(null), [onPendingChange]);

  const context = { tradeId, positionId, reloadToken };
  return (
    <div className="min-w-0 space-y-5" aria-label="Überwachungsbelege der Position">
      <IndicativeEntryObservation {...context} />
      <section
        className="rounded-xl border border-slate-700 p-4"
        aria-label="Produkttermine und Ausstiegshandelsplatz"
      >
        <h3 className="font-semibold">Produkttermine und Ausstiegshandelsplatz</h3>
        <p className="mt-2 text-sm text-slate-300">
          Die dokumentierten Fristen und ihre Prüfgrenzen stehen bei den Positionshinweisen. Den
          festen Ausstiegshandelsplatz und die Produktbelege bearbeitest du am Optionsschein.
        </p>
        <Link
          className="mt-3 inline-block rounded text-sky-300 underline focus-visible:outline-2 focus-visible:outline-sky-300"
          to={productDetailsHref}
        >
          Produkttermine und Handelsplatz am Optionsschein prüfen
        </Link>
      </section>
      <details className="min-w-0 rounded-xl border border-slate-700 p-4">
        <summary className="cursor-pointer rounded font-semibold focus-visible:outline-2 focus-visible:outline-sky-300">
          Hebeltrader: Quellen, Voraussetzungen und Prüfungen
        </summary>
        <p className="my-3 text-sm text-slate-300">
          Originalbelege und begrenzte Regelprüfungen bleiben getrennte Aussagen. Vollständige
          Belege bestätigen keine vollständige oder aktive Überwachung.
        </p>
        <div className="min-w-0 space-y-4">
          <HebeltraderEvidenceCoverage {...context} />
          <HebeltraderTargetHistory
            {...context}
            qualificationSessions={sessions}
            onBusyChange={reportBusy}
            isContextPending={isContextPending}
          />
          <HebeltraderSessions {...context} />
          <HebeltraderOriginalBid {...context} />
          <HebeltraderLoss {...context} />
        </div>
      </details>
    </div>
  );
}
