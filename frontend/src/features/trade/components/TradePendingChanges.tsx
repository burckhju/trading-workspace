import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import { PendingNavigationGuard } from '../../../components/PendingNavigationGuard';

interface Participant {
  isDirty: () => boolean;
  isBusy: () => boolean;
  onDiscard: () => void;
}

interface PendingChangesContext {
  register: (key: string, participant: Participant) => () => void;
  requestChange: (key: string, action: () => void) => void;
  notify: () => void;
  isBusy: () => boolean;
  revision: number;
}

const Context = createContext<PendingChangesContext | null>(null);

/** A booking rendered on its own owns a guard; a booking inside the page shares it. */
export function TradePendingChangesProvider({ children }: { children: ReactNode }) {
  const existing = useContext(Context);
  return existing ? children : <PendingChangesOwner>{children}</PendingChangesOwner>;
}

function PendingChangesOwner({ children }: { children: ReactNode }) {
  const participants = useRef(new Map<string, Participant>());
  const [revision, setRevision] = useState(0);
  const [pending, setPending] = useState<{ key: string; action: () => void } | null>(null);
  const stayButton = useRef<HTMLButtonElement>(null);
  const notify = useCallback(() => setRevision((revision) => revision + 1), []);
  const isBusy = useCallback(
    () => [...participants.current.values()].some((participant) => participant.isBusy()),
    [],
  );
  const shouldBlock = useCallback(
    () =>
      [...participants.current.values()].some(
        (participant) => participant.isBusy() || participant.isDirty(),
      ),
    [],
  );
  const register = useCallback(
    (key: string, participant: Participant) => {
      participants.current.set(key, participant);
      notify();
      return () => {
        if (participants.current.get(key) === participant) participants.current.delete(key);
        notify();
      };
    },
    [notify],
  );
  const requestChange = useCallback(
    (key: string, action: () => void) => {
      if (isBusy() || participants.current.get(key)?.isDirty()) setPending({ key, action });
      else action();
    },
    [isBusy],
  );
  const value = useMemo(
    () => ({ register, requestChange, notify, isBusy, revision }),
    [register, requestChange, notify, isBusy, revision],
  );

  useEffect(() => {
    if (!pending) return;
    const previous = document.activeElement;
    stayButton.current?.focus();
    return () => {
      if (previous instanceof HTMLElement && previous.isConnected) previous.focus();
    };
  }, [pending]);

  const busy = isBusy();
  return (
    <Context.Provider value={value}>
      <PendingNavigationGuard
        shouldBlock={shouldBlock}
        busy={busy}
        onDiscard={() => {
          for (const participant of participants.current.values()) participant.onDiscard();
        }}
      />
      {children}
      {pending && (
        <div className="fixed inset-0 z-[60] flex items-start justify-center bg-black/70 p-3 pt-8">
          <section
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="trade-local-pending-title"
            className="w-full max-w-xl space-y-3 rounded-xl border border-amber-700 bg-slate-950 p-5 shadow-xl"
            onKeyDown={(event) => {
              if (event.key === 'Escape') {
                event.stopPropagation();
                setPending(null);
              }
              if (event.key === 'Tab') {
                const buttons = event.currentTarget.querySelectorAll('button');
                const first = buttons[0];
                const last = buttons[buttons.length - 1];
                if (event.shiftKey && document.activeElement === first) {
                  event.preventDefault();
                  last?.focus();
                } else if (!event.shiftKey && document.activeElement === last) {
                  event.preventDefault();
                  first?.focus();
                }
              }
            }}
          >
            <h2 id="trade-local-pending-title" className="font-semibold">
              {busy ? 'Speicherung läuft' : 'Ungespeicherte Änderungen'}
            </h2>
            <p className="text-sm">
              {busy
                ? 'Bitte den Abschluss abwarten, bevor du die Buchung oder Ansicht wechselst.'
                : 'Möchtest du die Eingaben dieser Bearbeitung verwerfen und wechseln?'}
            </p>
            <div className="flex flex-wrap gap-3">
              <button
                ref={stayButton}
                type="button"
                onClick={() => setPending(null)}
                className="rounded-lg border px-3 py-2"
              >
                Hier bleiben
              </button>
              {!busy && (
                <button
                  type="button"
                  onClick={() => {
                    // Read the synchronous lock again; a write may have started since rendering.
                    if (isBusy()) {
                      notify();
                      return;
                    }
                    participants.current.get(pending.key)?.onDiscard();
                    setPending(null);
                    pending.action();
                  }}
                  className="rounded-lg border border-amber-700 px-3 py-2"
                >
                  Eingaben verwerfen und wechseln
                </button>
              )}
            </div>
          </section>
        </div>
      )}
    </Context.Provider>
  );
}

// The hook and provider intentionally share their feature-scoped context.
// eslint-disable-next-line react-refresh/only-export-components
export function useTradePendingChanges(key: string, participant: Participant) {
  const context = useContext(Context);
  const register = context?.register;
  const request = context?.requestChange;
  const announce = context?.notify;
  const checkBusy = context?.isBusy;
  const current = useRef(participant);
  current.current = participant;
  useLayoutEffect(
    () =>
      register?.(key, {
        isDirty: () => current.current.isDirty(),
        isBusy: () => current.current.isBusy(),
        onDiscard: () => current.current.onDiscard(),
      }),
    [register, key],
  );
  const requestChange = useCallback(
    (action: () => void) => {
      if (request) request(key, action);
      else action();
    },
    [request, key],
  );
  const notify = useCallback(() => announce?.(), [announce]);
  const isBusy = useCallback(() => checkBusy?.() ?? false, [checkBusy]);
  return { requestChange, notify, isBusy };
}
