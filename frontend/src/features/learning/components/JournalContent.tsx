import { useEffect, useRef, type ReactNode } from 'react';
import type { JournalTexts } from '../services/journalClient';
import { journalFields } from './journalViewState';

export const journalButton =
  'rounded border border-slate-600 px-3 py-2 text-sm disabled:opacity-50';

export function JournalTextsView({
  value,
  finalized = false,
}: {
  value: JournalTexts;
  finalized?: boolean;
}) {
  return (
    <div className="space-y-3" aria-label="Gespeicherte Journaltexte">
      {journalFields.map(([field, label]) => (
        <div key={field}>
          <h4 className="text-sm text-slate-400">{label}</h4>
          <p className="whitespace-pre-wrap break-words">
            {value[field]?.trim() ? value[field] : 'Nicht ausgefüllt'}
          </p>
        </div>
      ))}
      {journalFields.every(([field]) => !value[field]?.trim()) && (
        <p className="text-amber-300">
          {finalized
            ? 'Inhaltsleerer Abschluss – keine persönliche Bewertung dokumentiert.'
            : 'Alle drei optionalen Journalfelder sind leer.'}
        </p>
      )}
    </div>
  );
}

/** The confirmation occupies the journal's content area; there is no second full-text preview. */
export function JournalDialog({
  title,
  children,
  onCancel,
  onConfirm,
  confirmLabel = 'Journalaktion bestätigen',
  disabled = false,
  busy = false,
  returnFocusLabel,
}: {
  title: string;
  children: ReactNode;
  onCancel: () => void;
  onConfirm: () => void;
  confirmLabel?: string;
  disabled?: boolean;
  busy?: boolean;
  returnFocusLabel?: string;
}) {
  const cancel = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const previousFocus = document.activeElement;
    const scope = cancel.current?.closest('section[aria-label="Trade-Journal"]');
    const previousLabel = returnFocusLabel ?? previousFocus?.textContent;
    cancel.current?.focus();
    return () => {
      if (
        !returnFocusLabel &&
        previousFocus instanceof HTMLElement &&
        previousFocus !== document.body &&
        previousFocus.isConnected
      )
        previousFocus.focus();
      else if (scope?.isConnected) {
        const replacement = Array.from(scope.querySelectorAll('button')).find(
          (item) => item.textContent === previousLabel,
        );
        (replacement ?? scope.querySelector<HTMLElement>('select, h2'))?.focus();
      }
    };
  }, [returnFocusLabel]);
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Journalaktion bestätigen"
      className="space-y-4 rounded border border-amber-600 p-4"
      onKeyDown={(event) => {
        if (event.key === 'Escape' && !busy) {
          event.preventDefault();
          event.stopPropagation();
          onCancel();
        }
        if (event.key === 'Tab') {
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
        }
      }}
    >
      <h3 className="font-semibold">{title}</h3>
      {children}
      <div className="flex flex-wrap gap-3">
        <button
          ref={cancel}
          type="button"
          className={journalButton}
          disabled={busy}
          onClick={onCancel}
        >
          Abbrechen
        </button>
        <button
          type="button"
          className={journalButton}
          disabled={disabled || busy}
          onClick={onConfirm}
        >
          {confirmLabel}
        </button>
      </div>
    </div>
  );
}
