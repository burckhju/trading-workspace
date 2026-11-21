import { useCallback, useRef, useState } from 'react';
import type { TargetRequestStatus } from '../hebeltraderQualification';
import type { HebeltraderTargetAssessmentRequest } from '../hebeltraderTargets';

export interface QualificationSession {
  open: boolean;
  reference: string;
  referenceBasisId: string | null;
  commandEpoch: number;
  command: {
    payload: HebeltraderTargetAssessmentRequest;
    phase: 'PENDING' | 'UNKNOWN' | 'REJECTED' | 'CONFIRMED';
    message: string | null;
    receipt: TargetRequestStatus | null;
  } | null;
}

export const emptyQualificationSession: QualificationSession = {
  open: false,
  reference: '',
  referenceBasisId: null,
  commandEpoch: 0,
  command: null,
};

export type QualificationUpdate = (previous: QualificationSession) => QualificationSession;

export interface QualificationSessions {
  values: Readonly<Record<string, QualificationSession>>;
  update: (key: string, change: QualificationUpdate) => void;
}

export function qualificationSessionKey(tradeId: string, positionId: string): string {
  return JSON.stringify([tradeId, positionId]);
}

/** Explicit host-owned, in-memory drafts; no browser storage or global mutable cache. */
export function useHebeltraderQualificationSessions(): QualificationSessions & {
  getSnapshot: () => Readonly<Record<string, QualificationSession>>;
} {
  const [values, setValues] = useState<Record<string, QualificationSession>>({});
  const current = useRef(values);
  const update = useCallback((key: string, change: QualificationUpdate) => {
    const next = {
      ...current.current,
      [key]: change(current.current[key] ?? emptyQualificationSession),
    };
    // Navigation and other owner commands see a new draft/write lock synchronously.
    current.current = next;
    setValues(next);
  }, []);
  const getSnapshot = useCallback(() => current.current, []);
  return { values, update, getSnapshot };
}
