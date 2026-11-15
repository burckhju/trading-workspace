import { useEffect, useRef, useState } from 'react';
import type {
  HebeltraderTargetAssessmentRequest,
  HebeltraderTargetsReport,
} from '../hebeltraderTargets';
import { readTargetRequest } from '../services/hebeltraderQualification';
import { assessHebeltraderTargets, HebeltraderCommandError } from '../services/hebeltraderTargets';
import type {
  QualificationSession,
  QualificationSessions,
} from './useHebeltraderQualificationSessions';

export function useHebeltraderTargetCommand({
  tradeId,
  positionId,
  sessionKey,
  session,
  update,
  onReport,
}: {
  tradeId: string;
  positionId: string;
  sessionKey: string;
  session: QualificationSession;
  update: QualificationSessions['update'];
  onReport: (report: HebeltraderTargetsReport) => void;
}) {
  const generation = useRef(0);
  const pending = useRef<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const [readingReceipt, setReadingReceipt] = useState(false);
  const reading = useRef(false);
  const [receiptError, setReceiptError] = useState<string | null>(null);

  useEffect(() => {
    generation.current += 1;
    return () => {
      generation.current += 1;
      controller.current?.abort();
      const id = pending.current;
      if (id)
        update(sessionKey, (previous) =>
          previous.command?.payload.request_id === id
            ? {
                ...previous,
                command: {
                  ...previous.command,
                  phase: 'UNKNOWN',
                  message:
                    'Die Ansicht wurde während der Anfrage gewechselt. Der Schreibausgang ist unbestätigt.',
                },
              }
            : previous,
        );
    };
  }, [sessionKey, update]);

  async function execute(payload: HebeltraderTargetAssessmentRequest, retry = false) {
    if (pending.current || reading.current || (!retry && session.command?.phase === 'UNKNOWN'))
      return;
    pending.current = payload.request_id;
    const unresolvedRetry = retry && session.command?.phase === 'UNKNOWN';
    const abort = new AbortController();
    controller.current = abort;
    const currentGeneration = generation.current;
    const current = () => generation.current === currentGeneration && !abort.signal.aborted;
    setReceiptError(null);
    update(sessionKey, (previous) => ({
      ...previous,
      commandEpoch: previous.commandEpoch + 1,
      command: { payload, phase: 'PENDING', message: null, receipt: null },
    }));
    try {
      const report = await assessHebeltraderTargets(tradeId, payload, abort.signal);
      if (!current()) return;
      update(sessionKey, (previous) => ({
        ...previous,
        command: {
          payload,
          phase: 'CONFIRMED',
          message:
            'Die ausdrückliche Prüfung wurde bestätigt. Die Betriebsaktivierung bleibt unverändert.',
          receipt: null,
        },
      }));
      onReport(report);
    } catch (error) {
      if (!current()) return;
      const rejected = error instanceof HebeltraderCommandError && error.outcome === 'REJECTED';
      update(sessionKey, (previous) => ({
        ...previous,
        command: {
          payload,
          phase: rejected && !unresolvedRetry ? 'REJECTED' : 'UNKNOWN',
          receipt: null,
          message:
            rejected && unresolvedRetry
              ? `Die Wiederholung wurde abgelehnt: ${error.message} Der Ausgang der ursprünglichen Anfrage bleibt unbestätigt.`
              : error instanceof Error
                ? error.message
                : 'Der Schreibausgang ist unbestätigt.',
        },
      }));
    } finally {
      if (current()) pending.current = null;
    }
  }

  async function readReceipt() {
    const command = session.command;
    if (!command || command.phase !== 'UNKNOWN' || pending.current || reading.current) return;
    reading.current = true;
    setReadingReceipt(true);
    setReceiptError(null);
    const abort = new AbortController();
    controller.current = abort;
    const currentGeneration = generation.current;
    const current = () => generation.current === currentGeneration && !abort.signal.aborted;
    try {
      const receipt = await readTargetRequest(
        tradeId,
        positionId,
        command.payload.request_id,
        abort.signal,
      );
      if (!current()) return;
      const expected = command.payload.qualification;
      if (
        receipt.status === 'RECORDED' &&
        (receipt.assessment?.basis_id !== command.payload.expected_basis_id ||
          (expected &&
            (!receipt.qualification ||
              (
                [
                  'history_fingerprint',
                  'listing_fingerprint',
                  'source_version_id',
                  'source_scale_reference',
                  'evidence_reference',
                ] as const
              ).some((key) => expected[key] !== receipt.qualification?.[key]))))
      ) {
        throw new Error(
          'Der Vorgangsbeleg passt nicht zum eingefrorenen Prüfauftrag. Der Ausgang bleibt unbestätigt.',
        );
      }
      update(sessionKey, (previous) =>
        previous.command?.payload.request_id === command.payload.request_id
          ? {
              ...previous,
              commandEpoch: previous.commandEpoch + (receipt.status === 'RECORDED' ? 1 : 0),
              command: {
                ...previous.command,
                phase: receipt.status === 'RECORDED' ? 'CONFIRMED' : 'UNKNOWN',
                receipt,
                message:
                  receipt.status === 'RECORDED'
                    ? 'Der gespeicherte Vorgangsbeleg bestätigt genau diese Anfrage. Er zeigt ihren damaligen Prüfstand.'
                    : 'Der Vorgangsstatus ist unbekannt. Dies beweist weder ein Scheitern noch einen laufenden oder fehlenden Vorgang.',
              },
            }
          : previous,
      );
    } catch (error) {
      if (current())
        setReceiptError(
          error instanceof Error ? error.message : 'Der Vorgangsbeleg konnte nicht gelesen werden.',
        );
    } finally {
      if (current()) {
        reading.current = false;
        setReadingReceipt(false);
      }
    }
  }

  return {
    execute,
    readReceipt,
    retry: () => session.command?.phase === 'UNKNOWN' && execute(session.command.payload, true),
    busy: session.command?.phase === 'PENDING' || readingReceipt,
    blocked:
      session.command?.phase === 'PENDING' ||
      session.command?.phase === 'UNKNOWN' ||
      readingReceipt,
    readingReceipt,
    receiptError,
  };
}
