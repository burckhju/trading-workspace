import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from 'react';
import type {
  IssuerResponse,
  TradingVenueResponse,
  UnderlyingSummaryResponse,
} from '../../market/types/api';
import { MarketTransportError } from '../../market/services/http';
import type { ProductFormGuard } from '../hooks/useProductNavigationGuard';
import type { SelectionRepairContext } from '../services/selectionRepairContext';
import { warrantApiClient } from '../services/client';
import type { OptionDirection, WarrantResponse } from '../types/api';
import { StrikeCurrencyInput } from './StrikeCurrencyInput';
import { WarrantListingFields } from './WarrantListingFields';

const EMPTY_PRODUCT = {
  issuer_id: '',
  underlying_id: '',
  display_name: '',
  isin: '',
  wkn: '',
  option_direction: 'CALL' as OptionDirection,
  strike: '',
  strike_currency_code: '',
  maturity_date: '',
  ratio: '',
};
const EMPTY_LISTING = { trading_venue_id: '', symbol: '', quotation_currency_code: '' };

export function WarrantCreateForm({
  issuers,
  underlyings,
  venues,
  selectionContext,
  onCreated,
  onCancel,
  onGuardChange,
}: {
  issuers: IssuerResponse[];
  underlyings: UnderlyingSummaryResponse[];
  venues: TradingVenueResponse[];
  selectionContext?: SelectionRepairContext;
  onCreated: (value: WarrantResponse) => void;
  onCancel: () => void;
  onGuardChange: (guard: ProductFormGuard) => void;
}) {
  const [initial] = useState(() => ({
    ...EMPTY_PRODUCT,
    underlying_id: selectionContext?.underlying.id ?? '',
  }));
  const [productForm, setProductForm] = useState(initial);
  const [creationListing, setCreationListing] = useState({ ...EMPTY_LISTING });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const submitting = useRef(false);
  const mounted = useRef(true);
  const dirty =
    JSON.stringify(productForm) !== JSON.stringify(initial) ||
    JSON.stringify(creationListing) !== JSON.stringify(EMPTY_LISTING);
  useEffect(() => {
    onGuardChange({ dirty, busy });
  }, [dirty, busy, onGuardChange]);
  useLayoutEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    if (
      !venues.some((venue) => venue.id === creationListing.trading_venue_id) ||
      !/^[A-Z]{3}$/.test(creationListing.quotation_currency_code)
    ) {
      setError('Bitte Handelsplatz und Handelswährung dieses Optionsscheins angeben.');
      return;
    }
    submitting.current = true;
    setBusy(true);
    onGuardChange({ dirty, busy: true });
    setError('');
    try {
      const created = await warrantApiClient.create({
        ...productForm,
        isin: productForm.isin || null,
        wkn: productForm.wkn || null,
        strike_currency_code: productForm.strike_currency_code || null,
        initial_listing: { ...creationListing, symbol: creationListing.symbol.trim() || null },
      });
      // The confirmed identity moves the owner directly into detail mode. No second POST after a read failure.
      if (mounted.current) onCreated(created);
    } catch (cause) {
      if (mounted.current) {
        setError(
          cause instanceof MarketTransportError
            ? 'Speichererfolg unklar. Bitte vor einem weiteren Versuch den Katalog prüfen. Die Eingaben bleiben erhalten.'
            : cause instanceof Error
              ? cause.message
              : 'Optionsschein und Notierung konnten nicht gespeichert werden.',
        );
        submitting.current = false;
        setBusy(false);
        onGuardChange({ dirty, busy: false });
      }
    }
  }

  return (
    <form
      onSubmit={(event) => void create(event)}
      aria-label="Optionsschein anlegen"
      className="min-w-0 rounded-xl border border-slate-800 p-5"
    >
      <fieldset disabled={busy} className="min-w-0">
        <h2 className="text-lg font-medium">Optionsschein anlegen</h2>
        <p className="mt-1 text-sm text-slate-400">
          Emittent und Basiswert werden aus bestehenden Stammdaten referenziert; technische IDs
          müssen nicht eingegeben werden. Produkt und erste Notierung werden gemeinsam gespeichert.
        </p>
        <div className="mt-4 grid gap-3">
          <label className="text-sm">
            Anzeigename *
            <input
              required
              autoFocus
              value={productForm.display_name}
              onChange={(e) => setProductForm({ ...productForm, display_name: e.target.value })}
              className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2"
            />
          </label>
          <label className="text-sm">
            Emittent *
            <select
              required
              value={productForm.issuer_id}
              onChange={(e) => setProductForm({ ...productForm, issuer_id: e.target.value })}
              className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2"
            >
              <option value="">Bitte wählen</option>
              {issuers.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.display_name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Basiswert *
            <select
              required
              disabled={Boolean(selectionContext)}
              value={productForm.underlying_id}
              onChange={(e) => setProductForm({ ...productForm, underlying_id: e.target.value })}
              className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2"
            >
              <option value="">Bitte wählen</option>
              {underlyings.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm">
              ISIN
              <input
                maxLength={12}
                value={productForm.isin}
                onChange={(e) =>
                  setProductForm({ ...productForm, isin: e.target.value.toUpperCase() })
                }
                className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2 font-mono"
              />
            </label>
            <label className="text-sm">
              WKN
              <input
                maxLength={16}
                value={productForm.wkn}
                onChange={(e) =>
                  setProductForm({ ...productForm, wkn: e.target.value.toUpperCase() })
                }
                className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2 font-mono"
              />
            </label>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm">
              Richtung *
              <select
                value={productForm.option_direction}
                onChange={(e) =>
                  setProductForm({
                    ...productForm,
                    option_direction: e.target.value as OptionDirection,
                  })
                }
                className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2"
              >
                <option>CALL</option>
                <option>PUT</option>
              </select>
            </label>
            <label className="text-sm">
              Strike *
              <input
                required
                inputMode="decimal"
                value={productForm.strike}
                onChange={(e) => setProductForm({ ...productForm, strike: e.target.value })}
                className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2"
              />
            </label>
          </div>
          <StrikeCurrencyInput
            label="Strike-Währung"
            value={productForm.strike_currency_code}
            onChange={(value) => setProductForm({ ...productForm, strike_currency_code: value })}
          />
          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm">
              Fälligkeit *
              <input
                required
                type="date"
                value={productForm.maturity_date}
                onChange={(e) => setProductForm({ ...productForm, maturity_date: e.target.value })}
                className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2"
              />
            </label>
            <label className="text-sm">
              Bezugsverhältnis *
              <input
                required
                inputMode="decimal"
                value={productForm.ratio}
                onChange={(e) => setProductForm({ ...productForm, ratio: e.target.value })}
                className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2"
              />
              <span className="mt-1 block text-xs text-slate-500">
                z. B. 0,1 = 0,1 Basiswert-Einheiten je Optionsschein
              </span>
            </label>
          </div>
        </div>
        <section className="mt-5 rounded-lg border border-slate-700 p-3">
          <h3 className="mb-3 font-medium">Notierung dieses Optionsscheins</h3>
          <WarrantListingFields
            value={creationListing}
            onChange={setCreationListing}
            venues={venues}
            creation
          />
          <p className="mt-3 text-xs text-slate-400">
            Diese Angaben nur einmal eintragen. Kein aktueller Kurs erforderlich. Nicht aus der
            Notierung der Aktie oder der Strike-Währung ableiten.
          </p>
        </section>

        {error && (
          <p role="alert" className="mt-4 rounded border border-rose-800 p-3 text-sm">
            {error}
          </p>
        )}
        <div className="mt-5 flex flex-wrap gap-3">
          <button
            disabled={busy}
            className="rounded-lg bg-sky-700 px-4 py-2 text-sm disabled:opacity-50"
          >
            {busy ? 'Wird gespeichert …' : 'Optionsschein anlegen'}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="rounded border border-slate-700 px-4 py-2 text-sm"
          >
            Anlage abbrechen
          </button>
        </div>
      </fieldset>
    </form>
  );
}
