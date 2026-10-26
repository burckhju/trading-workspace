import { useContext, useEffect, useRef } from 'react';
import { UNSAFE_DataRouterContext, useBlocker } from 'react-router-dom';

export interface ProductFormGuard {
  dirty: boolean;
  busy: boolean;
}

export const DISCARD_PRODUCT_DRAFT =
  'Ungespeicherte Änderungen verwerfen und den aktuellen Produktkontext verlassen?';

function RouterGuard({ dirty, busy }: ProductFormGuard) {
  const blocker = useBlocker(dirty || busy);
  const stay = useRef<HTMLButtonElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (blocker.state !== 'blocked' || !dialog.current) return;
    const element = dialog.current;
    if (typeof element.showModal === 'function') element.showModal();
    else element.setAttribute('open', '');
    stay.current?.focus();
    return () => {
      if (element.open && typeof element.close === 'function') element.close();
    };
  }, [blocker.state]);
  if (blocker.state !== 'blocked') return null;
  return (
    <dialog
      ref={dialog}
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="product-leave-title"
      aria-describedby="product-leave-description"
      onCancel={(event) => {
        event.preventDefault();
        blocker.reset();
      }}
      onKeyDown={(event) => {
        if (event.key !== 'Tab') return;
        const buttons =
          event.currentTarget.querySelectorAll<HTMLButtonElement>('button:not(:disabled)');
        const first = buttons[0];
        const last = buttons[buttons.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }}
      className="m-auto w-[calc(100%-2rem)] max-w-lg space-y-4 rounded-xl border border-amber-700 bg-slate-900 p-5 text-slate-100 backdrop:bg-slate-950/80"
    >
      <h2 id="product-leave-title" className="text-lg font-semibold">
        {busy ? 'Speicherung läuft' : 'Ungespeicherte Änderungen'}
      </h2>
      <p id="product-leave-description">
        {busy ? 'Bitte den Abschluss der Speicherung abwarten.' : DISCARD_PRODUCT_DRAFT}
      </p>
      <div className="flex flex-wrap gap-3">
        <button
          ref={stay}
          type="button"
          onClick={() => blocker.reset()}
          className="rounded border px-3 py-2"
        >
          Auf dieser Seite bleiben
        </button>
        {!busy && (
          <button
            type="button"
            onClick={() => blocker.proceed()}
            className="rounded border border-amber-600 px-3 py-2"
          >
            Änderungen verwerfen und verlassen
          </button>
        )}
      </div>
    </dialog>
  );
}

/** Standalone component tests and embedded consumers need no router; the application uses a data router. */
export function ProductNavigationGuard(guard: ProductFormGuard) {
  const router = useContext(UNSAFE_DataRouterContext);
  useEffect(() => {
    if (!guard.dirty && !guard.busy) return;
    function preventUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = '';
    }
    window.addEventListener('beforeunload', preventUnload);
    return () => window.removeEventListener('beforeunload', preventUnload);
  }, [guard.dirty, guard.busy]);
  return router ? <RouterGuard {...guard} /> : null;
}
