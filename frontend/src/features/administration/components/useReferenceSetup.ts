import { useCallback, useEffect, useRef, useState } from 'react';
import { chartClient } from '../../analysis/services/chartClient';
import { candidateApiClient } from '../../candidate/services/client';
import type { CandidateLiveWorkflow } from '../../candidate/types/api';
import { MarketApiError } from '../../market/services/http';
import {
  resolveReferenceDataContext,
  type ReferenceDataContext,
  type ResolvedReferenceDataContext,
} from '../services/referenceDataContext';
import { mappingInputsChanged, normalizeMappingInput } from '../services/referenceMapping';
import {
  editsMapping,
  executeSetup,
  initialSetupDraft,
  isDirectReference,
  isListingAction,
  readSetupSnapshot,
  setupProblem,
  snapshotReviewKey,
  SetupValidationError,
  validateSetupReceipt,
  type SetupDraft,
  type SetupSelection,
  type SetupSnapshot,
} from '../services/referenceSetup';

type Outcome = 'none' | 'complete' | 'unknown';
interface Transition {
  selection: SetupSelection;
  draft?: Partial<SetupDraft>;
}
const messageOf = (reason: unknown) =>
  reason instanceof Error ? reason.message : 'Der Schritt konnte nicht abgeschlossen werden.';
function draftKey(draft: SetupDraft) {
  return JSON.stringify({
    ...draft,
    symbol: normalizeMappingInput(draft.symbol),
    exchange: normalizeMappingInput(draft.exchange),
  });
}

export function useReferenceSetup(context: ReferenceDataContext) {
  const candidate = Boolean(context.candidateId);
  const [selection, setSelection] = useState<SetupSelection>(context);
  const selectionRef = useRef(selection);
  const baselineSelection = useRef(JSON.stringify(selection));
  const [draft, setDraft] = useState(() => initialSetupDraft(context.action, candidate));
  const draftRef = useRef(draft);
  const baselineDraft = useRef(draftKey(draft));
  const dirty = useRef(false);
  const [confirmed, setConfirmed] = useState(false);
  const confirmationRef = useRef(false);
  const [busy, setBusy] = useState(false);
  const locked = useRef(false);
  const [loading, setLoading] = useState(true);
  const [resolved, setResolved] = useState<ResolvedReferenceDataContext | null>(null);
  const [snapshot, setSnapshot] = useState<SetupSnapshot | null>(null);
  const snapshotRef = useRef<SetupSnapshot | null>(null);
  const [error, setError] = useState('');
  const [readError, setReadError] = useState('');
  const [message, setMessage] = useState('');
  const [outcome, setOutcome] = useState<Outcome>('none');
  const outcomeRef = useRef<Outcome>('none');
  const [reviewRequired, setReviewRequired] = useState(false);
  const [pending, setPending] = useState<Transition | null>(null);
  const [workflow, setWorkflow] = useState<CandidateLiveWorkflow | null>(null);
  const sequence = useRef(0);
  const readAbort = useRef<AbortController | null>(null);
  const mounted = useRef(true);

  const clearConfirmation = useCallback(() => {
    confirmationRef.current = false;
    setConfirmed(false);
  }, []);
  const markOutcome = useCallback((value: Outcome) => {
    outcomeRef.current = value;
    setOutcome(value);
  }, []);
  const shouldBlock = useCallback(
    () =>
      locked.current ||
      dirty.current ||
      confirmationRef.current ||
      outcomeRef.current === 'unknown',
    [],
  );
  const setDraftValue = useCallback((value: SetupDraft) => {
    draftRef.current = value;
    setDraft(value);
    dirty.current =
      draftKey(value) !== baselineDraft.current ||
      JSON.stringify(selectionRef.current) !== baselineSelection.current;
  }, []);

  const applySnapshot = useCallback(
    (value: SetupSnapshot, prefill: boolean) => {
      if (
        prefill &&
        value.mapping &&
        (isDirectReference(selectionRef.current.action) ||
          isListingAction(selectionRef.current.action))
      ) {
        const previous = selectionRef.current;
        const bound = {
          ...previous,
          mappingId: value.mapping.id,
          listingId: value.listing?.id ?? previous.listingId,
        };
        if (baselineSelection.current === JSON.stringify(previous))
          baselineSelection.current = JSON.stringify(bound);
        selectionRef.current = bound;
        setSelection(bound);
      }
      snapshotRef.current = value;
      setSnapshot(value);
      setReadError(value.venueError ? `Handelsplatz-Lesestand fehlt: ${value.venueError}` : '');
      if (prefill && editsMapping(selectionRef.current.action)) {
        const filled = {
          ...draftRef.current,
          symbol: value.mapping?.provider_symbol ?? '',
          exchange: value.mapping?.provider_exchange_code ?? '',
        };
        baselineDraft.current = draftKey(filled);
        setDraftValue(filled);
      }
      clearConfirmation();
    },
    [clearConfirmation, setDraftValue],
  );

  const read = useCallback(
    async (choice: SetupSelection, prefill = false, readWorkflow = false) => {
      const generation = ++sequence.current;
      readAbort.current?.abort();
      const abort = new AbortController();
      readAbort.current = abort;
      setLoading(true);
      setReadError('');
      try {
        const [value, nextWorkflow] = await Promise.all([
          readSetupSnapshot(choice, abort.signal),
          readWorkflow && context.candidateId
            ? candidateApiClient.liveWorkflow(context.candidateId, abort.signal)
            : Promise.resolve(null),
        ]);
        if (!mounted.current || abort.signal.aborted || generation !== sequence.current) return;
        if (nextWorkflow && nextWorkflow.candidate_id !== context.candidateId)
          throw new Error('Der gelesene Workflow gehört zu einem anderen Kandidaten.');
        if (
          !prefill &&
          outcomeRef.current === 'none' &&
          snapshotRef.current &&
          snapshotReviewKey(snapshotRef.current) !== snapshotReviewKey(value)
        )
          setReviewRequired(true);
        applySnapshot(value, prefill);
        if (nextWorkflow) setWorkflow(nextWorkflow);
      } catch (reason: unknown) {
        if (mounted.current && !abort.signal.aborted && generation === sequence.current)
          setReadError(messageOf(reason));
      } finally {
        if (mounted.current && !abort.signal.aborted && generation === sequence.current)
          setLoading(false);
      }
    },
    [applySnapshot, context.candidateId],
  );

  useEffect(() => {
    mounted.current = true;
    const abort = new AbortController();
    resolveReferenceDataContext(context, abort.signal)
      .then(async (value) => {
        if (abort.signal.aborted) return;
        setResolved(value);
        setWorkflow(value.workflow);
        const choice: SetupSelection = {
          action: value.action,
          underlyingId: value.underlyingId,
          listingId: value.listingId,
          referenceId: value.referenceId,
          sectorId: value.sectorId,
          mappingId: value.mappingId,
        };
        selectionRef.current = choice;
        baselineSelection.current = JSON.stringify(choice);
        setSelection(choice);
        await read(choice, true);
      })
      .catch((reason: unknown) => {
        if (!abort.signal.aborted) {
          setError(messageOf(reason));
          setLoading(false);
        }
      });
    return () => {
      mounted.current = false;
      abort.abort();
      readAbort.current?.abort();
      sequence.current += 1;
    };
  }, [context, read]);

  function changeDraft(patch: Partial<SetupDraft>) {
    if (locked.current) return;
    clearConfirmation();
    setDraftValue({ ...draftRef.current, ...patch });
    if (
      outcomeRef.current === 'complete' &&
      editsMapping(selectionRef.current.action) &&
      !candidate
    ) {
      markOutcome('none');
      setMessage('');
    }
  }
  function commitTransition(transition: Transition) {
    if (locked.current) return;
    setPending(null);
    const nextDraft = {
      ...initialSetupDraft(transition.selection.action, candidate),
      ...transition.draft,
    };
    selectionRef.current = transition.selection;
    baselineSelection.current = JSON.stringify(transition.selection);
    setSelection(transition.selection);
    baselineDraft.current = draftKey(initialSetupDraft(transition.selection.action, candidate));
    setDraftValue(nextDraft);
    snapshotRef.current = null;
    setSnapshot(null);
    clearConfirmation();
    setReviewRequired(false);
    setError('');
    setMessage('');
    markOutcome('none');
    void read(transition.selection, true);
  }
  function changeContext(next: SetupSelection, proposed?: Partial<SetupDraft>) {
    if (locked.current || !resolved) return;
    const transition = { selection: next, draft: proposed };
    if (shouldBlock()) setPending(transition);
    else commitTransition(transition);
  }
  function changeTarget(patch: Partial<SetupSelection>) {
    if (locked.current || !resolved || outcomeRef.current === 'unknown') return;
    const next = { ...selectionRef.current, ...patch };
    selectionRef.current = next;
    setSelection(next);
    dirty.current =
      draftKey(draftRef.current) !== baselineDraft.current ||
      JSON.stringify(next) !== baselineSelection.current;
    snapshotRef.current = null;
    setSnapshot(null);
    clearConfirmation();
    setReviewRequired(false);
    setError('');
    setMessage('');
    markOutcome('none');
    void read(next);
  }
  function confirm(value: boolean) {
    if (!locked.current) {
      confirmationRef.current = value;
      setConfirmed(value);
    }
  }
  function discardForRoute() {
    dirty.current = false;
    confirmationRef.current = false;
  }

  async function submit() {
    const shown = snapshotRef.current;
    const choice = selectionRef.current;
    if (
      locked.current ||
      loading ||
      !resolved ||
      !shown ||
      !confirmationRef.current ||
      reviewRequired ||
      outcomeRef.current !== 'none'
    )
      return;
    if (
      editsMapping(choice.action) &&
      !mappingInputsChanged(shown.mapping, draftRef.current.symbol, draftRef.current.exchange)
    )
      return;
    if (setupProblem(choice, shown, draftRef.current)) return;
    locked.current = true;
    setBusy(true);
    readAbort.current?.abort();
    sequence.current += 1;
    clearConfirmation();
    setError('');
    setReadError('');
    setMessage('');
    let sent = false;
    try {
      if (candidate) await resolveReferenceDataContext(context);
      const fresh = await readSetupSnapshot(choice);
      if (snapshotReviewKey(shown) !== snapshotReviewKey(fresh)) {
        applySnapshot(fresh, false);
        setReviewRequired(true);
        setError(
          'Der gelesene Stand hat sich geändert. Bitte den aktuellen Stand prüfen; dein Entwurf bleibt erhalten.',
        );
        return;
      }
      const problem = setupProblem(choice, fresh, draftRef.current);
      if (problem) throw new Error(problem);
      sent = true;
      const result = await executeSetup(choice, fresh, draftRef.current, candidate);
      validateSetupReceipt(choice, fresh, draftRef.current, candidate, result);
      // Bind a newly created mapping to the acknowledged identity before readback.
      // A different current mapping must never become the target of this request.
      const readChoice =
        (choice.action.endsWith('Mapping') || choice.action.endsWith('Validate')) &&
        result &&
        typeof result === 'object' &&
        'id' in result &&
        typeof result.id === 'string'
          ? { ...choice, mappingId: result.id, listingId: fresh.listing?.id ?? choice.listingId }
          : choice;
      selectionRef.current = readChoice;
      setSelection(readChoice);
      markOutcome('complete');
      baselineDraft.current = draftKey(draftRef.current);
      baselineSelection.current = JSON.stringify(readChoice);
      dirty.current = false;
      if (
        result &&
        typeof result === 'object' &&
        'inserted' in result &&
        'updated' in result &&
        'unchanged' in result
      ) {
        setMessage(
          `Import abgeschlossen: ${String(result.inserted)} neu, ${String(result.updated)} aktualisiert, ${String(result.unchanged)} unverändert.`,
        );
      } else if (choice.action.endsWith('Validate')) {
        setMessage(
          'Prüfauftrag abgeschlossen. Technischer Mappingstatus und Handelsplatzabgleich werden getrennt neu gelesen.',
        );
      } else {
        setMessage(
          'Schritt gespeichert. Weitere Zuordnungen, Validierung und Import bleiben separate Aktionen.',
        );
      }
      chartClient.clear();
      await read(readChoice, editsMapping(choice.action), true);
    } catch (reason: unknown) {
      setError(
        reason instanceof MarketApiError
          ? `${reason.response.code}: ${reason.message}`
          : messageOf(reason),
      );
      if (
        sent &&
        !(reason instanceof SetupValidationError) &&
        (!(reason instanceof MarketApiError) || reason.status >= 500)
      ) {
        markOutcome('unknown');
        setMessage(
          'Der Transportabschluss ist unbekannt. Zuerst wird der aktuelle Zustand gelesen. Ein passender Wert beweist nicht den Abschluss dieses Requests; der Schreibauftrag wird nicht wiederholt.',
        );
        chartClient.clear();
        await read(choice, false, true);
      }
    } finally {
      if (mounted.current) {
        locked.current = false;
        setBusy(false);
      }
    }
  }

  const problem = snapshot ? setupProblem(selection, snapshot, draft) : '';
  const unchanged = Boolean(
    snapshot &&
      editsMapping(selection.action) &&
      !mappingInputsChanged(snapshot.mapping, draft.symbol, draft.exchange),
  );
  return {
    selection,
    draft,
    snapshot,
    resolved,
    workflow,
    busy,
    loading,
    error,
    readError,
    message,
    outcome,
    reviewRequired,
    pending,
    confirmed,
    problem,
    unchanged,
    canSubmit: Boolean(
      resolved &&
        snapshot &&
        !busy &&
        !loading &&
        !readError &&
        !reviewRequired &&
        !problem &&
        !unchanged &&
        outcome === 'none' &&
        confirmed,
    ),
    shouldBlock,
    discardForRoute,
    confirm,
    changeDraft,
    changeContext,
    changeTarget,
    submit,
    cancel: () => changeContext(selection),
    stay: () => setPending(null),
    discard: () => {
      if (pending) commitTransition(pending);
    },
    acknowledge: () => {
      if (!locked.current) {
        setReviewRequired(false);
        setError('');
        clearConfirmation();
      }
    },
    reload: () => {
      if (!locked.current) {
        clearConfirmation();
        chartClient.clear();
        void read(selectionRef.current, false, true);
      }
    },
    isMappingContext: isDirectReference(selection.action) || isListingAction(selection.action),
  };
}
