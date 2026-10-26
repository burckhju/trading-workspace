import type { EntryType, TradePlanContentRequest } from '../types/api';

const inputClass = 'mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2';

function ContentField({
  label,
  value,
  onChange,
  required = false,
  decimal = false,
  multiline = false,
  placeholder,
}: {
  label: string;
  value?: string | number | null;
  onChange: (value: string) => void;
  required?: boolean;
  decimal?: boolean;
  multiline?: boolean;
  placeholder?: string;
}) {
  return (
    <label className="block min-w-0 text-sm">
      <span className="text-slate-300">{label}</span>
      {multiline ? (
        <textarea
          required={required}
          rows={3}
          className={inputClass}
          value={value ?? ''}
          onChange={(event) => onChange(event.target.value)}
        />
      ) : (
        <input
          required={required}
          inputMode={decimal ? 'decimal' : undefined}
          className={inputClass}
          value={value ?? ''}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
    </label>
  );
}

/** Controlled content shared by creation and amendments; decimal strings stay strings. */
export function TradePlanContentForm({
  value,
  onChange,
  disabled = false,
}: {
  value: TradePlanContentRequest;
  onChange: (value: TradePlanContentRequest) => void;
  disabled?: boolean;
}) {
  const entry = value.entry;
  const updateEntry = (change: Partial<TradePlanContentRequest['entry']>) =>
    onChange({ ...value, entry: { ...entry, ...change } });
  const updateInvalidation = (change: Partial<TradePlanContentRequest['invalidation']>) =>
    onChange({ ...value, invalidation: { ...value.invalidation, ...change } });
  const updateRisk = (change: Partial<TradePlanContentRequest['risk_assumptions']>) =>
    onChange({ ...value, risk_assumptions: { ...value.risk_assumptions, ...change } });

  function changeEntryType(type: EntryType) {
    updateEntry({
      type,
      price: type === 'PRICE' ? (entry.price ?? '') : null,
      price_from: type === 'PRICE_RANGE' ? (entry.price_from ?? '') : null,
      price_to: type === 'PRICE_RANGE' ? (entry.price_to ?? '') : null,
      trigger: type === 'TRIGGER' ? (entry.trigger ?? '') : null,
    });
  }

  return (
    <fieldset disabled={disabled} className="min-w-0 space-y-5 disabled:opacity-60">
      <legend className="sr-only">Planinhalt</legend>
      <ContentField
        label="Trade Thesis"
        value={value.thesis}
        onChange={(thesis) => onChange({ ...value, thesis })}
        required
        multiline
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="text-slate-300">Entry-Art</span>
          <select
            className={inputClass}
            value={entry.type}
            onChange={(event) => changeEntryType(event.target.value as EntryType)}
          >
            <option value="PRICE">Preis</option>
            <option value="PRICE_RANGE">Preisbereich</option>
            <option value="TRIGGER">Trigger</option>
          </select>
        </label>
        <ContentField
          label="Währung"
          value={entry.currency}
          onChange={(currency) => updateEntry({ currency })}
          required
        />
      </div>
      <p className="text-xs text-slate-400">
        Die Planwährung bezieht sich auf den Basiswert. Beim Wechsel der Entry-Art werden die
        bisherigen Preis- beziehungsweise Triggerfelder ersetzt.
      </p>
      {entry.type === 'PRICE' && (
        <ContentField
          label="Entry-Preis"
          value={entry.price}
          onChange={(price) => updateEntry({ price })}
          required
          decimal
        />
      )}
      {entry.type === 'PRICE_RANGE' && (
        <div className="grid gap-3 sm:grid-cols-2">
          <ContentField
            label="Preis von"
            value={entry.price_from}
            onChange={(price_from) => updateEntry({ price_from })}
            required
            decimal
          />
          <ContentField
            label="Preis bis"
            value={entry.price_to}
            onChange={(price_to) => updateEntry({ price_to })}
            required
            decimal
          />
        </div>
      )}
      {entry.type === 'TRIGGER' && (
        <ContentField
          label="Trigger"
          value={entry.trigger}
          onChange={(trigger) => updateEntry({ trigger })}
          required
          multiline
        />
      )}
      <details className="rounded-lg border border-slate-800 p-3">
        <summary className="cursor-pointer text-sm">Weitere Entry-Angaben</summary>
        <div className="mt-3 space-y-3">
          <ContentField
            label="Referenzpreis"
            value={entry.reference_price}
            onChange={(reference_price) =>
              updateEntry({ reference_price: reference_price || null })
            }
            decimal
          />
          <ContentField
            label="Gültig bis (ISO 8601 mit Zeitzone)"
            value={entry.valid_until}
            onChange={(valid_until) => updateEntry({ valid_until: valid_until || null })}
            placeholder="z. B. 2026-12-31T16:00:00Z"
          />
          <ContentField
            label="Entry-Begründung"
            value={entry.rationale}
            onChange={(rationale) => updateEntry({ rationale: rationale || null })}
            multiline
          />
        </div>
      </details>
      <div className="grid gap-3 sm:grid-cols-2">
        <ContentField
          label="Technischer Stop"
          value={value.invalidation.stop_price}
          onChange={(stop_price) => updateInvalidation({ stop_price: stop_price || null })}
          decimal
        />
        <ContentField
          label="Invalidierungsregel"
          value={value.invalidation.invalidation_rule}
          onChange={(invalidation_rule) =>
            updateInvalidation({ invalidation_rule: invalidation_rule || null })
          }
        />
      </div>
      <ContentField
        label="Invalidierungsbegründung"
        value={value.invalidation.rationale}
        onChange={(rationale) => updateInvalidation({ rationale: rationale || null })}
        multiline
      />
      <section className="space-y-3" aria-label="Kursziele">
        <h3 className="font-medium">Kursziele</h3>
        {value.targets.map((target, index) => (
          <div key={target.sequence} className="space-y-2 rounded-lg border border-slate-800 p-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <ContentField
                label={`Target ${target.sequence}`}
                value={target.price}
                onChange={(price) =>
                  onChange({
                    ...value,
                    targets: value.targets.map((item, position) =>
                      position === index ? { ...item, price } : item,
                    ),
                  })
                }
                required
                decimal
              />
              <ContentField
                label={`Target-Begründung ${target.sequence}`}
                value={target.rationale}
                onChange={(rationale) =>
                  onChange({
                    ...value,
                    targets: value.targets.map((item, position) =>
                      position === index ? { ...item, rationale: rationale || null } : item,
                    ),
                  })
                }
              />
            </div>
            {value.targets.length > 1 && (
              <button
                type="button"
                className="rounded border border-slate-700 px-3 py-1 text-sm"
                onClick={() =>
                  onChange({
                    ...value,
                    targets: value.targets
                      .filter((_, position) => position !== index)
                      .map((item, position) => ({ ...item, sequence: position + 1 })),
                  })
                }
              >
                Target {target.sequence} entfernen
              </button>
            )}
          </div>
        ))}
        <button
          type="button"
          className="rounded-lg border border-slate-700 px-3 py-2 text-sm"
          onClick={() =>
            onChange({
              ...value,
              targets: [...value.targets, { sequence: value.targets.length + 1, price: '' }],
            })
          }
        >
          Target hinzufügen
        </button>
      </section>
      <ContentField
        label="Plan-Risiko / Annahme"
        value={value.risk_assumptions.thesis_risk}
        onChange={(thesis_risk) => updateRisk({ thesis_risk })}
        required
        multiline
      />
      <details className="rounded-lg border border-slate-800 p-3">
        <summary className="cursor-pointer text-sm">Weitere Risikoangaben</summary>
        <div className="mt-3 space-y-3">
          <ContentField
            label="Max-Loss-Annahme (optional)"
            value={value.risk_assumptions.max_loss_assumption}
            onChange={(max_loss_assumption) =>
              updateRisk({ max_loss_assumption: max_loss_assumption || null })
            }
          />
          <ContentField
            label="Risk Notes"
            value={value.risk_assumptions.notes}
            onChange={(notes) => updateRisk({ notes: notes || null })}
            multiline
          />
        </div>
      </details>
    </fieldset>
  );
}
