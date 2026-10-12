import { useEffect, useRef, useState } from 'react';
import { MarketApiError } from '../../market/services/http';
import { ivApi, ivLabel } from '../services/iv';
import type { IvModelForm, IvModelResult } from '../types/iv';

const empty: IvModelForm = {
  scope: '',
  direction: 'CALL',
  currency: 'EUR',
  mode: 'iv',
  spot: '',
  strike: '',
  ratio: '',
  remaining_days: '',
  iv_percent: '',
  calibration_price: '',
  rate_percent: '',
  dividend_yield_percent: '',
  quantity: '',
  underlying_change_percent: '',
  iv_change_pp: '',
  elapsed_days: '',
};
const example: IvModelForm = {
  ...empty,
  spot: '100',
  strike: '100',
  ratio: '0.1',
  remaining_days: '90',
  iv_percent: '35',
  rate_percent: '2',
  dividend_yield_percent: '0',
  quantity: '100',
  underlying_change_percent: '-5',
  iv_change_pp: '-5',
  elapsed_days: '7',
};
const fields = {
  spot: 'Basiswertkurs (Währungseinheiten)',
  strike: 'Basispreis (Währungseinheiten)',
  ratio: 'Bezugsverhältnis (Basiswerteinheiten je Schein)',
  remaining_days: 'Restlaufzeit (Kalendertage)',
  rate_percent: 'Zins (% p. a., stetig)',
  dividend_yield_percent: 'Dividendenrendite (% p. a., stetig)',
  quantity: 'Stückzahl (Annahme)',
  underlying_change_percent: 'Basiswertänderung (relative %)',
  iv_change_pp: 'IV-Änderung (Prozentpunkte)',
  elapsed_days: 'Szenariohorizont (Kalendertage)',
} as const;

function readForm(key: string): IvModelForm {
  try {
    const saved: unknown = JSON.parse(sessionStorage.getItem(key) ?? 'null');
    if (saved && typeof saved === 'object') {
      const candidate = saved as Record<string, unknown>;
      if (
        Object.keys(empty).every((field) => typeof candidate[field] === 'string') &&
        ['CALL', 'PUT'].includes(String(candidate.direction)) &&
        ['iv', 'price'].includes(String(candidate.mode))
      )
        return candidate as unknown as IvModelForm;
    }
  } catch {
    /* Unavailable or invalid storage is not evidence. */
  }
  return { ...empty };
}

export function IvModelCalculator({ tradeId }: { tradeId: string }) {
  const key = `iv-assumptions-v1:${tradeId}`;
  const [form, setForm] = useState<IvModelForm>(() => readForm(key));
  const [result, setResult] = useState<IvModelResult | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);
  function change(next: IvModelForm) {
    active.current?.abort();
    active.current = null;
    setBusy(false);
    setForm(next);
    setResult(null);
    setError('');
    try {
      sessionStorage.setItem(key, JSON.stringify(next));
    } catch {
      /* Optional convenience. */
    }
  }
  async function calculate() {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setBusy(true);
    setError('');
    setResult(null);
    try {
      const value = await ivApi.preview(form, controller.signal);
      if (!controller.signal.aborted) setResult(value);
    } catch (cause) {
      if (!controller.signal.aborted)
        setError(
          cause instanceof MarketApiError
            ? (ivLabel(cause.response.message) ??
                'Eingaben prüfen: Werte fehlen oder das Modell unterstützt diesen Fall nicht.')
            : 'Modellrechnung nicht erreichbar. Es liegt kein neues Ergebnis vor.',
        );
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  const inputClass = 'block w-full min-w-0 rounded border border-slate-600 bg-slate-950 p-2';
  const money = (value: string | null) =>
    value === null
      ? 'Nicht berechenbar'
      : `${new Intl.NumberFormat('de-DE', { maximumFractionDigits: 6 }).format(Number(value))} ${result?.inputs.currency ?? ''}`;
  return (
    <details className="min-w-0 space-y-3 rounded border border-slate-700 p-3">
      <summary className="cursor-pointer font-semibold">
        Modelllabor: IV-Szenario mit eigenen Annahmen
      </summary>
      <p>
        Alle Eingaben sind hypothetisch und werden nicht als aktuelle Positionsdaten übernommen. Nur
        europäische Vanilla-Calls/Puts ohne Quanto, mit gleicher Währung und kontinuierlicher
        Dividendenrendite. Amerikanische Ausübung, diskrete Dividenden und strukturierte Produkte
        sind ausgeschlossen.
      </p>
      <p>
        Schätzungen von Zins und Dividenden sind erforderlich; null darf nur eine bewusste Annahme
        sein. Die Eingaben bleiben für diese Position in dieser Browsersitzung erhalten.
      </p>
      <button
        type="button"
        className="rounded border px-3 py-2"
        onClick={() => change({ ...example })}
      >
        Beispielannahmen laden
      </button>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void calculate();
        }}
        className="space-y-3"
      >
        <label className="block">
          Modellgeltung ausdrücklich wählen
          <select
            required
            className={inputClass}
            value={form.scope}
            onChange={(e) => change({ ...form, scope: e.target.value })}
          >
            <option value="">Bitte wählen</option>
            <option value="EUROPEAN">Europäischer Vanilla-Schein, kein FX/Quanto</option>
          </select>
        </label>
        <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <label>
            Richtung
            <select
              className={inputClass}
              value={form.direction}
              onChange={(e) => change({ ...form, direction: e.target.value as 'CALL' | 'PUT' })}
            >
              <option value="CALL">Call</option>
              <option value="PUT">Put</option>
            </select>
          </label>
          <label>
            Gemeinsame Währung (keine Umrechnung)
            <input
              required
              pattern="[A-Z]{3}"
              maxLength={3}
              className={inputClass}
              value={form.currency}
              onChange={(e) => change({ ...form, currency: e.target.value.toUpperCase() })}
            />
          </label>
          <label>
            IV-Grundlage (Annahme)
            <select
              className={inputClass}
              value={form.mode}
              onChange={(e) => change({ ...form, mode: e.target.value as 'iv' | 'price' })}
            >
              <option value="iv">IV vorgeben (%)</option>
              <option value="price">Aus hypothetischem Preis ableiten</option>
            </select>
          </label>
          {Object.entries({
            ...fields,
            ...(form.mode === 'iv'
              ? { iv_percent: 'IV-Annahme (% p. a.)' }
              : { calibration_price: 'Hypothetischer Preis je Schein' }),
          }).map(([field, label]) => (
            <label key={field} className="min-w-0">
              {label}
              <input
                required
                type="number"
                step="any"
                className={inputClass}
                value={form[field as keyof IvModelForm]}
                onChange={(e) => change({ ...form, [field]: e.target.value })}
              />
            </label>
          ))}
        </div>
        <p>
          35 % → 30 % bedeutet −5 Prozentpunkte, relativ etwa −14,29 %. Bezugsverhältnis und
          Stückzahl werden jeweils genau einmal berücksichtigt.
        </p>
        <button
          type="submit"
          disabled={busy}
          className="rounded border px-3 py-2 disabled:opacity-50"
        >
          {busy ? 'Modell wird berechnet …' : 'Annahmen berechnen'}
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
      {result && (
        <section
          aria-label="Hypothetisches IV-Ergebnis"
          className="min-w-0 space-y-2 break-words"
          aria-live="polite"
        >
          <h5 className="font-semibold">Hypothetische Modellrechnung · kein Verkaufserlös</h5>
          <p>
            {result.model_version} · IV{' '}
            {new Intl.NumberFormat('de-DE', { style: 'percent', maximumFractionDigits: 3 }).format(
              Number(result.inputs.iv_decimal),
            )}{' '}
            (
            {result.iv_origin === 'USER_ASSUMPTION'
              ? 'Eingabeannahme'
              : 'aus hypothetischem Preis berechnet'}
            )
          </p>
          <dl className="grid gap-3 sm:grid-cols-2">
            {[
              ['Modellpreis heute je Schein', result.baseline_price],
              ['Modellpreis im Szenario je Schein', result.scenario_price],
              ['Kombinierte Änderung je Schein', result.change_per_warrant],
              ['Kombinierte Änderung für die angenommene Stückzahl', result.position_change],
              ['Vega je Schein und IV-Prozentpunkt', result.vega_per_warrant_per_pp],
              ['Vega für die Stückzahl je IV-Prozentpunkt', result.position_vega_per_pp],
              ['Isolierter IV-Effekt je Schein (Neubewertung)', result.isolated_iv_change],
              ['Isolierter IV-Effekt je Schein (lokale Näherung)', result.local_iv_change],
              ['Isolierter Basiswerteffekt je Schein', result.isolated_spot_change],
              ['Isolierter Zeiteffekt je Schein', result.isolated_time_change],
            ].map(([label, value]) => (
              <div key={label} className="min-w-0">
                <dt className="text-slate-400">{label}</dt>
                <dd>{money(value)}</dd>
              </div>
            ))}
          </dl>
          {result.warnings.map((warning) => (
            <p key={warning}>{ivLabel(warning) ?? warning}</p>
          ))}
          <p>
            Negative Änderungen sind Modellverluste. Isolierte Effekte sind wegen Wechselwirkungen
            nicht additiv. Vega ist eine lokale Ableitung, keine Verlustobergrenze. Das kombinierte
            Szenario verwendet vollständige Neubewertung mit unverändertem Zins und unveränderter
            Dividendenrendite.
          </p>
          <p>
            Spread, Gebühren, Emittentenrisiko und tatsächliche Ausführbarkeit sind nicht enthalten.
            Keine Eintrittswahrscheinlichkeit, keine Kauf-/Verkaufsempfehlung und keine Änderung von
            Stops, Zielen oder Benachrichtigungen.
          </p>
        </section>
      )}
    </details>
  );
}
