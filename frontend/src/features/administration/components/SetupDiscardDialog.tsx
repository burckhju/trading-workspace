import { useEffect, useRef } from 'react';

export function SetupDiscardDialog({
  onStay,
  onDiscard,
}: {
  onStay: () => void;
  onDiscard: () => void;
}) {
  const stay = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const previous = document.activeElement;
    stay.current?.focus();
    return () => {
      if (previous instanceof HTMLElement && previous.isConnected) previous.focus();
    };
  }, []);
  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center bg-black/70 p-3 pt-8">
      <section
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="setup-discard-title"
        className="w-full max-w-xl space-y-4 rounded-xl border border-amber-700 bg-slate-950 p-5"
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            event.stopPropagation();
            onStay();
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
        <h2 id="setup-discard-title" className="font-semibold">
          Ungespeicherte Eingaben verwerfen?
        </h2>
        <p>
          Der gewählte Wechsel ersetzt den offenen Entwurf. Bereits abgeschlossene Schreibvorgänge
          werden dadurch nicht rückgängig gemacht.
        </p>
        <div className="flex flex-wrap gap-3">
          <button ref={stay} type="button" className="rounded border px-3 py-2" onClick={onStay}>
            Hier bleiben
          </button>
          <button
            type="button"
            className="rounded border border-amber-700 px-3 py-2"
            onClick={onDiscard}
          >
            Entwurf verwerfen und fortfahren
          </button>
        </div>
      </section>
    </div>
  );
}
