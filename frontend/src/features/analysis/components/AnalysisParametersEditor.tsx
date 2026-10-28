import { numericAnalysisFields, type AnalysisDraft } from '../services/analysisSetupDraft';

const inputClass = 'mt-1 w-full min-w-0 rounded border border-slate-600 bg-slate-950 p-2';

export function AnalysisParametersEditor({
  draft,
  onChange,
  disabled,
}: {
  draft: AnalysisDraft;
  onChange: (patch: Partial<AnalysisDraft>) => void;
  disabled: boolean;
}) {
  return (
    <fieldset disabled={disabled} className="min-w-0 space-y-4">
      <legend className="mb-3 text-lg font-medium">Zeitraum und Analyseparameter</legend>
      <div className="grid min-w-0 gap-4 sm:grid-cols-2">
        <label className="min-w-0 text-sm">
          Von
          <input
            required
            type="date"
            value={draft.start_date}
            max={draft.end_date || undefined}
            onChange={(event) => onChange({ start_date: event.target.value })}
            className={inputClass}
          />
        </label>
        <label className="min-w-0 text-sm">
          Bis
          <input
            required
            type="date"
            value={draft.end_date}
            min={draft.start_date || undefined}
            onChange={(event) => onChange({ end_date: event.target.value })}
            className={inputClass}
          />
        </label>
        <label className="min-w-0 text-sm">
          Kursfeld
          <select
            value={draft.price_field}
            onChange={(event) => onChange({ price_field: event.target.value })}
            className={inputClass}
          >
            <option value="ADJUSTED_CLOSE">Bereinigter Schlusskurs (ADJUSTED_CLOSE)</option>
            <option value="CLOSE">Schlusskurs (CLOSE)</option>
          </select>
        </label>
        {numericAnalysisFields.map(([field, label]) => (
          <label key={field} className="min-w-0 text-sm">
            {label}
            <input
              required
              type="number"
              step="1"
              min={field === 'maximum_data_age_days' || field === 'rounding_scale' ? 0 : 1}
              max={field === 'rounding_scale' ? 12 : undefined}
              value={draft[field]}
              onChange={(event) => onChange({ [field]: event.target.value })}
              className={inputClass}
            />
          </label>
        ))}
        <label className="min-w-0 text-sm">
          Momentumfenster (aufsteigend, mit Kommas)
          <input
            value={draft.momentum_windows}
            onChange={(event) => onChange({ momentum_windows: event.target.value })}
            className={inputClass}
          />
        </label>
        <label className="min-w-0 text-sm">
          Annualisierungsfaktor
          <input
            required
            inputMode="decimal"
            value={draft.annualization_factor}
            onChange={(event) => onChange({ annualization_factor: event.target.value })}
            className={inputClass}
          />
        </label>
      </div>
      <p className="text-sm text-slate-400">
        Alle angezeigten Parameter werden mit dem neuen Lauf gespeichert. Ausgewertet werden
        ausschließlich bereits gespeicherte Marktdaten für den bestätigten Zeitraum.
      </p>
    </fieldset>
  );
}
