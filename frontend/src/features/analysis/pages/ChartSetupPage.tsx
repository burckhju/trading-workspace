import { useEffect, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  topDownAdminClient,
  type VenueReconciliation,
} from '../../administration/services/topDownAdminClient';
import { marketApiClient } from '../../market/services/client';
import type { ListingResponse } from '../../market/types/api';
import { UnderlyingSearchCombobox } from '../components/UnderlyingSearchCombobox';
import { chartClient } from '../services/chartClient';
import { chartSetupClient, type SectorProposal } from '../services/chartSetupClient';
import type { ChartCatalog } from '../types/charts';

const inputClass = 'mt-1 w-full rounded border border-slate-600 bg-slate-950 p-2';
const actions = [
  ['bootstrap', 'Marktreferenzen DAX / S&P 500 / Nasdaq 100 anlegen'],
  ['sector', 'Sektor anlegen'],
  ['reference', 'Sektor-Benchmark anlegen'],
  ['sectorReference', 'Sektor einer Benchmark zuordnen'],
  ['proxy', 'ETF-Listing als Benchmark-Proxy zuordnen'],
  ['stockSector', 'Basiswert einem Sektor zuordnen'],
  ['stockMarket', 'Basiswert einem Markt zuordnen'],
  ['referenceMapping', 'Index: Provider-Mapping speichern (deaktiviert)'],
  ['referenceValidate', 'Index: Mapping prüfen und aktivieren'],
  ['basis', 'Index: Renditegrundlage bestätigen'],
  ['referenceImport', 'Index: Historie importieren'],
  ['listingMapping', 'Aktie / ETF: Provider-Mapping speichern (deaktiviert)'],
  ['listingValidate', 'Aktie / ETF: Mapping prüfen und aktivieren'],
  ['listingImport', 'Aktie / ETF: Historie importieren'],
] as const;
type Action = (typeof actions)[number][0];
const today = () => new Date().toISOString().slice(0, 10);

export function ChartSetupPage() {
  const [params] = useSearchParams();
  const [catalog, setCatalog] = useState<ChartCatalog | null>(null);
  const [proposals, setProposals] = useState<SectorProposal[]>([]);
  const [action, setAction] = useState<Action>(
    params.has('reference_id')
      ? 'referenceImport'
      : params.has('listing_id')
        ? 'listingImport'
        : params.has('sector_id')
          ? 'sectorReference'
          : params.has('underlying_id')
            ? 'stockSector'
            : 'bootstrap',
  );
  const [reference, setReference] = useState(params.get('reference_id') ?? '');
  const [sector, setSector] = useState(params.get('sector_id') ?? '');
  const [underlying, setUnderlying] = useState(params.get('underlying_id') ?? '');
  const [listing, setListing] = useState(params.get('listing_id') ?? '');
  const [listings, setListings] = useState<ListingResponse[]>([]);
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [system, setSystem] = useState('');
  const [version, setVersion] = useState('');
  const [symbol, setSymbol] = useState('');
  const [exchange, setExchange] = useState('');
  const [source, setSource] = useState('');
  const [basis, setBasis] = useState('PRICE_INDEX');
  const [start, setStart] = useState(`${new Date().getUTCFullYear() - 1}-01-01`);
  const [end, setEnd] = useState(today());
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const [venueEvidence, setVenueEvidence] = useState<VenueReconciliation | null>(null);
  const identity = catalog?.references.find(
    (item) => item.identity.reference_id === reference,
  )?.identity;
  const assignment = ['sectorReference', 'proxy', 'stockSector', 'stockMarket'].includes(action);
  const needsReference = [
    'sectorReference',
    'proxy',
    'stockMarket',
    'referenceMapping',
    'referenceValidate',
    'basis',
    'referenceImport',
  ].includes(action);
  const needsSector = ['sectorReference', 'stockSector'].includes(action);
  const needsListing = ['proxy', 'listingMapping', 'listingValidate', 'listingImport'].includes(
    action,
  );
  const needsUnderlying = needsListing || ['stockSector', 'stockMarket'].includes(action);
  const importing = action.endsWith('Import');

  useEffect(() => {
    const abort = new AbortController();
    Promise.all([chartClient.catalog(today(), abort.signal), chartSetupClient.proposals()])
      .then(([values, hints]) => {
        if (!abort.signal.aborted) {
          setCatalog(values);
          setProposals(hints);
        }
      })
      .catch((reason: unknown) => {
        if (!abort.signal.aborted)
          setError(reason instanceof Error ? reason.message : 'Einrichtung nicht verfügbar.');
      });
    return () => abort.abort();
  }, [revision]);
  useEffect(() => {
    if (!underlying) return;
    let current = true;
    marketApiClient
      .getUnderlying(underlying)
      .then((value) => {
        if (!current) return;
        setListings(value.listings);
        setListing(value.listings.find((item) => item.is_primary)?.id ?? '');
      })
      .catch((reason: unknown) => {
        if (current) setError(reason instanceof Error ? reason.message : 'Notierungen fehlen.');
      });
    return () => {
      current = false;
    };
  }, [underlying]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!confirmed || busy) return;
    setBusy(true);
    setError('');
    setMessage('');
    setVenueEvidence(null);
    const evidence = {
      valid_from: start,
      valid_to: null,
      source: 'CHART_SETUP',
      source_reference: source,
      quality_status: 'GOOD',
    };
    let result: unknown;
    try {
      switch (action) {
        case 'bootstrap':
          result = await chartSetupClient.write('bootstrap-v1');
          break;
        case 'sector':
          result = await chartSetupClient.write('sectors', {
            code,
            name,
            classification_system: system,
            classification_version: version,
          });
          break;
        case 'reference':
          result = await chartSetupClient.write('sector-references', {
            code,
            name,
            region: 'US',
            reference_version: version,
          });
          break;
        case 'sectorReference':
          result = await chartSetupClient.write(`sectors/${sector}/reference-assignments`, {
            ...evidence,
            market_reference_id: reference,
          });
          break;
        case 'proxy':
          result = await chartSetupClient.write(
            `market-references/${reference}/listing-assignments`,
            { ...evidence, listing_id: listing },
          );
          break;
        case 'stockSector':
          result = await chartSetupClient.write(`underlyings/${underlying}/sector-assignments`, {
            ...evidence,
            sector_id: sector,
          });
          break;
        case 'stockMarket':
          result = await chartSetupClient.write(`underlyings/${underlying}/benchmark-assignments`, {
            ...evidence,
            market_reference_id: reference,
            role: 'BROAD_MARKET',
          });
          break;
        case 'referenceMapping':
          result = await chartSetupClient.write(
            `market-references/${reference}/provider-mapping/eodhd`,
            { provider_symbol: symbol, provider_exchange_code: exchange },
            'PUT',
          );
          break;
        case 'referenceValidate':
          result = await chartSetupClient.write(
            `market-references/${reference}/provider-mapping/eodhd/validate`,
          );
          break;
        case 'basis':
          if (!identity?.mapping_id || !identity.mapping_version)
            throw new Error('Aktives Mapping zuerst prüfen.');
          result = await chartSetupClient.write(`market-references/${reference}/series-basis`, {
            mapping_id: identity.mapping_id,
            mapping_version: identity.mapping_version,
            return_basis: basis,
            source_url: source,
            confirmed: true,
          });
          break;
        case 'referenceImport':
          result = await chartSetupClient.write(
            `market-references/${reference}/daily-prices/import`,
            { start_date: start, end_date: end },
          );
          break;
        case 'listingMapping':
          result = await topDownAdminClient.createMapping(listing, symbol, exchange);
          break;
        case 'listingValidate':
        case 'listingImport': {
          const mappings = await topDownAdminClient.mappings();
          const mapping = mappings.find((item) => item.listing_id === listing);
          if (!mapping) throw new Error('Für diese Notierung fehlt ein Mapping.');
          if (action === 'listingValidate') {
            result = await topDownAdminClient.validateMapping(mapping.id);
            setVenueEvidence(await topDownAdminClient.venueReconciliation(mapping.id));
          } else {
            result = await topDownAdminClient.importHistory(listing, mapping.id, start, end);
          }
          break;
        }
      }
      chartClient.clear();
      setConfirmed(false);
      setRevision((value) => value + 1);
      if (result && typeof result === 'object' && 'inserted' in result) {
        const counts = result as { inserted: number; updated: number; unchanged: number };
        setMessage(
          `Import abgeschlossen: ${counts.inserted} neu, ${counts.updated} aktualisiert, ${counts.unchanged} unverändert.`,
        );
      } else if (result && typeof result === 'object' && 'status' in result) {
        const status = (result as { status: string }).status;
        setMessage(`Mappingstatus: ${status}. Historie wird separat importiert.`);
      } else
        setMessage(
          'Schritt gespeichert. Weitere Zuordnungen und Datenimporte bleiben separate Schritte.',
        );
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'Schritt fehlgeschlagen.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-w-0 w-full space-y-6">
      <header>
        <Link className="text-sky-300" to="/market-charts">
          ← Diagramme
        </Link>
        <h1 className="mt-3 text-3xl font-semibold">Diagramm-Datenbasis einrichten</h1>
        <p className="mt-2 text-slate-300">
          Vorhandene Sektoren und Referenzen bleiben maßgeblich. Jeder Schritt wird einzeln geprüft
          und bestätigt. Chartauswahl ändert keine Zuordnung.
        </p>
      </header>
      {error && (
        <p role="alert" className="rounded border border-rose-700 p-3">
          {error}
        </p>
      )}
      {message && (
        <p role="status" className="rounded border border-emerald-700 p-3">
          {message}
        </p>
      )}
      {venueEvidence && (
        <p className="rounded border border-amber-700 p-3 text-sm">
          Handelsplatzabgleich: {venueEvidence.status}. {venueEvidence.explanation}{' '}
          {venueEvidence.status !== 'MATCHED' &&
            'Technische Mappingaktivierung allein belegt keine eindeutige Handelsplatzzuordnung. Bitte vor dem Import klären.'}
        </p>
      )}
      <section className="space-y-3 rounded border border-slate-700 p-4">
        <h2 className="text-xl font-semibold">Vollständige Sektor-Vorschläge zur Prüfung</h2>
        <p className="text-sm text-slate-300">
          Elf GICS-Sektoren, Quellenstand 04.10.2026. ETF-Kurse sind Stellvertreter ihrer
          Select-Sector-Benchmark. Die Vorschläge enthalten keine Kursdaten; Providerzugang und
          verfügbare Historie sind nicht nachgewiesen. Bestehende Systematik verwenden; neue
          Sektoren nur gezielt ergänzen.
        </p>
        <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Sektor-Vorschläge">
          <table className="w-full text-left text-sm">
            <thead>
              <tr>
                {['Sektor', 'Benchmark / ETF', 'Identität / Quelle', 'Einrichtung'].map((label) => (
                  <th scope="col" className="p-2" key={label}>
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {proposals.map((hint) => (
                <tr key={hint.code} className="border-t border-slate-700 align-top">
                  <th className="p-2" scope="row">
                    {hint.code} · {hint.sector}
                  </th>
                  <td className="p-2">
                    {hint.benchmark}
                    <span className="block">{hint.ticker} · ETF-Proxy</span>
                  </td>
                  <td className="p-2">
                    {hint.isin}
                    <span className="block">
                      NYSE Arca / {hint.mic} / {hint.currency}
                    </span>
                    <a
                      className="text-sky-300 underline"
                      href={hint.source_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Emittentenbeleg
                    </a>
                  </td>
                  <td className="space-y-2 p-2">
                    <button
                      className="block text-sky-300 underline"
                      onClick={() => {
                        setAction('sector');
                        setCode(hint.code);
                        setName(hint.sector);
                        setSystem(hint.classification_system);
                        setVersion(hint.classification_version);
                        setConfirmed(false);
                      }}
                    >
                      Sektorformular vorbereiten
                    </button>
                    <button
                      className="block text-sky-300 underline"
                      onClick={() => {
                        setAction('reference');
                        setCode(`SELECT_${hint.ticker}`);
                        setName(hint.benchmark);
                        setVersion(hint.reviewed_on);
                        setSource(hint.source_url);
                        setConfirmed(false);
                      }}
                    >
                      Benchmarkformular vorbereiten
                    </button>
                    <Link
                      className="block text-sky-300 underline"
                      to={`/underlyings/new?${new URLSearchParams({ type: 'ETF', name: `State Street ${hint.benchmark.replace(' Index', '')} SPDR ETF`, isin: hint.isin, ticker: hint.ticker, mic: hint.mic, currency: hint.currency })}`}
                    >
                      ETF-Stammdaten prüfen / anlegen
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-sm">
          <a className="text-sky-300 underline" href={proposals[0]?.taxonomy_source}>
            GICS-Systematik
          </a>{' '}
          ·{' '}
          <a className="text-sky-300 underline" href={proposals[0]?.venue_source}>
            MIC-Verzeichnis
          </a>{' '}
          ·{' '}
          <Link className="text-sky-300 underline" to="/trading-venues-admin">
            Handelsplatzverwaltung
          </Link>
        </p>
      </section>
      <form
        className="max-w-3xl space-y-4 rounded border border-slate-700 p-4"
        onSubmit={(event) => void submit(event)}
        onChange={(event) => {
          if (!(event.target instanceof HTMLInputElement && event.target.type === 'checkbox'))
            setConfirmed(false);
        }}
      >
        <h2 className="text-xl font-semibold">Administrationsschritt</h2>
        <label className="block">
          Aktion
          <select
            className={inputClass}
            value={action}
            onChange={(event) => {
              setAction(event.target.value as Action);
              setConfirmed(false);
            }}
          >
            {actions.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        {['sector', 'reference'].includes(action) && (
          <div className="grid gap-3 sm:grid-cols-2">
            <label>
              Code
              <input
                required
                maxLength={50}
                className={inputClass}
                value={code}
                onChange={(event) => setCode(event.target.value)}
              />
            </label>
            <label>
              Name
              <input
                required
                maxLength={200}
                className={inputClass}
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <label>
              Version
              <input
                required
                maxLength={50}
                className={inputClass}
                value={version}
                onChange={(event) => setVersion(event.target.value)}
              />
            </label>
            {action === 'sector' && (
              <label>
                Klassifikationssystem
                <input
                  required
                  className={inputClass}
                  maxLength={100}
                  value={system}
                  onChange={(event) => setSystem(event.target.value)}
                />
              </label>
            )}
          </div>
        )}
        {needsReference && (
          <label className="block">
            Markt- / Sektor-Benchmark
            <select
              required
              className={inputClass}
              value={reference}
              onChange={(event) => {
                setReference(event.target.value);
                setConfirmed(false);
              }}
            >
              <option value="">Bitte wählen</option>
              {catalog?.references
                .filter((item) => item.identity.active)
                .map(({ identity: item }) => (
                  <option key={item.key} value={item.reference_id ?? ''}>
                    {item.name} · {item.reference_code}
                  </option>
                ))}
            </select>
            <span className="text-sm text-slate-400">
              {identity?.provider_identity ?? 'Kein Mapping'} · {identity?.mapping_status} ·{' '}
              {identity?.return_basis}
            </span>
          </label>
        )}
        {needsSector && (
          <label className="block">
            Administrierter Sektor
            <select
              required
              className={inputClass}
              value={sector}
              onChange={(event) => setSector(event.target.value)}
            >
              <option value="">Bitte wählen</option>
              {catalog?.sectors.map(({ context }) => (
                <option key={context.id} value={context.id}>
                  {context.classification_system} · {context.code} · {context.name}
                </option>
              ))}
            </select>
          </label>
        )}
        {needsUnderlying && (
          <UnderlyingSearchCombobox
            value={underlying}
            onChange={setUnderlying}
            selectLabel="Basiswert / ETF"
          />
        )}
        {needsListing && (
          <label className="block">
            Eindeutige Notierung
            {listings.length ? (
              <select
                required
                className={inputClass}
                value={listing}
                onChange={(event) => setListing(event.target.value)}
              >
                <option value="">Bitte wählen</option>
                {listings.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.ticker} · {item.trading_venue_mic} · {item.currency_code}
                  </option>
                ))}
              </select>
            ) : (
              <input
                required
                className={inputClass}
                value={listing}
                onChange={(event) => setListing(event.target.value)}
                placeholder="Listing-ID oder Basiswert oben wählen"
              />
            )}
          </label>
        )}
        {action.endsWith('Mapping') && (
          <div className="grid gap-3 sm:grid-cols-2">
            <label>
              Geprüftes EODHD-Symbol
              <input
                required
                className={inputClass}
                value={symbol}
                onChange={(event) => setSymbol(event.target.value)}
              />
            </label>
            <label>
              Geprüfter EODHD-Exchange-Code
              <input
                required
                className={inputClass}
                value={exchange}
                onChange={(event) => setExchange(event.target.value)}
              />
            </label>
            <p className="text-sm text-slate-400 sm:col-span-2">
              Ticker und MIC sind kein bestätigtes Provider-Mapping. Index direkt als Referenz; ETF
              über seine echte Notierung.
            </p>
          </div>
        )}
        {action === 'basis' && (
          <label className="block">
            Belegte Indexserie
            <select
              className={inputClass}
              value={basis}
              onChange={(event) => setBasis(event.target.value)}
            >
              <option value="PRICE_INDEX">Kursindex</option>
              <option value="TOTAL_RETURN_INDEX">Total-Return-Index</option>
            </select>
          </label>
        )}
        {(assignment || action === 'basis') && (
          <label className="block">
            Quellenbeleg (HTTPS)
            <input
              type="url"
              pattern="https://.*"
              required
              maxLength={assignment ? 200 : 500}
              className={inputClass}
              value={source}
              onChange={(event) => setSource(event.target.value)}
            />
          </label>
        )}
        {(assignment || importing) && (
          <label className="block">
            {assignment ? 'Zuordnung gültig ab' : 'Import von'}
            <input
              required
              className={inputClass}
              type="date"
              value={start}
              max={end}
              onChange={(event) => setStart(event.target.value)}
            />
          </label>
        )}
        {importing && (
          <>
            <label className="block">
              Import bis
              <input
                required
                type="date"
                className={inputClass}
                value={end}
                max={today()}
                min={start}
                onChange={(event) => setEnd(event.target.value)}
              />
            </label>
            <p className="text-sm text-slate-400">
              Ein kontrollierter Import, maximal 10 Jahre pro Anfrage. Abrufkosten und Zugriff
              richten sich nach der vorhandenen Provider-Konfiguration. Keine automatischen
              Wiederholungen.
            </p>
          </>
        )}
        {assignment && (
          <p className="text-sm text-slate-400">
            Vorhandene gültige Zuordnungen zuerst in der Abdeckungsmatrix prüfen. Überschneidungen
            werden vom Backend abgewiesen.
          </p>
        )}
        <label className="flex gap-2">
          <input
            required
            type="checkbox"
            checked={confirmed}
            onChange={(event) => setConfirmed(event.target.checked)}
          />
          Ich habe Identität, Quellenbeleg und den gewählten Schritt geprüft.
        </label>
        <button
          disabled={!confirmed || busy}
          className="rounded border border-sky-600 px-4 py-2 disabled:opacity-40"
        >
          {busy ? 'Schritt wird ausgeführt …' : 'Geprüften Schritt ausführen'}
        </button>
        <Link className="ml-4 text-sky-300 underline" to="/market-charts">
          Abdeckung prüfen
        </Link>
      </form>
    </div>
  );
}
