import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import {
  topDownAdminClient,
  type MarketReference,
  type ProviderMapping,
  type Sector,
  type VenueReconciliation,
} from '../services/topDownAdminClient';

function dateOffset(days: number) {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function TopDownWorkflowActionPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const action = params.get('action') ?? '';
  const candidateId = params.get('candidate_id') ?? '';
  const resourceId = params.get('resource_id') ?? '';
  const underlyingId = params.get('underlying_id') ?? '';
  const listingId = params.get('listing_id') ?? resourceId;
  const mappingId = params.get('mapping_id') ?? resourceId;
  const sectorId = params.get('sector_id') ?? resourceId;

  const [references, setReferences] = useState<MarketReference[]>([]);
  const [sectors, setSectors] = useState<Sector[]>([]);
  const [mappings, setMappings] = useState<ProviderMapping[]>([]);
  const [selected, setSelected] = useState('');
  const [manualListing, setManualListing] = useState(listingId);
  const [symbol, setSymbol] = useState('');
  const [exchange, setExchange] = useState('');
  const [startDate, setStartDate] = useState(dateOffset(-400));
  const [endDate, setEndDate] = useState(dateOffset(0));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [venueReconciliation, setVenueReconciliation] = useState<VenueReconciliation | null>(null);

  useEffect(() => {
    Promise.all([
      topDownAdminClient.references(),
      topDownAdminClient.sectors(),
      topDownAdminClient.mappings(),
    ])
      .then(([refs, sectorValues, mappingValues]) => {
        setReferences(refs.filter((item) => item.active));
        setSectors(sectorValues.filter((item) => item.active));
        setMappings(mappingValues);
      })
      .catch((value: unknown) =>
        setError(
          value instanceof Error
            ? value.message
            : 'Administrationsdaten konnten nicht geladen werden.',
        ),
      );
  }, []);

  const mappingForListing = useMemo(
    () => mappings.find((item) => item.listing_id === listingId) ?? null,
    [mappings, listingId],
  );

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setVenueReconciliation(null);
    try {
      switch (action) {
        case 'ASSIGN_BROAD_MARKET_BENCHMARK':
          await topDownAdminClient.assignBenchmark(underlyingId, selected);
          break;
        case 'ASSIGN_SECTOR':
          await topDownAdminClient.assignSector(underlyingId, selected);
          break;
        case 'ASSIGN_SECTOR_REFERENCE':
          await topDownAdminClient.assignSectorReference(sectorId, selected);
          break;
        case 'ASSIGN_REFERENCE_LISTING':
          await topDownAdminClient.assignReferenceListing(resourceId, manualListing);
          break;
        case 'CREATE_EODHD_MAPPING':
          await topDownAdminClient.createMapping(listingId, symbol, exchange);
          break;
        case 'VALIDATE_EODHD_MAPPING': {
          await topDownAdminClient.validateMapping(mappingId);
          const reconciliation = await topDownAdminClient.venueReconciliation(mappingId);
          setVenueReconciliation(reconciliation);
          if (reconciliation.status !== 'MATCHED') return;
          break;
        }
        case 'ACTIVATE_OR_REASSIGN_BENCHMARK':
          await topDownAdminClient.activateReference(
            params.get('market_reference_id') ?? resourceId,
          );
          break;
        case 'ACTIVATE_OR_REASSIGN_SECTOR_REFERENCE':
          await topDownAdminClient.activateReference(
            params.get('market_reference_id') ?? resourceId,
          );
          break;
        case 'ACTIVATE_OR_REASSIGN_SECTOR':
          await topDownAdminClient.activateSector(params.get('sector_id') ?? resourceId);
          break;
        case 'IMPORT_DAILY_PRICE_HISTORY': {
          const resolvedMapping = params.get('mapping_id') ?? mappingForListing?.id;
          if (!resolvedMapping) throw new Error('Kein Provider-Mapping für das Listing gefunden.');
          await topDownAdminClient.importHistory(listingId, resolvedMapping, startDate, endDate);
          break;
        }
        case 'RUN_MARKET_ANALYSIS': {
          if (!underlyingId || !listingId) throw new Error('Underlying- oder Listing-ID fehlt.');
          const analysis = await topDownAdminClient.createAnalysis(underlyingId, listingId);
          await topDownAdminClient.runAnalysis(analysis.id, startDate, endDate);
          break;
        }
        default:
          throw new Error(`Aktion ${action || 'unbekannt'} besitzt noch kein Formular.`);
      }
      void navigate(`/candidates?candidate=${encodeURIComponent(candidateId)}`);
    } catch (value: unknown) {
      setError(value instanceof Error ? value.message : 'Aktion fehlgeschlagen.');
    } finally {
      setBusy(false);
    }
  }

  const selectOptions = action === 'ASSIGN_SECTOR' ? sectors : references;
  const needsSelect = [
    'ASSIGN_BROAD_MARKET_BENCHMARK',
    'ASSIGN_SECTOR',
    'ASSIGN_SECTOR_REFERENCE',
  ].includes(action);

  return (
    <div className="mx-auto max-w-2xl">
      <p className="text-xs uppercase tracking-wide text-slate-500">Top-down Administration</p>
      <h1 className="mt-1 text-2xl font-semibold">Workflow-Schritt ausführen</h1>
      <p className="mt-2 text-sm text-slate-400">{action}</p>
      {error && <p className="mt-5 rounded-lg border border-rose-800 p-3 text-sm">{error}</p>}
      {venueReconciliation && (
        <div className="mt-5 rounded-lg border border-amber-800 p-3 text-sm">
          <p className="font-medium">Venue-Reconciliation: {venueReconciliation.status}</p>
          <p className="mt-1 text-slate-300">{venueReconciliation.explanation}</p>
          {venueReconciliation.status !== 'MATCHED' && (
            <p className="mt-2 text-xs text-slate-400">
              Keine automatische Stammdatenänderung. Bitte nur den administrativen Sonderfall
              prüfen; der normale Trading-Workflow bleibt unverändert.
            </p>
          )}
        </div>
      )}
      {action === 'CREATE_OR_SELECT_PRIMARY_LISTING' ? (
        <div className="mt-6 rounded-xl border border-slate-800 p-5">
          <p className="text-sm text-slate-300">
            Für den Basiswert muss zuerst ein Primary Listing in der Basiswertverwaltung angelegt
            oder ausgewählt werden.
          </p>
          <div className="mt-4 flex gap-3">
            <Link
              to={`/underlyings/${underlyingId}`}
              className="rounded-lg border border-sky-700 px-4 py-2 text-sm"
            >
              Basiswert öffnen
            </Link>
            <Link
              to={`/candidates?candidate=${encodeURIComponent(candidateId)}`}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm"
            >
              Zurück
            </Link>
          </div>
        </div>
      ) : (
        <form
          onSubmit={(event) => void submit(event)}
          className="mt-6 space-y-5 rounded-xl border border-slate-800 p-5"
        >
          {needsSelect && (
            <label className="block text-sm">
              Auswahl
              <select
                required
                value={selected}
                onChange={(event) => setSelected(event.target.value)}
                className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2"
              >
                <option value="">Bitte auswählen</option>
                {selectOptions.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.code} – {item.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          {action === 'ASSIGN_REFERENCE_LISTING' && (
            <label className="block text-sm">
              Listing-ID
              <input
                required
                value={manualListing}
                onChange={(event) => setManualListing(event.target.value)}
                className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2"
              />
            </label>
          )}
          {action === 'CREATE_EODHD_MAPPING' && (
            <>
              <label className="block text-sm">
                EODHD Symbol
                <input
                  required
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2"
                />
              </label>
              <label className="block text-sm">
                EODHD Exchange Code
                <input
                  required
                  value={exchange}
                  onChange={(e) => setExchange(e.target.value)}
                  className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2"
                />
              </label>
              <p className="text-xs text-amber-300">
                Provider-Symbole werden nicht automatisch geraten. Bitte vor dem Validieren
                fachlich/providerseitig prüfen.
              </p>
            </>
          )}
          {['IMPORT_DAILY_PRICE_HISTORY', 'RUN_MARKET_ANALYSIS'].includes(action) && (
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-sm">
                Von
                <input
                  type="date"
                  required
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2"
                />
              </label>
              <label className="text-sm">
                Bis
                <input
                  type="date"
                  required
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2"
                />
              </label>
            </div>
          )}
          {[
            'ACTIVATE_OR_REASSIGN_BENCHMARK',
            'ACTIVATE_OR_REASSIGN_SECTOR',
            'ACTIVATE_OR_REASSIGN_SECTOR_REFERENCE',
          ].includes(action) && (
            <p className="text-sm text-slate-300">
              Die aktuell zugeordnete Referenz wird wieder aktiviert. Eine fachliche Neuzuordnung
              bleibt eine separate, historisierte Admin-Aktion.
            </p>
          )}
          {action === 'VALIDATE_EODHD_MAPPING' && (
            <p className="text-sm text-slate-300">
              Das Mapping wird über den bestehenden expliziten Validierungsprozess geprüft und
              aktiviert.
            </p>
          )}
          <div className="flex gap-3">
            <button
              disabled={busy}
              className="rounded-lg border border-sky-700 px-4 py-2 text-sm disabled:opacity-50"
            >
              {busy ? 'Wird ausgeführt …' : 'Aktion ausführen'}
            </button>
            <Link
              to={`/candidates?candidate=${encodeURIComponent(candidateId)}`}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm"
            >
              Abbrechen
            </Link>
          </div>
        </form>
      )}
    </div>
  );
}
