import { FormEvent, useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ErrorNotice, LoadingNotice } from '../components/ApiFeedback';
import { marketApiClient } from '../services/client';
import type {
  CurrencyResponse,
  TradingVenueResponse,
  UnderlyingDetailResponse,
} from '../types/api';

export function UnderlyingFormPage() {
  const { underlyingId } = useParams();
  const editing = Boolean(underlyingId);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [existing, setExisting] = useState<UnderlyingDetailResponse | null>(null);
  const [venues, setVenues] = useState<TradingVenueResponse[]>([]);
  const [currencies, setCurrencies] = useState<CurrencyResponse[]>([]);
  const [name, setName] = useState('');
  const [isin, setIsin] = useState('');
  const [wkn, setWkn] = useState('');
  const [venueId, setVenueId] = useState('');
  const [ticker, setTicker] = useState('');
  const [currency, setCurrency] = useState('');
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const providerSource = !editing ? searchParams.get('source') : null;
  const providerExchange = !editing ? searchParams.get('exchange')?.trim().toUpperCase() : null;
  const providerTicker = !editing ? searchParams.get('ticker')?.trim().toUpperCase() : null;

  useEffect(() => {
    void Promise.all([
      marketApiClient.listTradingVenues(),
      marketApiClient.listCurrencies(),
      editing && underlyingId ? marketApiClient.getUnderlying(underlyingId) : Promise.resolve(null),
    ])
      .then(([v, c, detail]) => {
        setVenues(v.items);
        setCurrencies(c.items);
        setVenueId(v.items[0]?.id ?? '');
        setCurrency(c.items[0]?.code ?? '');
        if (detail) {
          setExisting(detail);
          setName(detail.name);
          setIsin(detail.isin ?? '');
          setWkn(detail.wkn ?? '');
          const primary = detail.listings.find((l) => l.is_primary);
          if (primary) {
            setVenueId(primary.trading_venue_id);
            setTicker(primary.ticker);
            setCurrency(primary.currency_code);
          }
          return;
        }

        const suggestedName = searchParams.get('name')?.trim();
        const suggestedIsin = searchParams.get('isin')?.trim().toUpperCase();
        const suggestedTicker = searchParams.get('ticker')?.trim().toUpperCase();
        const suggestedCurrency = searchParams.get('currency')?.trim().toUpperCase();
        const suggestedExchange = searchParams.get('exchange')?.trim().toUpperCase();
        if (suggestedName) setName(suggestedName);
        if (suggestedIsin) setIsin(suggestedIsin);
        if (suggestedTicker) setTicker(suggestedTicker);
        if (suggestedCurrency && c.items.some((item) => item.code === suggestedCurrency)) {
          setCurrency(suggestedCurrency);
        }
        if (suggestedExchange) {
          const exactVenue = v.items.find((item) => item.mic.toUpperCase() === suggestedExchange);
          if (exactVenue) setVenueId(exactVenue.id);
        }
      })
      .catch(setError)
      .finally(() => setLoading(false));
  }, [editing, underlyingId, searchParams]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (editing && existing) {
        const updated = await marketApiClient.updateUnderlying(existing.id, {
          version: existing.version,
          name,
          isin: isin || null,
          wkn: wkn || null,
        });
        void navigate(`/underlyings/${updated.id}`);
      } else {
        const created = await marketApiClient.createUnderlying({
          name,
          isin: isin || null,
          wkn: wkn || null,
          primary_listing: {
            trading_venue_id: venueId,
            ticker,
            currency_code: currency,
            is_primary: true,
          },
        });
        void navigate(`/underlyings/${created.id}`);
      }
    } catch (reason) {
      setError(reason);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingNotice label="Formular wird vorbereitet …" />;
  return (
    <section className="w-full max-w-3xl space-y-6">
      <div>
        <Link
          to={editing && underlyingId ? `/underlyings/${underlyingId}` : '/underlyings'}
          className="text-sm text-sky-300"
        >
          ← Zurück
        </Link>
        <h1 className="mt-3 text-3xl font-semibold">
          {editing ? 'Basiswert bearbeiten' : 'Basiswert anlegen'}
        </h1>
        <p className="mt-2 text-slate-400">
          {editing
            ? 'Stammdaten ändern. Eine bestehende Verifikation kann zurückgesetzt werden.'
            : 'Grunddaten und primäre Notierung werden gemeinsam gespeichert.'}
        </p>
      </div>
      {providerSource === 'EODHD' && (
        <div className="rounded-xl border border-amber-900 bg-amber-950/20 p-4 text-sm">
          <p className="font-medium text-amber-200">Vorschlag aus EODHD übernommen</p>
          <p className="mt-1 text-slate-400">
            Name, ISIN, Ticker und Währung wurden soweit verfügbar vorausgefüllt. Bitte Handelsplatz
            und Stammdaten vor dem Speichern prüfen. Der Provider-Treffer selbst ist noch keine
            Workspace-Wahrheit.
          </p>
          {(providerTicker || providerExchange) && (
            <p className="mt-2 font-mono text-xs text-slate-500">
              Provider: {providerTicker ?? '—'} · {providerExchange ?? '—'}
            </p>
          )}
        </div>
      )}
      {error !== null && <ErrorNotice error={error} />}
      <form
        onSubmit={(event) => {
          void submit(event);
        }}
        className="space-y-6"
      >
        <fieldset className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <legend className="px-2 font-semibold">1. Grunddaten</legend>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="md:col-span-2">
              <span className="mb-1 block text-sm">Name *</span>
              <input
                required
                maxLength={200}
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
              />
            </label>
            <label>
              <span className="mb-1 block text-sm">Basiswertart</span>
              <select
                disabled
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
              >
                <option>Aktie</option>
              </select>
            </label>
            <span />
            <label>
              <span className="mb-1 block text-sm">ISIN</span>
              <input
                value={isin}
                onChange={(e) => setIsin(e.target.value.toUpperCase())}
                maxLength={12}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono"
              />
            </label>
            <label>
              <span className="mb-1 block text-sm">WKN</span>
              <input
                value={wkn}
                onChange={(e) => setWkn(e.target.value.toUpperCase())}
                maxLength={6}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono"
              />
            </label>
          </div>
        </fieldset>
        {!editing && (
          <fieldset className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
            <legend className="px-2 font-semibold">2. Primäre Notierung</legend>
            <div className="grid gap-4 md:grid-cols-3">
              {venues.length === 1 ? (
                <div>
                  <span className="mb-1 block text-sm">Markt</span>
                  <div
                    aria-label="Automatisch gewählter Markt"
                    className="rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-2 text-slate-300"
                  >
                    {venues[0].name} · {venues[0].mic}
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    Automatisch übernommen, weil genau ein aktiver Handelsplatz verfügbar ist.
                  </p>
                </div>
              ) : (
                <label>
                  <span className="mb-1 block text-sm">Markt *</span>
                  <select
                    aria-label="Markt *"
                    required
                    value={venueId}
                    onChange={(e) => setVenueId(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
                  >
                    {venues.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name} · {v.mic}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-slate-500">
                    Auswahl nur erforderlich, weil mehrere aktive Handelsplätze verfügbar sind.
                  </p>
                </label>
              )}
              <label>
                <span className="mb-1 block text-sm">Ticker *</span>
                <input
                  required
                  maxLength={32}
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono"
                />
              </label>
              <label>
                <span className="mb-1 block text-sm">Währung *</span>
                <select
                  required
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
                >
                  {currencies.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.code} · {c.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </fieldset>
        )}
        <div className="flex justify-end gap-3">
          <Link
            to={editing && underlyingId ? `/underlyings/${underlyingId}` : '/underlyings'}
            className="rounded-lg border border-slate-700 px-4 py-2"
          >
            Abbrechen
          </Link>
          <button
            disabled={saving}
            className="rounded-lg bg-sky-500 px-5 py-2 font-semibold text-slate-950 disabled:opacity-50"
          >
            {saving ? 'Speichern …' : 'Speichern'}
          </button>
        </div>
      </form>
    </section>
  );
}
