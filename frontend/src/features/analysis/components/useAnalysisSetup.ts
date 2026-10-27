import { useCallback, useEffect, useRef, useState } from 'react';
import { MarketApiError } from '../../market/services/http';
import {
  analysisDraftProblem,
  analysisDraftRequest,
  initialAnalysisDraft,
  prepareAnalysisSource,
  validateAnalysisCreateReceipt,
  validateAnalysisRunReadback,
  validateAnalysisRunReceipt,
  type AnalysisDraft,
} from '../services/analysisSetupDraft';
import {
  resolveAnalysisSetupContext,
  type AnalysisSetupContext,
  type ResolvedAnalysisSetupContext,
} from '../services/analysisWorkflowContext';
import { analysisApiClient } from '../services/client';
import type {
  AnalysisRun,
  AnalysisRunDetail,
  AnalysisSummary,
  RunAnalysisRequest,
} from '../types/api';

type Outcome = 'none' | 'complete' | 'unknown';
type Transition = { context: AnalysisSetupContext } | { draft: AnalysisDraft };
type AcknowledgedRun = { run: AnalysisRun; request: RunAnalysisRequest };
const messageOf = (error: unknown) =>
  error instanceof MarketApiError
    ? `${error.response.code}: ${error.message}`
    : error instanceof Error
      ? error.message
      : 'Der Analyseauftrag konnte nicht abgeschlossen werden.';

function reviewKey(value: ResolvedAnalysisSetupContext) {
  return JSON.stringify({
    analysis: value.detail,
    underlying: value.underlying && [
      value.underlying.id,
      value.underlying.version,
      value.underlying.lifecycle_status,
    ],
    listing: value.listing,
    source: value.source && [value.source.run, value.source.parameters],
    step: value.workflowStep,
  });
}

function contextProblem(value: ResolvedAnalysisSetupContext | null): string {
  if (!value) return 'Der vorhandene Kontext muss zuerst vollständig gelesen werden.';
  if (value.detail) return '';
  if (!value.underlying) return 'Bitte einen vorhandenen Basiswert auswählen.';
  if (!value.listing) return 'Bitte eine bestehende Notierung ausdrücklich auswählen.';
  if (value.underlying.lifecycle_status !== 'ACTIVE' || value.listing.lifecycle_status !== 'ACTIVE')
    return 'Für eine neue Analyse werden ein aktiver Basiswert und eine aktive Notierung benötigt.';
  return '';
}

export function useAnalysisSetup(
  context: AnalysisSetupContext,
  onCreated: (context: AnalysisSetupContext) => void,
) {
  const [initialContext] = useState(context);
  const [choice, setChoice] = useState(context);
  const choiceRef = useRef(context);
  const baselineChoice = useRef(JSON.stringify([context.underlyingId, context.listingId]));
  const initialDraft = () =>
    initialAnalysisDraft(Boolean(context.workflowAction), context.sourceVersion !== null);
  const [draft, setDraft] = useState(initialDraft);
  const draftRef = useRef(draft);
  const baselineDraft = useRef(JSON.stringify(draft));
  const dirty = useRef(false);
  const [snapshot, setSnapshot] = useState<ResolvedAnalysisSetupContext | null>(null);
  const snapshotRef = useRef<ResolvedAnalysisSetupContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [initialReady, setInitialReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const locked = useRef(false);
  const [confirmed, setConfirmed] = useState(false);
  const confirmedRef = useRef(false);
  const [outcome, setOutcome] = useState<Outcome>('none');
  const outcomeRef = useRef<Outcome>('none');
  const [reviewRequired, setReviewRequired] = useState(false);
  const [pending, setPending] = useState<Transition | null>(null);
  const [error, setError] = useState('');
  const [readError, setReadError] = useState('');
  const [acknowledged, setAcknowledged] = useState<AcknowledgedRun | null>(null);
  const acknowledgedRef = useRef<AcknowledgedRun | null>(null);
  const [readRun, setReadRun] = useState<AnalysisRunDetail | null>(null);
  const [possibleAnalyses, setPossibleAnalyses] = useState<AnalysisSummary[]>([]);
  const generation = useRef(0);
  const readAbort = useRef<AbortController | null>(null);
  const mounted = useRef(false);

  const clearConfirmation = useCallback(() => {
    confirmedRef.current = false;
    setConfirmed(false);
  }, []);
  const markOutcome = (value: Outcome) => {
    outcomeRef.current = value;
    setOutcome(value);
  };
  const shouldBlock = useCallback(
    () =>
      locked.current || dirty.current || confirmedRef.current || outcomeRef.current === 'unknown',
    [],
  );
  const applyDraft = (value: AnalysisDraft) => {
    draftRef.current = value;
    setDraft(value);
    dirty.current =
      JSON.stringify(value) !== baselineDraft.current ||
      JSON.stringify([choiceRef.current.underlyingId, choiceRef.current.listingId]) !==
        baselineChoice.current;
    clearConfirmation();
  };

  const read = useCallback(
    async (requested: AnalysisSetupContext, initial = false) => {
      const sequence = ++generation.current;
      readAbort.current?.abort();
      const controller = new AbortController();
      readAbort.current = controller;
      setLoading(true);
      setReadError('');
      clearConfirmation();
      try {
        const value = await resolveAnalysisSetupContext(requested, controller.signal, {
          requireBlockedStep: outcomeRef.current === 'none',
        });
        let exactRun: AnalysisRunDetail | null = null;
        const receipt = acknowledgedRef.current;
        if (receipt && value.detail) {
          exactRun = await analysisApiClient.getRun(
            requested.analysisId,
            receipt.run.version,
            controller.signal,
          );
          validateAnalysisRunReadback(exactRun, value.detail, receipt.run, receipt.request);
        }
        let possible: AnalysisSummary[] = [];
        if (outcomeRef.current === 'unknown' && !requested.analysisId) {
          const analyses = await analysisApiClient.list(controller.signal);
          possible = analyses.filter(
            (item) =>
              item.underlying_id === requested.underlyingId &&
              item.listing_id === requested.listingId,
          );
        }
        if (!mounted.current || controller.signal.aborted || sequence !== generation.current)
          return;
        if (
          !initial &&
          outcomeRef.current === 'none' &&
          snapshotRef.current &&
          reviewKey(snapshotRef.current) !== reviewKey(value)
        )
          setReviewRequired(true);
        if (
          initial &&
          baselineChoice.current === JSON.stringify([requested.underlyingId, requested.listingId])
        )
          baselineChoice.current = JSON.stringify([
            value.context.underlyingId,
            value.context.listingId,
          ]);
        choiceRef.current = value.context;
        setChoice(value.context);
        snapshotRef.current = value;
        setSnapshot(value);
        setReadRun(exactRun);
        setPossibleAnalyses(possible);
        setInitialReady(true);
      } catch (reason: unknown) {
        if (mounted.current && !controller.signal.aborted && sequence === generation.current)
          setReadError(messageOf(reason));
      } finally {
        if (mounted.current && !controller.signal.aborted && sequence === generation.current)
          setLoading(false);
      }
    },
    [clearConfirmation],
  );

  useEffect(() => {
    mounted.current = true;
    void read(initialContext, true);
    return () => {
      mounted.current = false;
      readAbort.current?.abort();
      generation.current += 1;
    };
  }, [initialContext, read]);

  function commitTransition(transition: Transition) {
    if (locked.current || outcomeRef.current !== 'none') return;
    setPending(null);
    setError('');
    setReviewRequired(false);
    clearConfirmation();
    if ('draft' in transition) {
      applyDraft(transition.draft);
      return;
    }
    choiceRef.current = transition.context;
    setChoice(transition.context);
    snapshotRef.current = null;
    setSnapshot(null);
    baselineChoice.current = JSON.stringify([
      transition.context.underlyingId,
      transition.context.listingId,
    ]);
    const nextDraft = initialAnalysisDraft(
      Boolean(initialContext.workflowAction),
      initialContext.sourceVersion !== null,
    );
    baselineDraft.current = JSON.stringify(nextDraft);
    applyDraft(nextDraft);
    void read(transition.context, true);
  }
  function transition(value: Transition) {
    if (locked.current || outcomeRef.current !== 'none' || !initialReady) return;
    if (shouldBlock()) setPending(value);
    else commitTransition(value);
  }
  function changeTarget(underlyingId: string, listingId: string) {
    if (choiceRef.current.analysisId || initialContext.workflowAction || locked.current) return;
    transition({ context: { ...initialContext, underlyingId, listingId } });
  }
  function changeDraft(patch: Partial<AnalysisDraft>) {
    if (!locked.current && outcomeRef.current === 'none')
      applyDraft({ ...draftRef.current, ...patch });
  }
  function prepareSource() {
    if (locked.current || !snapshotRef.current?.source || outcomeRef.current !== 'none') return;
    try {
      transition({
        draft: prepareAnalysisSource(draftRef.current, snapshotRef.current.source.parameters),
      });
    } catch (reason: unknown) {
      setError(messageOf(reason));
      clearConfirmation();
    }
  }

  async function submit() {
    const shown = snapshotRef.current;
    const selected = choiceRef.current;
    if (
      locked.current ||
      loading ||
      readError ||
      reviewRequired ||
      !confirmedRef.current ||
      outcomeRef.current !== 'none' ||
      !shown ||
      contextProblem(shown)
    )
      return;
    const running = Boolean(selected.analysisId);
    let request: RunAnalysisRequest | null = null;
    if (running) {
      try {
        request = analysisDraftRequest(draftRef.current);
      } catch (reason: unknown) {
        setError(messageOf(reason));
        return;
      }
    }
    locked.current = true;
    setBusy(true);
    readAbort.current?.abort();
    const writeGeneration = ++generation.current;
    clearConfirmation();
    setError('');
    setReadError('');
    let sent = false;
    let createdContext: AnalysisSetupContext | null = null;
    try {
      const fresh = await resolveAnalysisSetupContext(selected);
      if (!mounted.current || generation.current !== writeGeneration) return;
      if (reviewKey(shown) !== reviewKey(fresh)) {
        snapshotRef.current = fresh;
        setSnapshot(fresh);
        setReviewRequired(true);
        setError(
          'Der gelesene Analysekontext hat sich geändert. Bitte den aktuellen Stand prüfen; deine Eingaben bleiben erhalten.',
        );
        return;
      }
      const problem = contextProblem(fresh);
      if (problem) throw new Error(problem);
      if (running && request && fresh.detail) {
        sent = true;
        const value =
          fresh.detail.analysis.listing_id === null
            ? await analysisApiClient.runReference(selected.analysisId, request)
            : await analysisApiClient.run(selected.analysisId, request);
        if (!mounted.current || generation.current !== writeGeneration) return;
        validateAnalysisRunReceipt(value, fresh.detail);
        const receipt = { run: value, request };
        acknowledgedRef.current = receipt;
        setAcknowledged(receipt);
        markOutcome('complete');
        dirty.current = false;
        baselineDraft.current = JSON.stringify(draftRef.current);
        await read(selected);
      } else if (!running && fresh.underlying && fresh.listing) {
        sent = true;
        const value = await analysisApiClient.create(fresh.underlying.id, fresh.listing.id);
        if (!mounted.current || generation.current !== writeGeneration) return;
        validateAnalysisCreateReceipt(value, fresh.underlying.id, fresh.listing.id);
        createdContext = {
          ...fresh.context,
          analysisId: value.id,
          instrumentId: value.market_data_instrument_id ?? '',
        };
        choiceRef.current = createdContext;
        dirty.current = false;
        markOutcome('complete');
      }
    } catch (reason: unknown) {
      setError(messageOf(reason));
      if (sent && (!(reason instanceof MarketApiError) || reason.status >= 500)) {
        markOutcome('unknown');
        await read(selected);
      }
    } finally {
      if (mounted.current) {
        locked.current = false;
        setBusy(false);
      }
    }
    if (createdContext && mounted.current) onCreated(createdContext);
  }

  const problem =
    contextProblem(snapshot) || (choice.analysisId ? analysisDraftProblem(draft) : '');
  return {
    choice,
    snapshot,
    draft,
    confirmed,
    busy,
    loading,
    initialReady,
    pending,
    error,
    readError,
    reviewRequired,
    acknowledged,
    readRun,
    possibleAnalyses,
    outcome,
    problem,
    canSubmit:
      !busy &&
      !loading &&
      !readError &&
      !reviewRequired &&
      !problem &&
      outcome === 'none' &&
      confirmed,
    shouldBlock,
    changeDraft,
    changeTarget,
    prepareSource,
    submit,
    confirm: (value: boolean) => {
      if (!locked.current && outcomeRef.current === 'none') {
        confirmedRef.current = value;
        setConfirmed(value);
      }
    },
    reload: () => {
      if (!locked.current) void read(choiceRef.current);
    },
    acknowledge: () => {
      if (!locked.current) {
        setReviewRequired(false);
        setError('');
        clearConfirmation();
      }
    },
    cancel: () =>
      transition({
        draft: initialAnalysisDraft(
          Boolean(initialContext.workflowAction),
          initialContext.sourceVersion !== null,
        ),
      }),
    stay: () => setPending(null),
    discard: () => {
      if (pending) commitTransition(pending);
    },
    discardForRoute: () => {
      if (!locked.current) {
        dirty.current = false;
        confirmedRef.current = false;
      }
    },
  };
}
