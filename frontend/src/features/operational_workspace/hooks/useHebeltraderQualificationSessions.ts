import { useCallback, useState } from 'react';
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
export function useHebeltraderQualificationSessions(): QualificationSessions {
  const [values, setValues] = useState<Record<string, QualificationSession>>({});
  const update = useCallback((key: string, change: QualificationUpdate) => {
    setValues((previous) => ({
      ...previous,
      [key]: change(previous[key] ?? emptyQualificationSession),
    }));
  }, []);
  return { values, update };
}
