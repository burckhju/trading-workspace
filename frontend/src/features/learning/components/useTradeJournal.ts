import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { MarketApiError } from '../../market/services/http';
import {
  journalClient,
  selectJournalEntry,
  snapshotJournalActor,
  type JournalActor,
  type JournalCommand,
  type JournalHistory,
  type JournalReceipt,
  type JournalTexts,
  type JournalVersion,
} from '../services/journalClient';
import {
  confirmationIsCurrent,
  journalQuery,
  journalTexts,
  sameJournalTexts,
  sameJournalVersion,
  type JournalConfirmation,
} from './journalViewState';

export type JournalNavigationState = { dirty: boolean; pending: boolean };
export type JournalPanelProps = {
  tradeId: string;
  refreshVersion?: number;
  discardVersion?: number;
  onNavigationStateChange?: (state: JournalNavigationState) => void;
  isContextPending?: () => boolean;
};

type Editor = { base: JournalVersion; texts: JournalTexts };
type Attempt = {
  tradeId: string;
  actor: JournalActor;
  command: JournalCommand;
  key: string;
  base: JournalVersion | null;
  outcome: 'running' | 'unknown' | 'confirmed';
  receipt: JournalReceipt | null;
};
type JournalState = {
  queryKey: string;
  history: JournalHistory | null;
  selectedId: string | null;
  editor: Editor | null;
  confirmation: JournalConfirmation | null;
  readState: 'loading' | 'ready' | 'error';
  completedRefresh: number | null;
  pending: boolean;
  attempt: Attempt | null;
  reconcileRequired: boolean;
  error: string | null;
  notice: string | null;
};

function initialState(queryKey: string): JournalState {
  return {
    queryKey,
    history: null,
    selectedId: null,
    editor: null,
    confirmation: null,
    readState: 'loading',
    completedRefresh: null,
    pending: false,
    attempt: null,
    reconcileRequired: false,
    error: null,
    notice: null,
  };
}

function hasLocalChanges(state: JournalState): boolean {
  return !!state.editor && !sameJournalTexts(state.editor.base, state.editor.texts);
}

function commandError(error: unknown): string {
  if (error instanceof MarketApiError) {
    const messages: Record<string, string> = {
      JOURNAL_CONFLICT:
        'Der gespeicherte Journalstand wurde verändert. Eingaben bleiben erhalten; bitte den Lesestand prüfen und bewusst abgleichen.',
      SOURCE_VERSION_MISMATCH:
        'Die genaue Reviewquelle stimmt nicht mehr überein. Bitte neu lesen und die Quelle erneut ausdrücklich bestätigen.',
      JOURNAL_SOURCE_NOT_READY:
        'Die Reviewquelle ist für diese Aktion nicht bereit. Ein gültig gelesener bestehender Entwurf kann weiterhin gespeichert werden.',
      JOURNAL_NOT_FOUND: 'Die angefragte Journalversion oder der Trade ist nicht mehr vorhanden.',
      IDEMPOTENCY_KEY_REUSED:
        'Der Befehlsschlüssel gehört zu einem anderen Auftrag. Bitte den Lesestand prüfen.',
      JOURNAL_INVALID_REQUEST: 'Der Journalauftrag wurde als ungültig abgelehnt.',
    };
    return `${messages[error.response.code] ?? error.message} (${error.response.code})`;
  }
  return 'Der Schreibausgang ist unklar. Eingaben bleiben erhalten. Es wird kein Befehl automatisch wiederholt.';
}

export function useTradeJournal({
  tradeId,
  refreshVersion = 0,
  discardVersion = 0,
  onNavigationStateChange,
  isContextPending,
}: JournalPanelProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const query = journalQuery(location.search, tradeId);
  const [state, setState] = useState(() => initialState(query.key));
  const current = useRef(state);
  const context = useRef(query);
  context.current = query;
  const contextEpoch = useRef({ key: `${tradeId}:${query.key}`, value: 0 });
  if (contextEpoch.current.key !== `${tradeId}:${query.key}`) {
    contextEpoch.current = {
      key: `${tradeId}:${query.key}`,
      value: contextEpoch.current.value + 1,
    };
  }
  const report = useRef(onNavigationStateChange);
  report.current = onNavigationStateChange;
  const contextPending = useRef(isContextPending);
  contextPending.current = isContextPending;
  const readGeneration = useRef(0);
  const lifetime = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const currentRefresh = useRef(refreshVersion);
  currentRefresh.current = refreshVersion;
  const createdToOpen = useRef<string | null>(null);
  const selection = useRef<(id: string) => void>(() => undefined);
  selection.current = (id) => {
    const params = new URLSearchParams(location.search);
    params.set('trade_id', tradeId);
    params.set('journal_version_id', id);
    void navigate({ pathname: location.pathname, search: `?${params}`, hash: location.hash });
  };

  const update = useCallback((change: Partial<JournalState>) => {
    const next = { ...current.current, ...change };
    current.current = next;
    setState(next);
    // A same-tick route change must see both edits and the submit lock.
    report.current?.({
      dirty: hasLocalChanges(next) || !!next.attempt,
      pending: next.pending,
    });
  }, []);

  useEffect(() => {
    const life = lifetime;
    const reads = readGeneration;
    const abort = controller;
    ++life.current;
    return () => {
      ++life.current;
      ++reads.current;
      abort.current?.abort();
    };
  }, []);

  const load = useCallback(
    async (discardLocal = false, receiptAttempt?: Attempt): Promise<string | null> => {
      const requested = context.current;
      if (requested.error) {
        update({ readState: 'error', error: requested.error });
        return null;
      }
      const read = ++readGeneration.current;
      const activeLifetime = lifetime.current;
      const activeEpoch = contextEpoch.current.value;
      const activeRefresh = currentRefresh.current;
      controller.current?.abort();
      const requestController = new AbortController();
      controller.current = requestController;
      update({ readState: 'loading', error: null });
      try {
        const next = await journalClient.history(tradeId, requestController.signal);
        if (
          requestController.signal.aborted ||
          read !== readGeneration.current ||
          activeLifetime !== lifetime.current ||
          activeEpoch !== contextEpoch.current.value ||
          requested.key !== context.current.key
        ) {
          return null;
        }
        const previous = current.current;
        // An implicit initial selection is pinned across refreshes, too.
        const selected = selectJournalEntry(
          next,
          tradeId,
          requested.versionId ?? previous.selectedId,
        );
        let editor = previous.editor;
        let reconcileRequired = previous.reconcileRequired;
        let notice = previous.notice;
        let attempt = previous.attempt;
        let openCreated: string | null = null;
        if (receiptAttempt?.receipt) {
          const { command, receipt } = receiptAttempt;
          const materialize = command.operation === 'MATERIALIZE';
          if (
            receipt.result_type !== (materialize ? 'LEARNING_EVIDENCE' : 'TRADE_JOURNAL_VERSION') ||
            !receipt.result_id ||
            (!materialize && 'version_id' in command && receipt.result_id !== command.version_id)
          ) {
            throw new Error(
              'Der bestätigte Auftrag hat eine unerwartete Ergebnisidentität geliefert.',
            );
          }
          const result = selectJournalEntry(
            next,
            tradeId,
            materialize ? command.version_id : receipt.result_id,
          );
          if (!result) throw new Error('Das bestätigte Ergebnis fehlt im Journal-Lesestand.');
          if (materialize && result.learning_evidence_id !== receipt.result_id) {
            throw new Error(
              'Die bestätigte Evidence fehlt an der ausdrücklich übergebenen Journalversion.',
            );
          }
          if (
            materialize &&
            (!receiptAttempt.base || !sameJournalVersion(result.version, receiptAttempt.base))
          ) {
            throw new Error(
              'Der gelesene Journalstand entspricht nicht der unveränderlichen Evidencequelle.',
            );
          }
          if (
            command.operation === 'CREATE_DRAFT' &&
            result.version.supersedes_version_id !== command.expected_latest_version_id
          ) {
            throw new Error('Der bestätigte Entwurf hat nicht den erwarteten finalen Vorgänger.');
          }
          notice = receipt.replayed
            ? 'Früherer Journalauftrag bestätigt (Replay). Der aktuelle gespeicherte Stand wurde separat gelesen.'
            : 'Journalauftrag bestätigt. Der gespeicherte Stand wurde separat gelesen.';
          if (command.operation === 'SAVE_DRAFT' || command.operation === 'REBIND_SOURCE') {
            const saved = result.version;
            const expectedTexts =
              command.operation === 'SAVE_DRAFT' ? command : receiptAttempt.base;
            const expectedSource =
              command.operation === 'REBIND_SOURCE'
                ? command.expected_exit_review_version_id
                : receiptAttempt.base?.source_exit_review_version_id;
            const matches =
              saved.status === 'DRAFT' &&
              saved.edit_revision === command.expected_edit_revision + 1 &&
              saved.source_exit_review_version_id === expectedSource &&
              expectedTexts &&
              sameJournalTexts(saved, expectedTexts) &&
              (!editor || sameJournalTexts(editor.texts, expectedTexts));
            if (matches) {
              editor = null;
              reconcileRequired = false;
            } else {
              reconcileRequired = true;
              notice +=
                ' Der Entwurf ist inzwischen weiter verändert. Lokale Eingaben und ihre bisherige Basis bleiben erhalten; bitte bewusst abgleichen.';
            }
          } else if (command.operation === 'CREATE_DRAFT') {
            createdToOpen.current = result.version.id;
            openCreated = result.version.id;
          } else if (command.operation === 'FINALIZE') {
            if (
              result.version.status !== 'FINALIZED' ||
              result.version.edit_revision !== command.expected_edit_revision + 1 ||
              result.version.source_exit_review_version_id !==
                command.expected_exit_review_version_id ||
              !receiptAttempt.base ||
              !sameJournalTexts(result.version, receiptAttempt.base)
            ) {
              throw new Error('Der bestätigte Abschluss ist im Lesestand noch nicht finalisiert.');
            }
            editor = null;
          }
          attempt = null;
        }
        if (discardLocal) {
          editor = null;
          reconcileRequired = false;
          if (attempt?.outcome !== 'unknown') attempt = null;
          notice = 'Gespeicherten Journalstand geladen. Lokale Eingaben wurden bewusst verworfen.';
          if (attempt?.outcome === 'unknown')
            notice +=
              ' Der Ausgang des früheren Auftrags bleibt unklar; Folgeaktionen sind weiterhin gesperrt.';
        }
        if (
          selected?.version.id === createdToOpen.current &&
          requested.versionId === createdToOpen.current &&
          selected.version.status === 'DRAFT'
        ) {
          editor = { base: selected.version, texts: journalTexts(selected.version) };
          createdToOpen.current = null;
        }
        update({
          history: next,
          selectedId: selected?.version.id ?? null,
          editor,
          reconcileRequired,
          attempt,
          confirmation: discardLocal ? null : previous.confirmation,
          readState: 'ready',
          completedRefresh: activeRefresh,
          error: null,
          notice,
        });
        return openCreated;
      } catch (error) {
        if (
          !requestController.signal.aborted &&
          read === readGeneration.current &&
          activeLifetime === lifetime.current &&
          activeEpoch === contextEpoch.current.value &&
          requested.key === context.current.key
        ) {
          const detail =
            error instanceof Error ? error.message : 'Journal konnte nicht geladen werden.';
          update({
            readState: 'error',
            error: receiptAttempt?.receipt
              ? `Der Schreibauftrag ist bestätigt, aber sein exakter Lesestand konnte nicht bestätigt werden. ${detail} Nur den Lesestand erneut laden; keinen weiteren Schreibauftrag senden.`
              : `${detail} Ungespeicherte Eingaben bleiben erhalten.`,
          });
        }
        return null;
      }
    },
    [tradeId, update],
  );

  useEffect(() => {
    if (current.current.queryKey !== query.key) {
      ++readGeneration.current;
      controller.current?.abort();
      update(initialState(query.key));
    }
    if (current.current.pending) return undefined;
    void load(
      false,
      current.current.attempt?.outcome === 'confirmed' ? current.current.attempt : undefined,
    );
  }, [load, query.key, refreshVersion, update]);

  const previousDiscard = useRef(discardVersion);
  useEffect(() => {
    if (previousDiscard.current === discardVersion) return;
    previousDiscard.current = discardVersion;
    if (current.current.pending) return;
    update({
      editor: null,
      confirmation: null,
      attempt: null,
      reconcileRequired: false,
      notice: null,
    });
  }, [discardVersion, update]);

  const perform = useCallback(
    async (attempt: Attempt) => {
      if (current.current.pending || contextPending.current?.()) return;
      const activeLifetime = lifetime.current;
      const activeQuery = context.current.key;
      const activeEpoch = contextEpoch.current.value;
      const validContext = () =>
        activeLifetime === lifetime.current &&
        activeQuery === context.current.key &&
        activeEpoch === contextEpoch.current.value;
      update({
        pending: true,
        attempt: { ...attempt, outcome: 'running' },
        confirmation: null,
        error: null,
        notice: null,
      });
      let created: string | null = null;
      try {
        const receipt = await journalClient.command(
          attempt.tradeId,
          attempt.command,
          attempt.key,
          attempt.actor,
        );
        if (!validContext()) return;
        const confirmed: Attempt = { ...attempt, outcome: 'confirmed', receipt };
        update({ attempt: confirmed });
        created = await load(false, confirmed);
      } catch (error) {
        if (!validContext()) return;
        const rejected = error instanceof MarketApiError && error.status < 500;
        update({
          attempt: rejected ? null : { ...attempt, outcome: 'unknown' },
          readState: 'error',
          error: commandError(error),
        });
      } finally {
        if (validContext()) {
          update({ pending: false });
          if (created) selection.current(created);
          else if (
            current.current.completedRefresh !== currentRefresh.current &&
            current.current.readState === 'ready'
          ) {
            void load(
              false,
              current.current.attempt?.outcome === 'confirmed'
                ? current.current.attempt
                : undefined,
            );
          }
        }
      }
    },
    [load, update],
  );

  const entry =
    state.history?.versions.find((item) => item.version.id === state.selectedId) ?? null;
  const dirty = hasLocalChanges(state);
  const conflict =
    state.reconcileRequired ||
    (!!state.editor && (!entry || !sameJournalVersion(state.editor.base, entry.version)));
  const ready =
    !query.error &&
    state.queryKey === query.key &&
    state.readState === 'ready' &&
    state.completedRefresh === refreshVersion;
  const canAct =
    ready && !state.pending && !state.attempt && !conflict && !contextPending.current?.();
  const confirmationValid =
    !!state.confirmation &&
    !!state.history &&
    canAct &&
    confirmationIsCurrent(state.confirmation, state.history, entry);

  function submit(command: JournalCommand) {
    const latest = current.current;
    if (
      !canAct ||
      latest.pending ||
      contextPending.current?.() ||
      latest.attempt ||
      latest.queryKey !== context.current.key ||
      latest.completedRefresh !== currentRefresh.current
    )
      return;
    if (command.operation !== 'SAVE_DRAFT' && !confirmationValid) return;
    if (command.operation === 'SAVE_DRAFT' && (!latest.editor || !hasLocalChanges(latest))) return;
    const attempt: Attempt = {
      tradeId,
      actor: snapshotJournalActor(),
      command: Object.freeze({ ...command }),
      key: `journal:${crypto.randomUUID()}`,
      base: entry?.version ?? null,
      outcome: 'running',
      receipt: null,
    };
    void perform(attempt);
  }

  return {
    state,
    entry,
    dirty,
    conflict,
    ready,
    canAct,
    confirmationValid,
    queryError: query.error,
    selectVersion: (id: string) => {
      if (!current.current.pending && !contextPending.current?.()) selection.current(id);
    },
    edit: () => {
      if (canAct && !contextPending.current?.() && entry?.version.status === 'DRAFT') {
        update({
          editor: { base: entry.version, texts: journalTexts(entry.version) },
          notice: null,
        });
      }
    },
    changeText: (field: keyof JournalTexts, value: string) => {
      const editor = current.current.editor;
      if (editor && !current.current.pending && !contextPending.current?.()) {
        update({ editor: { ...editor, texts: { ...editor.texts, [field]: value } } });
      }
    },
    cancelEdit: () => {
      if (!current.current.pending && !contextPending.current?.())
        update({
          editor: null,
          confirmation: null,
          reconcileRequired: false,
          notice: 'Gespeicherter Journalstand · Lesemodus',
        });
    },
    refresh: () => {
      if (!current.current.pending && !contextPending.current?.())
        void load(
          false,
          current.current.attempt?.outcome === 'confirmed' ? current.current.attempt : undefined,
        );
    },
    loadSaved: () => {
      if (!current.current.pending && !contextPending.current?.())
        void load(
          true,
          current.current.attempt?.outcome === 'confirmed' ? current.current.attempt : undefined,
        );
    },
    openConfirmation: (command: JournalCommand) => {
      if (!canAct || contextPending.current?.() || dirty || !state.history) return;
      update({
        confirmation: {
          command: Object.freeze({ ...command }),
          saved: entry?.version ?? null,
          copySource: state.history.versions.find((item) => item.is_latest)?.version ?? null,
          sourceCurrentness: entry?.source_currentness ?? null,
          handoff: { ...state.history.handoff },
        },
      });
    },
    cancelConfirmation: () => {
      if (!current.current.pending && !contextPending.current?.()) update({ confirmation: null });
    },
    save: () => {
      const editor = current.current.editor;
      if (editor)
        submit({
          operation: 'SAVE_DRAFT',
          version_id: editor.base.id,
          expected_edit_revision: editor.base.edit_revision,
          ...editor.texts,
        });
    },
    confirm: () => {
      if (current.current.confirmation) submit(current.current.confirmation.command);
    },
    retry: () => {
      const attempt = current.current.attempt;
      if (
        attempt?.outcome === 'unknown' &&
        !current.current.pending &&
        !contextPending.current?.() &&
        !context.current.error &&
        current.current.queryKey === context.current.key
      )
        void perform(attempt);
    },
  };
}
