import { useCallback, useContext, useEffect, useRef } from 'react';
import { UNSAFE_DataRouterContext, useBeforeUnload, useBlocker } from 'react-router-dom';

interface GuardProps {
  shouldBlock: () => boolean;
  busy?: boolean;
  onDiscard?: () => void;
}

function RouteGuard({ shouldBlock, busy, onDiscard }: GuardProps) {
  const stayButton = useRef<HTMLButtonElement>(null);
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      shouldBlock() &&
      (currentLocation.pathname !== nextLocation.pathname ||
        currentLocation.search !== nextLocation.search),
  );

  useEffect(() => {
    if (blocker.state !== 'blocked') return;
    const previousFocus = document.activeElement;
    stayButton.current?.focus();
    return () => {
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) previousFocus.focus();
    };
  }, [blocker.state]);

  if (blocker.state !== 'blocked') return null;
  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center bg-black/70 p-3 pt-8">
      <section
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="pending-navigation-title"
        className="w-full max-w-xl space-y-3 rounded-xl border border-amber-700 bg-slate-950 p-5 shadow-xl"
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            event.stopPropagation();
            blocker.reset();
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
        <h2 id="pending-navigation-title" className="font-semibold">
          {busy ? 'Speicherung läuft' : 'Ungespeicherte Änderungen'}
        </h2>
        <p className="text-sm">
          {busy
            ? 'Bitte den Abschluss abwarten, bevor du den Kontext wechselst.'
            : 'Möchtest du die Eingaben verwerfen und den gewählten Kontext öffnen?'}
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            ref={stayButton}
            type="button"
            onClick={() => blocker.reset()}
            className="rounded-lg border px-3 py-2"
          >
            Hier bleiben
          </button>
          {!busy && (
            <button
              type="button"
              onClick={() => {
                onDiscard?.();
                blocker.proceed();
              }}
              className="rounded-lg border border-amber-700 px-3 py-2"
            >
              Eingaben verwerfen und wechseln
            </button>
          )}
        </div>
      </section>
    </div>
  );
}

/** Protect pending input on route changes and native unload without storing another draft. */
export function PendingNavigationGuard({ shouldBlock, busy, onDiscard }: GuardProps) {
  const dataRouter = useContext(UNSAFE_DataRouterContext);
  useBeforeUnload(
    useCallback(
      (event) => {
        if (!shouldBlock()) return;
        event.preventDefault();
        event.returnValue = '';
      },
      [shouldBlock],
    ),
  );
  return dataRouter ? (
    <RouteGuard shouldBlock={shouldBlock} busy={busy} onDiscard={onDiscard} />
  ) : null;
}
