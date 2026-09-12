import { useId } from 'react';

interface StrikeCurrencyInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
}

export function StrikeCurrencyInput({ label, value, onChange }: StrikeCurrencyInputProps) {
  const id = useId();

  return (
    <div className="text-sm">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        aria-describedby={`${id}-help`}
        value={value}
        onChange={(event) => onChange(event.target.value.toUpperCase())}
        maxLength={3}
        pattern="[A-Za-z]{3}"
        placeholder="z. B. USD"
        className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2 font-mono"
      />
      <p id={`${id}-help`} className="mt-1 text-xs text-slate-400">
        Währung des Basispreises laut Produktbedingungen, nicht Handelswährung. Keine automatische
        Währungsumrechnung. Für einen Strike in Punkten keine Währung erfinden.
      </p>
      {!value && (
        <p className="mt-1 text-xs text-amber-300">
          Strike-Währung ungeklärt. Ohne bestätigte Währung ist ein währungsbasierter
          Strike-Vergleich nicht möglich.
        </p>
      )}
    </div>
  );
}
