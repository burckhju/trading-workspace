import { chartRangeStart } from '../services/chartRanges';
import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { UnderlyingSearchCombobox } from '../components/UnderlyingSearchCombobox';
import { TimeSeriesChart } from '../components/TimeSeriesChart';
import { chartDate, chartMessage } from '../components/chartLabels';
import { chartClient } from '../services/chartClient';
import type { ChartCatalog, ChartComparison, UnderlyingChartContext } from '../types/charts';

const today = () => new Date().toISOString().slice(0, 10);
const control = 'rounded border border-slate-600 bg-slate-950 p-2 text-sm';

export function MarketChartsPage() {
  const [params, setParams] = useSearchParams();
  const rawEnd = params.get('end') ?? today();
  const end =
    /^\d{4}-\d{2}-\d{2}$/.test(rawEnd) && !Number.isNaN(Date.parse(rawEnd)) ? rawEnd : today();
  const rawPeriod = params.get('period') ?? '3';
  const period = ['1', '3', '6', '12', '36', 'all'].includes(rawPeriod) ? rawPeriod : '3';
  const field = params.get('field') === 'ADJUSTED_CLOSE' ? 'ADJUSTED_CLOSE' : 'CLOSE';
  const underlyingId = params.get('underlying') ?? '';
  const keys = params.getAll('target').join('|');
  const [catalog, setCatalog] = useState<ChartCatalog | null>(null);
  const [context, setContext] = useState<UnderlyingChartContext | null>(null);
  const [result, setResult] = useState<ChartComparison | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [contextError, setContextError] = useState<string | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectionError, setSelectionError] = useState<string | null>(null);

  function update(name: string, value: string) {
    const next = new URLSearchParams(params);
    next.set(name, value);
    setParams(next);
  }

  function selectTargets(targets: string[]) {
    if (targets.length > 4) {
      setSelectionError('Maximal vier Serien gleichzeitig.');
      return;
    }
    const next = new URLSearchParams(params);
    next.delete('target');
    [...new Set(targets)].forEach((key) => next.append('target', key));
    setSelectionError(null);
    setParams(next);
  }

  useEffect(() => {
    const abort = new AbortController();
    setCatalog(null);
    setCatalogError(null);
    chartClient
      .catalog(end, abort.signal)
      .then((value) => {
        if (!abort.signal.aborted) setCatalog(value);
      })
      .catch((reason: unknown) => {
        if (!abort.signal.aborted)
          setCatalogError(reason instanceof Error ? reason.message : 'Übersicht nicht verfügbar.');
      });
    return () => abort.abort();
  }, [end]);

  useEffect(() => {
    setContext(null);
    setContextError(null);
    if (!underlyingId) return;
    const abort = new AbortController();
    chartClient
      .underlying(underlyingId, end, abort.signal)
      .then((value) => {
        if (!abort.signal.aborted) setContext(value);
      })
      .catch((reason: unknown) => {
        if (!abort.signal.aborted)
          setContextError(
            reason instanceof Error ? reason.message : 'Aktienkontext nicht verfügbar.',
          );
      });
    return () => abort.abort();
  }, [underlyingId, end]);

  const initial = underlyingId
    ? context?.subject?.key
    : catalog?.references.find((item) => item.identity.reference_code === 'SP500')?.identity.key;
  const effectiveKeys = keys || initial || '';
  useEffect(() => {
    setResult(null);
    setError(null);
    if (!effectiveKeys) {
      setLoading(false);
      return;
    }
    const abort = new AbortController();
    setLoading(true);
    chartClient
      .series(effectiveKeys.split('|'), chartRangeStart(end, period), end, field, abort.signal)
      .then((value) => {
        if (!abort.signal.aborted) setResult(value);
      })
      .catch((reason: unknown) => {
        if (!abort.signal.aborted)
          setError(reason instanceof Error ? reason.message : 'Diagrammdaten nicht verfügbar.');
      })
      .finally(() => {
        if (!abort.signal.aborted) setLoading(false);
      });
    return () => abort.abort();
  }, [effectiveKeys, period, end, field]);

  return (
    <div className="mx-auto min-w-0 w-full max-w-7xl space-y-6">
      <header>
        <Link to="/market-analyses" className="text-sm text-sky-300">
          ← Marktanalysen
        </Link>
        <h1 className="mt-2 text-3xl font-semibold">Markt, Sektoren und Aktien</h1>
        <p className="mt-2 text-slate-300">
          Gespeicherte Tageskurse vergleichen. Identität, Datenbasis und Lücken bleiben sichtbar.
        </p>
      </header>
      <div className="grid gap-4 rounded-xl border border-slate-700 p-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="grid gap-2 text-sm">
          Zeitraum
          <select
            className={control}
            value={period}
            onChange={(event) => update('period', event.target.value)}
          >
            {[
              ['1', '1 Monat'],
              ['3', '3 Monate'],
              ['6', '6 Monate'],
              ['12', '1 Jahr'],
              ['36', '3 Jahre'],
              ['all', 'Gesamthistorie'],
            ].map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-2 text-sm">
          Enddatum
          <input
            className={control}
            type="date"
            value={end}
            max={today()}
            min="1900-01-01"
            onChange={(event) => {
              if (event.target.value) update('end', event.target.value);
            }}
          />
        </label>
        <label className="grid gap-2 text-sm">
          Preisgrundlage
          <select
            className={control}
            value={field}
            onChange={(event) => update('field', event.target.value)}
          >
            <option value="CLOSE">CLOSE – unbereinigt</option>
            <option value="ADJUSTED_CLOSE">ADJUSTED_CLOSE – Splits/Dividenden</option>
          </select>
        </label>
        <label className="grid gap-2 text-sm">
          Marktreferenz
          <select
            className={control}
            value={
              [...(catalog?.references ?? []), ...(catalog?.proxies ?? [])].some(
                (item) => item.identity.key === effectiveKeys.split('|')[0],
              )
                ? effectiveKeys.split('|')[0]
                : ''
            }
            onChange={(event) => selectTargets([event.target.value])}
          >
            <option value="">Markt auswählen</option>
            {catalog?.references.map(({ identity }) => (
              <option key={identity.key} value={identity.key}>
                {identity.name} · direkte Referenz
              </option>
            ))}
            {catalog?.proxies.map(({ identity }) => (
              <option key={`${identity.key}:${identity.reference_id}`} value={identity.key}>
                {identity.name} · ETF-Proxy für {identity.reference_code}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="rounded-xl border border-slate-700 p-4">
        <h2 className="mb-3 font-semibold">Aktie oder ETF auswählen</h2>
        <UnderlyingSearchCombobox
          value={underlyingId}
          onChange={(id) => {
            const next = new URLSearchParams(params);
            next.set('underlying', id);
            next.delete('target');
            setParams(next);
          }}
        />
        {context && (
          <div className="mt-3 space-y-2 text-sm">
            <p>
              Fachliche Zuordnung zum {chartDate(context.assignment_date)}: Markt{' '}
              {context.market?.name ?? 'fehlt'} · Sektor {context.sector?.name ?? 'fehlt'}.
            </p>
            {context.issues.map((issue) => (
              <p key={issue} className="text-amber-200">
                {chartMessage(issue)}
              </p>
            ))}
            <button
              className="rounded border border-sky-700 p-2 disabled:opacity-40"
              disabled={!context.subject || !context.market || !context.sector}
              onClick={() =>
                selectTargets(
                  [context.subject, context.sector, context.market].flatMap((item) =>
                    item ? [item.key] : [],
                  ),
                )
              }
            >
              Mit zugeordnetem Sektor und Markt vergleichen
            </button>
            <Link
              className="ml-3 text-sky-300 underline"
              to={`/chart-setup?underlying_id=${context.underlying_id}`}
            >
              Zuordnungen einrichten
            </Link>
          </div>
        )}
      </div>
      {catalogError && <p role="alert">{catalogError}</p>}
      {contextError && <p role="alert">{contextError}</p>}
      {selectionError && <p role="alert">{selectionError}</p>}
      {error && (
        <p role="alert" className="rounded border border-rose-700 p-4">
          {error}
        </p>
      )}
      {loading && <p role="status">Gespeicherte Kurse werden geladen …</p>}
      {result && (
        <TimeSeriesChart key={`${effectiveKeys}:${period}:${end}:${field}`} result={result} />
      )}
      {!effectiveKeys && !loading && (
        <p className="rounded border border-amber-700 p-4">
          Keine passende Marktserie eingerichtet.{' '}
          <Link to="/chart-setup" className="text-sky-300 underline">
            Markt und Datenbasis einrichten
          </Link>
        </p>
      )}
      <section className="rounded-xl border border-slate-700 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold">Sektor-Abdeckungsmatrix</h2>
          <Link to="/chart-setup" className="text-sm text-sky-300 underline">
            Sektoren und Referenzen einrichten
          </Link>
        </div>
        <p className="my-3 text-sm text-slate-400">
          Alle administrierten Sektoren zum {chartDate(end)}. Kursabdeckung bezeichnet gespeicherte
          Daten; ETF-Serien sind Stellvertreter für die jeweilige Benchmark.
        </p>
        {catalog?.taxonomy_status === 'NO_SECTOR_TAXONOMY' && (
          <p className="text-amber-200">
            {chartMessage(catalog.taxonomy_status)} Die Einrichtung zeigt eine vollständige,
            quellenbelegte Sektorliste zur expliziten Übernahme.
          </p>
        )}
        <div
          className="overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Sektor-Abdeckungsmatrix"
        >
          <table className="w-full text-left text-sm">
            <thead>
              <tr>
                {[
                  'Sektor / System',
                  'Referenz / ETF',
                  'Kennung / Listing',
                  'Quelle',
                  'Historie',
                  'Status / Aktion',
                ].map((title) => (
                  <th scope="col" key={title} className="p-2">
                    {title}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {catalog?.sectors.map(
                ({ context: sector, reference_history: direct, proxy_history: proxyHistory }) => {
                  const identity = sector.proxy ?? sector.reference;
                  const history = sector.proxy ? proxyHistory : direct;
                  return (
                    <tr key={sector.id} className="border-t border-slate-700 align-top">
                      <th scope="row" className="p-2">
                        {sector.name}
                        <span className="block text-xs font-normal text-slate-400">
                          {sector.classification_system} {sector.classification_version} ·{' '}
                          {sector.code}
                        </span>
                      </th>
                      <td className="p-2">
                        {sector.reference?.name ?? 'Nicht zugeordnet'}
                        {sector.proxy && (
                          <span className="block">ETF-Proxy: {sector.proxy.name}</span>
                        )}
                      </td>
                      <td className="p-2">
                        {identity?.isin ?? identity?.reference_code ?? '—'}
                        <span className="block">
                          {identity?.mic ?? 'Keine Notierung'} / {identity?.currency ?? 'unbekannt'}
                        </span>
                      </td>
                      <td className="p-2">
                        {identity?.provider_identity ?? 'Mapping fehlt'}
                        <span className="block text-xs">{identity?.mapping_status}</span>
                      </td>
                      <td className="p-2">
                        {history.count} EOD
                        <span className="block whitespace-nowrap">
                          {chartDate(history.first_date)} – {chartDate(history.last_date)}
                        </span>
                      </td>
                      <td className="space-y-2 p-2">
                        <p>
                          {chartMessage(sector.status)}
                          {history.count === 0 ? ' · Historie fehlt' : ''}
                        </p>
                        {identity && sector.status === 'CONFIGURED' && (
                          <div className="flex flex-wrap gap-2">
                            <button
                              className="text-sky-300 underline"
                              onClick={() => selectTargets([identity.key])}
                            >
                              Diagramm
                            </button>
                            <button
                              className="text-sky-300 underline"
                              onClick={() =>
                                selectTargets([
                                  ...new Set([
                                    ...effectiveKeys.split('|').filter(Boolean),
                                    identity.key,
                                  ]),
                                ])
                              }
                            >
                              Vergleichen
                            </button>
                          </div>
                        )}
                        <Link className="block text-sky-300 underline" to={sector.setup_url}>
                          Einrichten
                        </Link>
                      </td>
                    </tr>
                  );
                },
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
