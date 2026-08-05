import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ErrorNotice, LoadingNotice } from '../components/ApiFeedback';
import { StatusBadge } from '../components/StatusBadge';
import { marketApiClient } from '../services/client';
import type { CurrencyResponse, LifecycleStatus, TradingVenueResponse, UnderlyingSearchResponse } from '../types/api';

const PAGE_SIZE = 25;

export function UnderlyingListPage() {
  const [query, setQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [lifecycle, setLifecycle] = useState<LifecycleStatus | ''>('ACTIVE');
  const [venueId, setVenueId] = useState('');
  const [currencyCode, setCurrencyCode] = useState('');
  const [offset, setOffset] = useState(0);
  const [result, setResult] = useState<UnderlyingSearchResponse | null>(null);
  const [venues, setVenues] = useState<TradingVenueResponse[]>([]);
  const [currencies, setCurrencies] = useState<CurrencyResponse[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      marketApiClient.listTradingVenues(controller.signal),
      marketApiClient.listCurrencies(controller.signal),
    ]).then(([venueResponse, currencyResponse]) => {
      setVenues(venueResponse.items);
      setCurrencies(currencyResponse.items);
    }).catch((reason: unknown) => {
      if (!(reason instanceof DOMException && reason.name === 'AbortError')) setError(reason);
    });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    marketApiClient.searchUnderlyings({
      query: submittedQuery || undefined,
      lifecycleStatus: lifecycle || undefined,
      tradingVenueId: venueId || undefined,
      currencyCode: currencyCode || undefined,
      offset,
      limit: PAGE_SIZE,
    }, controller.signal).then(setResult).catch((reason: unknown) => {
      if (!(reason instanceof DOMException && reason.name === 'AbortError')) setError(reason);
    }).finally(() => setLoading(false));
    return () => controller.abort();
  }, [submittedQuery, lifecycle, venueId, currencyCode, offset]);

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setOffset(0);
    setSubmittedQuery(query.trim());
  }

  return <section className="w-full space-y-6" aria-labelledby="underlyings-title">
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div><p className="text-sm font-medium uppercase tracking-[0.2em] text-sky-400">Stammdaten</p><h1 id="underlyings-title" className="mt-2 text-3xl font-semibold">Basiswerte</h1><p className="mt-2 text-slate-400">Aktien und ihre börslichen Notierungen zentral verwalten.</p></div>
      <Link to="/underlyings/new" className="rounded-lg bg-sky-500 px-4 py-2.5 font-semibold text-slate-950 hover:bg-sky-400">Basiswert anlegen</Link>
    </div>
    <form onSubmit={submitSearch} className="grid gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4 md:grid-cols-5">
      <label className="md:col-span-2"><span className="mb-1 block text-sm text-slate-300">Suche</span><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Name, Ticker, ISIN oder WKN" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2" /></label>
      <label><span className="mb-1 block text-sm text-slate-300">Status</span><select value={lifecycle} onChange={(e) => { setLifecycle(e.target.value as LifecycleStatus | ''); setOffset(0); }} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"><option value="ACTIVE">Aktiv</option><option value="INACTIVE">Deaktiviert</option><option value="">Alle</option></select></label>
      <label><span className="mb-1 block text-sm text-slate-300">Markt</span><select value={venueId} onChange={(e) => { setVenueId(e.target.value); setOffset(0); }} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"><option value="">Alle</option>{venues.map((v) => <option key={v.id} value={v.id}>{v.name} · {v.mic}</option>)}</select></label>
      <label><span className="mb-1 block text-sm text-slate-300">Währung</span><select value={currencyCode} onChange={(e) => { setCurrencyCode(e.target.value); setOffset(0); }} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"><option value="">Alle</option>{currencies.map((c) => <option key={c.code} value={c.code}>{c.code} · {c.name}</option>)}</select></label>
      <button className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium hover:bg-slate-800 md:col-start-5">Suchen</button>
    </form>
    {error ? <ErrorNotice error={error} /> : loading ? <LoadingNotice /> : result && result.items.length === 0 ? <div className="rounded-xl border border-dashed border-slate-700 p-10 text-center"><h2 className="font-semibold">Keine Basiswerte gefunden</h2><p className="mt-2 text-sm text-slate-400">Filter anpassen oder einen neuen Basiswert anlegen.</p></div> : result ? <>
      <div className="overflow-x-auto rounded-xl border border-slate-800"><table className="w-full min-w-[900px] text-left text-sm"><thead className="bg-slate-900 text-slate-400"><tr><th className="px-4 py-3">Name</th><th className="px-4 py-3">Primäre Notierung</th><th className="px-4 py-3">ISIN</th><th className="px-4 py-3">WKN</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Letzte Änderung</th></tr></thead><tbody className="divide-y divide-slate-800">{result.items.map((item) => <tr key={item.id} className="hover:bg-slate-900/70"><td className="px-4 py-4"><Link className="font-medium text-sky-300 hover:underline" to={`/underlyings/${item.id}`}>{item.name}</Link></td><td className="px-4 py-4 text-slate-300">{item.primary_listing ? `${item.primary_listing.ticker} · ${item.primary_listing.trading_venue_name} · ${item.primary_listing.currency_code}` : '—'}</td><td className="px-4 py-4 font-mono text-xs">{item.isin ?? '—'}</td><td className="px-4 py-4 font-mono text-xs">{item.wkn ?? '—'}</td><td className="px-4 py-4"><div className="flex gap-2"><StatusBadge status={item.lifecycle_status}/><StatusBadge status={item.quality_status}/></div></td><td className="px-4 py-4 text-slate-400">{new Date(item.updated_at).toLocaleString('de-DE')}</td></tr>)}</tbody></table></div>
      <div className="flex items-center justify-between text-sm text-slate-400"><span>{result.total} Treffer</span><div className="flex gap-2"><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} className="rounded-lg border border-slate-700 px-3 py-2 disabled:opacity-40">Zurück</button><button disabled={offset + PAGE_SIZE >= result.total} onClick={() => setOffset(offset + PAGE_SIZE)} className="rounded-lg border border-slate-700 px-3 py-2 disabled:opacity-40">Weiter</button></div></div>
    </> : null}
  </section>;
}
