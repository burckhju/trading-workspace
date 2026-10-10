import { useId } from 'react';

import type { TradingVenueResponse } from '../../market/types/api';

export interface ListingFields {
  trading_venue_id: string;
  quotation_currency_code: string;
  symbol: string;
}

export function WarrantListingFields({
  value,
  onChange,
  venues,
  creation = false,
}: {
  value: ListingFields;
  onChange: (value: ListingFields) => void;
  venues: TradingVenueResponse[];
  creation?: boolean;
}) {
  const helpId = useId();
  const venueLabel = creation ? 'Handelsplatz des Optionsscheins' : 'Handelsplatz';
  const currencyLabel = creation ? 'Handelswährung des Optionsscheins' : 'Handelswährung';
  const symbolLabel = creation ? 'Börsensymbol des Optionsscheins' : 'Symbol';
  const inputClass = 'mt-1 w-full min-w-0 rounded border border-slate-700 bg-slate-950 p-2 text-sm';
  return (
    <div className="min-w-0 space-y-3">
      <label className="block text-sm">
        <span>{venueLabel}</span>
        <select
          aria-label={venueLabel}
          required
          value={value.trading_venue_id}
          onChange={(event) => onChange({ ...value, trading_venue_id: event.target.value })}
          className={inputClass}
        >
          <option value="">Handelsplatz wählen</option>
          {venues.map((venue) => (
            <option key={venue.id} value={venue.id}>
              {venue.name} ({venue.mic})
            </option>
          ))}
        </select>
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block min-w-0 text-sm">
          <span>{currencyLabel}</span>
          <input
            required
            maxLength={3}
            pattern="[A-Za-z]{3}"
            placeholder="z. B. EUR"
            value={value.quotation_currency_code}
            onChange={(event) =>
              onChange({ ...value, quotation_currency_code: event.target.value.toUpperCase() })
            }
            className={`${inputClass} font-mono`}
          />
        </label>
        <label className="block min-w-0 text-sm">
          <span>{symbolLabel} (optional)</span>
          <input
            aria-label={symbolLabel}
            aria-describedby={helpId}
            maxLength={64}
            value={value.symbol}
            onChange={(event) => onChange({ ...value, symbol: event.target.value })}
            className={inputClass}
          />
        </label>
      </div>
      <p id={helpId} className="text-xs text-slate-400">
        Veröffentlicht der Handelsplatz kein Börsensymbol, bleibt das Feld leer. Kein
        Basiswertsymbol, keine ISIN oder WKN als Ersatz eintragen.
      </p>
    </div>
  );
}
