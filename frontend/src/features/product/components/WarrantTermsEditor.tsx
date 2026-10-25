import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from 'react';
import { MarketApiError, MarketTransportError } from '../../market/services/http';
import type { WarrantDetailSnapshot } from '../services/adminContext';
import type { AddWarrantTermsRequest, OptionDirection, WarrantTermsResponse } from '../types/api';
import { StrikeCurrencyInput } from './StrikeCurrencyInput';

function formFromTerms(terms: WarrantTermsResponse) {
  return {
    option_direction: terms.option_direction,
    strike: terms.strike,
    strike_currency_code: terms.strike_currency_code ?? '',
    maturity_date: terms.maturity_date,
    ratio: terms.ratio,
  };
}

export function WarrantTermsValues({ terms }: { terms: WarrantTermsResponse }) {
  return (
    <dl className="grid grid-cols-2 gap-x-5 gap-y-3 text-sm sm:grid-cols-3">
      <div>
        <dt className="text-slate-400">Richtung</dt>
        <dd>{terms.option_direction}</dd>
      </div>
      <div>
        <dt className="text-slate-400">Strike</dt>
        <dd className="break-words">
          {terms.strike} {terms.strike_currency_code ?? '(Währung ungeklärt)'}
        </dd>
      </div>
      <div>
        <dt className="text-slate-400">Bezugsverhältnis</dt>
        <dd className="break-words">{terms.ratio}</dd>
      </div>
      <div>
        <dt className="text-slate-400">Fälligkeit</dt>
        <dd>{terms.maturity_date}</dd>
      </div>
      <div>
        <dt className="text-slate-400">Bedingungsversion</dt>
        <dd>{terms.version_no}</dd>
      </div>
      <div>
        <dt className="text-slate-400">Gültig ab</dt>
        <dd>{new Date(terms.effective_from).toLocaleString('de-DE')}</dd>
      </div>
      {terms.effective_to && (
        <div>
          <dt className="text-slate-400">Gültig bis</dt>
          <dd>{new Date(terms.effective_to).toLocaleString('de-DE')}</dd>
        </div>
      )}
    </dl>
  );
}

export function WarrantTermsEditor({
  snapshot,
  onSave,
  onCancel,
  onDirtyChange,
  onCompare,
  onBasisChanged,
  busy,
}: {
  snapshot: WarrantDetailSnapshot & { currentTerms: WarrantTermsResponse };
  onSave: (productId: string, request: AddWarrantTermsRequest) => Promise<void>;
  onCancel: () => void;
  onDirtyChange: (dirty: boolean) => void;
  onCompare: () => Promise<WarrantDetailSnapshot>;
  onBasisChanged: (snapshot: WarrantDetailSnapshot) => void;
  busy: boolean;
}) {
  // This immutable basis belongs to this editor instance, never to refreshed props.
  const [basis, setBasis] = useState(snapshot);
  const [form, setForm] = useState(() => formFromTerms(snapshot.currentTerms));
  const [error, setError] = useState('');
  const [comparison, setComparison] = useState<WarrantDetailSnapshot | null>(null);
  const [comparing, setComparing] = useState(false);
  const submitting = useRef(false);
  const alive = useRef(true);
  const directionInput = useRef<HTMLSelectElement>(null);
  const dirty = JSON.stringify(form) !== JSON.stringify(formFromTerms(basis.currentTerms));
  useEffect(() => {
    directionInput.current?.focus();
  }, [basis]);
  useEffect(() => {
    onDirtyChange(dirty);
  }, [dirty, onDirtyChange]);
  useLayoutEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (submitting.current || busy || comparing) return;
    submitting.current = true;
    setError('');
    try {
      await onSave(basis.warrant.id, {
        ...form,
        strike_currency_code: form.strike_currency_code || null,
        expected_version: basis.warrant.version,
      });
    } catch (cause) {
      if (alive.current) {
        setError(
          cause instanceof MarketApiError &&
            cause.response.code === 'WARRANT_CONCURRENT_MODIFICATION'
            ? `Versionskonflikt: ${cause.message} Ihre Eingaben und die Ausgangsversion bleiben erhalten. Bitte den aktuellen Stand bewusst laden und prüfen.`
            : cause instanceof MarketTransportError
              ? 'Speichererfolg unklar. Bitte den gespeicherten Stand prüfen, bevor Sie erneut speichern. Ihre Eingaben bleiben erhalten.'
              : cause instanceof Error
                ? cause.message
                : 'Produktbedingungen konnten nicht gespeichert werden.',
        );
      }
    } finally {
      submitting.current = false;
    }
  }

  async function compare() {
    if (comparing || submitting.current) return;
    setComparing(true);
    try {
      const next = await onCompare();
      if (!alive.current) return;
      if (!next.currentTerms) throw new Error(next.termsError ?? 'Aktuelle Bedingungen fehlen.');
      setComparison(next);
    } catch (cause) {
      if (alive.current)
        setError(
          cause instanceof Error
            ? cause.message
            : 'Aktueller Stand konnte nicht geladen werden. Der Entwurf bleibt erhalten.',
        );
    } finally {
      if (alive.current) setComparing(false);
    }
  }

  function adoptComparison() {
    if (
      !comparison?.currentTerms ||
      !window.confirm(
        'Den bisherigen Entwurf verwerfen und die geladenen aktuellen Bedingungen als neue Ausgangsbasis übernehmen? Bitte anschließend Änderungen erneut prüfen.',
      )
    )
      return;
    setBasis({ ...comparison, currentTerms: comparison.currentTerms });
    setForm(formFromTerms(comparison.currentTerms));
    onBasisChanged(comparison);
    setComparison(null);
    setError('');
  }

  const cls = 'mt-1 w-full min-w-0 rounded border border-slate-700 bg-slate-950 p-2 text-sm';
  return (
    <form
      onSubmit={(event) => void save(event)}
      aria-label="Produktbedingungen ändern"
      className="space-y-4"
    >
      <p className="text-sm text-slate-400">
        Ausgangsbasis: Produktversion {basis.warrant.version}, Bedingungsversion{' '}
        {basis.currentTerms.version_no}. Nur gewünschte Felder ändern; gespeichert wird eine
        vollständige neue Version.
      </p>
      <fieldset disabled={busy || comparing} className="grid min-w-0 gap-3 sm:grid-cols-2">
        <label>
          Neue Richtung
          <select
            ref={directionInput}
            autoFocus
            value={form.option_direction}
            onChange={(event) =>
              setForm({ ...form, option_direction: event.target.value as OptionDirection })
            }
            className={cls}
          >
            <option>CALL</option>
            <option>PUT</option>
          </select>
        </label>
        <label>
          Neuer Strike
          <input
            required
            inputMode="decimal"
            value={form.strike}
            onChange={(event) => setForm({ ...form, strike: event.target.value })}
            className={cls}
          />
        </label>
        <StrikeCurrencyInput
          label="Neue Strike-Währung"
          value={form.strike_currency_code}
          onChange={(value) => setForm({ ...form, strike_currency_code: value })}
        />
        <label>
          Neue Fälligkeit
          <input
            required
            type="date"
            value={form.maturity_date}
            onChange={(event) => setForm({ ...form, maturity_date: event.target.value })}
            className={cls}
          />
        </label>
        <label>
          Neues Bezugsverhältnis
          <input
            required
            inputMode="decimal"
            value={form.ratio}
            onChange={(event) => setForm({ ...form, ratio: event.target.value })}
            className={cls}
          />
        </label>
      </fieldset>
      {error && (
        <p role="alert" className="rounded border border-rose-800 p-3 text-sm">
          {error}
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <button
          disabled={busy || comparing}
          className="rounded bg-sky-800 px-3 py-2 text-sm disabled:opacity-50"
        >
          Neue Terms-Version
        </button>
        <button
          type="button"
          disabled={busy || comparing}
          onClick={onCancel}
          className="rounded border border-slate-700 px-3 py-2 text-sm"
        >
          Bedingungen abbrechen
        </button>
        <button
          type="button"
          disabled={busy || comparing}
          onClick={() => void compare()}
          className="rounded border border-slate-700 px-3 py-2 text-sm"
        >
          Aktuellen Stand zum Vergleich laden
        </button>
      </div>
      {comparison?.currentTerms && (
        <section
          aria-label="Aktueller Stand zum Vergleich"
          className="space-y-3 rounded border border-amber-700 p-4"
        >
          <h4 className="font-medium">
            Geladener aktueller Stand · Produktversion {comparison.warrant.version}
          </h4>
          <p className="text-sm">
            Ihr Entwurf oben bleibt unverändert. Prüfen Sie die Abweichungen; eine Übernahme ersetzt
            den Entwurf und löst keine Speicherung aus.
          </p>
          <WarrantTermsValues terms={comparison.currentTerms} />
          <button
            type="button"
            disabled={busy || comparing}
            onClick={adoptComparison}
            className="rounded border border-amber-700 px-3 py-2 text-sm"
          >
            Aktuellen Stand als Ausgangsbasis übernehmen
          </button>
        </section>
      )}
    </form>
  );
}
