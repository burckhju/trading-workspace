import { useEffect, useId, useRef, useState } from 'react';

import { marketApiClient } from '../../market/services/client';
import type { CurrencyResponse } from '../../market/types/api';

interface StrikeCurrencyInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
}

export function StrikeCurrencyInput({ label, value, onChange }: StrikeCurrencyInputProps) {
  const id = useId();
  const selectRef = useRef<HTMLSelectElement>(null);
  const [currencies, setCurrencies] = useState<CurrencyResponse[]>([]);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [request, setRequest] = useState(0);
  const available = currencies.some((currency) => currency.code === value);
  const invalid = Boolean(value) && (state !== 'ready' || !available);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    async function load() {
      try {
        // This existing consumer endpoint returns active currency references only.
        const response = await marketApiClient.listCurrencies(controller.signal);
        if (active) {
          setCurrencies(response.items);
          setState('ready');
        }
      } catch {
        if (active) setState('error');
      }
    }
    void load();
    return () => {
      active = false;
      controller.abort();
    };
  }, [request]);

  useEffect(() => {
    // Never silently clear a selected code when the reference request fails.
    // Keep the select enabled so native form validation blocks unavailable codes.
    selectRef.current?.setCustomValidity(
      invalid ? 'Die gewählte Strike-Währung ist nicht als aktive Referenz verfügbar.' : '',
    );
  }, [invalid]);

  function reload() {
    setState('loading');
    setCurrencies([]);
    setRequest((current) => current + 1);
  }

  return (
    <div className="text-sm">
      <label htmlFor={id}>{label}</label>
      <select
        ref={selectRef}
        id={id}
        aria-describedby={`${id}-help ${id}-status`}
        aria-busy={state === 'loading'}
        aria-invalid={invalid}
        value={value}
        onChange={(event) => {
          const code = event.target.value;
          if (!code || currencies.some((currency) => currency.code === code)) onChange(code);
        }}
        className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2 font-mono"
      >
        <option value="">Ungeklärt / keine Währungsangabe</option>
        {value && !available && (
          <option value={value} disabled>
            {value} – nicht als aktive Referenz verfügbar
          </option>
        )}
        {state === 'ready' &&
          currencies.map((currency) => (
            <option key={currency.code} value={currency.code}>
              {currency.code} – {currency.name}
            </option>
          ))}
      </select>
      <p id={`${id}-help`} className="mt-1 text-xs text-slate-400">
        Währung des Basispreises laut Produktbedingungen, nicht Handelswährung. Keine automatische
        Währungsumrechnung. Für einen Strike in Punkten keine Währung erfinden.
      </p>
      <div id={`${id}-status`} aria-live="polite" className="mt-1 text-xs text-slate-400">
        {state === 'loading' && <p>Währungsstammdaten werden geladen.</p>}
        {state === 'error' && (
          <p role="alert">Währungsstammdaten konnten nicht geladen werden.</p>
        )}
        {state === 'ready' && currencies.length === 0 && (
          <p>Keine aktiven Währungen verfügbar. Bitte den Referenzdatenstand prüfen.</p>
        )}
        {state === 'ready' && currencies.length > 0 && (
          <p>Zur Auswahl stehen die aktiven Währungen aus den Stammdaten.</p>
        )}
        {state !== 'loading' && (
          <button type="button" onClick={reload} className="mt-1 underline">
            Währungen neu laden
          </button>
        )}
      </div>
      {invalid && (
        <p className="mt-1 text-xs text-amber-300">
          Gewählte Strike-Währung nicht verfügbar. Bitte Stammdaten laden oder Auswahl prüfen.
        </p>
      )}
      {!value && (
        <p className="mt-1 text-xs text-amber-300">
          Strike-Währung ungeklärt. Ohne bestätigte Währung ist ein währungsbasierter
          Strike-Vergleich nicht möglich.
        </p>
      )}
    </div>
  );
}
