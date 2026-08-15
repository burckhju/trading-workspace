import { FormEvent, useEffect, useMemo, useState } from 'react';

import { marketApiClient } from '../../market/services/client';
import type {
  IssuerResponse,
  TradingVenueResponse,
  UnderlyingSummaryResponse,
} from '../../market/types/api';
import { warrantApiClient } from '../services/client';
import type {
  OptionDirection,
  WarrantListingResponse,
  WarrantResponse,
  WarrantTermsResponse,
} from '../types/api';

const EMPTY_PRODUCT = {
  issuer_id: '',
  underlying_id: '',
  display_name: '',
  isin: '',
  wkn: '',
  option_direction: 'CALL' as OptionDirection,
  strike: '',
  maturity_date: '',
  ratio: '',
};
const EMPTY_TERMS = {
  option_direction: 'CALL' as OptionDirection,
  strike: '',
  maturity_date: '',
  ratio: '',
};
const EMPTY_LISTING = { trading_venue_id: '', symbol: '', quotation_currency_code: 'EUR' };

export function WarrantAdminPage() {
  const [warrants, setWarrants] = useState<WarrantResponse[]>([]);
  const [issuers, setIssuers] = useState<IssuerResponse[]>([]);
  const [underlyings, setUnderlyings] = useState<UnderlyingSummaryResponse[]>([]);
  const [venues, setVenues] = useState<TradingVenueResponse[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [terms, setTerms] = useState<WarrantTermsResponse[]>([]);
  const [listings, setListings] = useState<WarrantListingResponse[]>([]);
  const [productForm, setProductForm] = useState(EMPTY_PRODUCT);
  const [termsForm, setTermsForm] = useState(EMPTY_TERMS);
  const [listingForm, setListingForm] = useState(EMPTY_LISTING);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = useMemo(
    () => warrants.find((item) => item.id === selectedId) ?? null,
    [selectedId, warrants],
  );
  const issuerName = (id: string) => issuers.find((item) => item.id === id)?.display_name ?? id;
  const underlyingName = (id: string) => underlyings.find((item) => item.id === id)?.name ?? id;
  const venueName = (id: string) => venues.find((item) => item.id === id)?.name ?? id;

  async function loadReferenceData() {
    const [issuerResponse, underlyingResponse, venueResponse] = await Promise.all([
      marketApiClient.listIssuers(),
      marketApiClient.searchUnderlyings({ lifecycleStatus: 'ACTIVE', limit: 100 }),
      marketApiClient.listTradingVenues(),
    ]);
    setIssuers(issuerResponse.items);
    setUnderlyings(underlyingResponse.items);
    setVenues(venueResponse.items);
  }

  async function loadWarrants(preferredId?: string) {
    const response = await warrantApiClient.list();
    setWarrants(response);
    setSelectedId((current) => preferredId ?? current ?? response[0]?.id ?? null);
  }

  async function loadDetail(id: string) {
    const [termsResponse, listingsResponse] = await Promise.all([
      warrantApiClient.terms(id),
      warrantApiClient.listings(id),
    ]);
    setTerms(termsResponse);
    setListings(listingsResponse);
  }

  useEffect(() => {
    void Promise.all([loadReferenceData(), loadWarrants()]).catch((value: unknown) =>
      setError(
        value instanceof Error ? value.message : 'Optionsscheine konnten nicht geladen werden.',
      ),
    );
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setTerms([]);
      setListings([]);
      return;
    }
    void loadDetail(selectedId).catch((value: unknown) =>
      setError(
        value instanceof Error ? value.message : 'Produktdetails konnten nicht geladen werden.',
      ),
    );
  }, [selectedId]);

  async function createProduct(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await warrantApiClient.create({
        ...productForm,
        isin: productForm.isin || null,
        wkn: productForm.wkn || null,
      });
      setProductForm(EMPTY_PRODUCT);
      await loadWarrants(created.id);
    } catch (value: unknown) {
      setError(
        value instanceof Error ? value.message : 'Optionsschein konnte nicht angelegt werden.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function addTerms(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await warrantApiClient.addTerms(selected.id, {
        ...termsForm,
        expected_version: selected.version,
      });
      setTermsForm(EMPTY_TERMS);
      await Promise.all([loadDetail(selected.id), loadWarrants(selected.id)]);
    } catch (value: unknown) {
      setError(
        value instanceof Error ? value.message : 'Produktbedingungen konnten nicht ergänzt werden.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function addListing(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await warrantApiClient.addListing(selected.id, listingForm);
      setListingForm(EMPTY_LISTING);
      await loadDetail(selected.id);
    } catch (value: unknown) {
      setError(value instanceof Error ? value.message : 'Notierung konnte nicht ergänzt werden.');
    } finally {
      setBusy(false);
    }
  }

  async function toggleStatus() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const updated =
        selected.lifecycle_status === 'ACTIVE'
          ? await warrantApiClient.deactivate(selected.id, selected.version)
          : await warrantApiClient.reactivate(selected.id, selected.version);
      await loadWarrants(updated.id);
    } catch (value: unknown) {
      setError(value instanceof Error ? value.message : 'Status konnte nicht geändert werden.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="w-full space-y-8">
      <header>
        <p className="text-xs uppercase tracking-wide text-slate-500">Administration · FT-004</p>
        <h1 className="mt-1 text-2xl font-semibold">Optionsscheine</h1>
        <p className="mt-2 max-w-4xl text-sm text-slate-400">
          Produktidentität, historische Produktbedingungen und handelbare Notierungen werden
          getrennt gepflegt. Preise, Rankings und Produktauswahl gehören ausdrücklich nicht hierher.
        </p>
      </header>
      {error && (
        <p className="rounded-lg border border-rose-800 p-3 text-sm text-rose-200">{error}</p>
      )}

      <section className="grid gap-6 lg:grid-cols-[1fr_1.5fr]">
        <form
          onSubmit={(event) => void createProduct(event)}
          className="rounded-xl border border-slate-800 p-5"
        >
          <h2 className="text-lg font-medium">Optionsschein anlegen</h2>
          <p className="mt-1 text-xs text-slate-500">
            Emittent und Basiswert werden aus bestehenden Stammdaten referenziert; technische IDs
            müssen nicht eingegeben werden.
          </p>
          <div className="mt-4 grid gap-3">
            <label className="text-sm">
              Anzeigename *
              <input
                required
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
            <div className="grid grid-cols-2 gap-3">
              <label className="text-sm">
                Fälligkeit *
                <input
                  required
                  type="date"
                  value={productForm.maturity_date}
                  onChange={(e) =>
                    setProductForm({ ...productForm, maturity_date: e.target.value })
                  }
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
          <button
            disabled={busy}
            className="mt-5 rounded-lg bg-sky-700 px-4 py-2 text-sm disabled:opacity-50"
          >
            Optionsschein anlegen
          </button>
        </form>

        <section className="rounded-xl border border-slate-800">
          <div className="border-b border-slate-800 px-5 py-4">
            <h2 className="font-medium">Vorhandene Produkte</h2>
            <p className="mt-1 text-xs text-slate-500">
              Deaktivieren entfernt keine Historie und ist nicht dasselbe wie fachliche Fälligkeit.
            </p>
          </div>
          <div className="divide-y divide-slate-800">
            {warrants.map((w) => (
              <button
                type="button"
                key={w.id}
                onClick={() => setSelectedId(w.id)}
                className={`block w-full px-5 py-4 text-left ${selectedId === w.id ? 'bg-slate-900' : ''}`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium">{w.display_name}</span>
                  <span className="text-xs text-slate-400">
                    {w.lifecycle_status === 'ACTIVE' ? 'Aktiv' : 'Inaktiv'}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-400">
                  {underlyingName(w.underlying_id)} · {issuerName(w.issuer_id)}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {w.isin ? `ISIN ${w.isin}` : 'keine ISIN'} ·{' '}
                  {w.wkn ? `WKN ${w.wkn}` : 'keine WKN'}
                </p>
              </button>
            ))}
            {warrants.length === 0 && (
              <p className="px-5 py-6 text-sm text-slate-500">Keine Optionsscheine vorhanden.</p>
            )}
          </div>
        </section>
      </section>

      {selected && (
        <section className="space-y-6 rounded-xl border border-slate-800 p-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Ausgewähltes Produkt</p>
              <h2 className="mt-1 text-xl font-medium">{selected.display_name}</h2>
              <p className="mt-1 text-sm text-slate-400">
                {underlyingName(selected.underlying_id)} · {issuerName(selected.issuer_id)}
              </p>
            </div>
            <button
              type="button"
              disabled={busy}
              onClick={() => void toggleStatus()}
              className="rounded border border-slate-700 px-3 py-1.5 text-sm"
            >
              {selected.lifecycle_status === 'ACTIVE' ? 'Deaktivieren' : 'Reaktivieren'}
            </button>
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <div>
              <h3 className="font-medium">Produktbedingungen / Historie</h3>
              <p className="mt-1 text-xs text-slate-500">
                Neue Bedingungen erzeugen eine neue Version; frühere Werte bleiben nachvollziehbar.
              </p>
              <div className="mt-3 space-y-2">
                {terms.map((t) => (
                  <div key={t.id} className="rounded border border-slate-800 p-3 text-sm">
                    <div className="flex justify-between">
                      <strong>Version {t.version_no}</strong>
                      <span>{t.option_direction}</span>
                    </div>
                    <p className="mt-1 text-slate-400">
                      Strike {t.strike} · Ratio {t.ratio} · Fälligkeit {t.maturity_date}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      gültig ab {new Date(t.effective_from).toLocaleString('de-DE')}
                      {t.effective_to
                        ? ` bis ${new Date(t.effective_to).toLocaleString('de-DE')}`
                        : ' · aktuell'}
                    </p>
                  </div>
                ))}
              </div>
              <form
                onSubmit={(e) => void addTerms(e)}
                className="mt-4 grid gap-2 rounded border border-slate-800 p-3"
              >
                <div className="grid grid-cols-2 gap-2">
                  <select
                    aria-label="Neue Richtung"
                    value={termsForm.option_direction}
                    onChange={(e) =>
                      setTermsForm({
                        ...termsForm,
                        option_direction: e.target.value as OptionDirection,
                      })
                    }
                    className="rounded border border-slate-700 bg-slate-950 p-2 text-sm"
                  >
                    <option>CALL</option>
                    <option>PUT</option>
                  </select>
                  <input
                    aria-label="Neuer Strike"
                    required
                    placeholder="Strike"
                    value={termsForm.strike}
                    onChange={(e) => setTermsForm({ ...termsForm, strike: e.target.value })}
                    className="rounded border border-slate-700 bg-slate-950 p-2 text-sm"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    aria-label="Neue Fälligkeit"
                    required
                    type="date"
                    value={termsForm.maturity_date}
                    onChange={(e) => setTermsForm({ ...termsForm, maturity_date: e.target.value })}
                    className="rounded border border-slate-700 bg-slate-950 p-2 text-sm"
                  />
                  <input
                    aria-label="Neues Bezugsverhältnis"
                    required
                    placeholder="Ratio"
                    value={termsForm.ratio}
                    onChange={(e) => setTermsForm({ ...termsForm, ratio: e.target.value })}
                    className="rounded border border-slate-700 bg-slate-950 p-2 text-sm"
                  />
                </div>
                <button
                  disabled={busy}
                  className="justify-self-start rounded bg-slate-800 px-3 py-2 text-sm"
                >
                  Neue Terms-Version
                </button>
              </form>
            </div>
            <div>
              <h3 className="font-medium">Handelbare Notierungen</h3>
              <p className="mt-1 text-xs text-slate-500">
                Handelsplatz und Symbol gehören zur Notierung, nicht zur Produktidentität.
              </p>
              <div className="mt-3 space-y-2">
                {listings.map((l) => (
                  <div key={l.id} className="rounded border border-slate-800 p-3 text-sm">
                    <strong>{l.symbol}</strong>
                    <p className="mt-1 text-slate-400">
                      {venueName(l.trading_venue_id)} · {l.quotation_currency_code}
                    </p>
                  </div>
                ))}
                {listings.length === 0 && (
                  <p className="text-sm text-slate-500">Noch keine Notierung hinterlegt.</p>
                )}
              </div>
              <form
                onSubmit={(e) => void addListing(e)}
                className="mt-4 grid gap-2 rounded border border-slate-800 p-3"
              >
                <select
                  aria-label="Handelsplatz"
                  required
                  value={listingForm.trading_venue_id}
                  onChange={(e) =>
                    setListingForm({ ...listingForm, trading_venue_id: e.target.value })
                  }
                  className="rounded border border-slate-700 bg-slate-950 p-2 text-sm"
                >
                  <option value="">Handelsplatz wählen</option>
                  {venues.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name} ({v.mic})
                    </option>
                  ))}
                </select>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    aria-label="Symbol"
                    required
                    placeholder="Symbol"
                    value={listingForm.symbol}
                    onChange={(e) => setListingForm({ ...listingForm, symbol: e.target.value })}
                    className="rounded border border-slate-700 bg-slate-950 p-2 text-sm"
                  />
                  <input
                    aria-label="Handelswährung"
                    required
                    maxLength={3}
                    value={listingForm.quotation_currency_code}
                    onChange={(e) =>
                      setListingForm({
                        ...listingForm,
                        quotation_currency_code: e.target.value.toUpperCase(),
                      })
                    }
                    className="rounded border border-slate-700 bg-slate-950 p-2 text-sm font-mono"
                  />
                </div>
                <button
                  disabled={busy}
                  className="justify-self-start rounded bg-slate-800 px-3 py-2 text-sm"
                >
                  Notierung hinzufügen
                </button>
              </form>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
