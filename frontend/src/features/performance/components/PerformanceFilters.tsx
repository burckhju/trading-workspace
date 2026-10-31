import type { RefObject } from 'react';

import type { ReportFilterErrors } from '../services/performanceReportContext';
import type { RealizedGrossFilters } from '../types/api';

type EditableFilter = Exclude<keyof RealizedGrossFilters, 'report_currency'>;
const inputClass =
  'mt-1 block w-full min-w-0 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400';
const fields = [
  { name: 'from_date', label: 'Von (einschließlich)', type: 'date' },
  { name: 'to_date', label: 'Bis (einschließlich)', type: 'date' },
  { name: 'report_timezone', label: 'Berichtszeitzone (IANA)', type: 'text' },
] as const;

export function PerformanceFilters({
  filters,
  errors,
  loading,
  formRef,
  onChange,
  onRead,
}: {
  filters: RealizedGrossFilters;
  errors: ReportFilterErrors;
  loading: boolean;
  formRef: RefObject<HTMLFormElement | null>;
  onChange: (field: EditableFilter, value: string) => void;
  onRead: () => void;
}) {
  return (
    <form
      ref={formRef}
      aria-label="Performance-Zeitraum auswählen"
      className="rounded-xl border border-slate-800 p-4 sm:p-5"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        onRead();
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {fields.map(({ name, label, type }) => (
          <div key={name} className="min-w-0 text-sm">
            <label htmlFor={`performance-${name}`}>{label}</label>
            <input
              id={`performance-${name}`}
              name={name}
              type={type}
              required
              value={filters[name]}
              autoComplete="off"
              spellCheck={false}
              list={name === 'report_timezone' ? 'performance-timezones' : undefined}
              aria-invalid={errors[name] ? true : undefined}
              aria-describedby={errors[name] ? `performance-${name}-error` : undefined}
              onChange={(event) => onChange(name, event.target.value)}
              className={inputClass}
            />
            {errors[name] && (
              <p id={`performance-${name}-error`} className="mt-1 text-sm text-amber-300">
                {errors[name]}
              </p>
            )}
          </div>
        ))}
        <label className="text-sm">
          Berichtswährung
          <input readOnly value="EUR" className={inputClass} />
        </label>
      </div>
      <datalist id="performance-timezones">
        <option value="Europe/Berlin" />
        <option value="Etc/UTC" />
        <option value="America/New_York" />
        <option value="Asia/Tokyo" />
      </datalist>
      <p className="mt-3 text-xs text-slate-400">
        Die gewählte Berichtszone bestimmt die Periodengrenzen. Die Berichtswährung ist fest Euro
        (EUR). Sie filtert belegte Währungen; sie bestätigt keine Buchung und rechnet nichts um.
      </p>
      <details className="mt-2 text-xs text-slate-400">
        <summary className="cursor-pointer">Herkunft der Berichtsauswahl</summary>
        <p className="mt-2">
          Ein eindeutiger Berichtskontext im Link übernimmt dessen Zeitraum und Berichtszone. Ohne
          diesen Kontext werden die bekannte Zeitzone dieses Browsers und der aktuelle Monat bis
          heute in dieser Zone vorgeschlagen. Ist keine gültige Browserzone verfügbar, gilt
          Europe/Berlin als Vorschlag. Zeitraum und Zone bleiben bearbeitbar. „Bericht lesen“ oder
          ein bewusster Wechsel der Berichtsart übernimmt die gültige neue Auswahl.
        </p>
      </details>
      <button
        type="submit"
        disabled={loading}
        className="mt-4 rounded-lg border border-sky-700 px-3 py-2 text-sm disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
      >
        {loading ? 'Bericht wird gelesen…' : 'Bericht lesen'}
      </button>
    </form>
  );
}
