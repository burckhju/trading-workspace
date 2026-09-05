import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { marketApiClient } from '../../market/services/client';
import type { UnderlyingDetailResponse } from '../../market/types/api';
import { AnalysisStatusBadge } from '../components/AnalysisStatusBadge';
import { UnderlyingSearchCombobox } from '../components/UnderlyingSearchCombobox';
import { analysisApiClient } from '../services/client';
import type { AnalysisOverviewView } from '../services/savedViews';
import { analysisPreferenceClient } from '../services/preferencesClient';
import type { AnalysisOverview } from '../types/api';

const statusLabels: Record<string, string> = {
  COMPLETED: 'Abgeschlossen',
  COMPLETED_WITH_WARNINGS: 'Mit Hinweisen',
  NOT_EVALUABLE: 'Nicht auswertbar',
  FAILED: 'Fehlgeschlagen',
};

const qualityLabels: Record<string, string> = {
  GOOD: 'Gut',
  LIMITED: 'Eingeschränkt',
  INSUFFICIENT: 'Unzureichend',
};

export function MarketAnalysisPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState<AnalysisOverview[]>([]);
  const [analysisTotal, setAnalysisTotal] = useState(0);
  const [analysisOffset, setAnalysisOffset] = useState(
    () => Number(searchParams.get('offset') ?? 0) || 0,
  );
  const [statusFilter, setStatusFilter] = useState(() => searchParams.get('status') ?? '');
  const [qualityFilter, setQualityFilter] = useState(
    () => searchParams.get('quality_status') ?? '',
  );
  const [analysisTimeFrom, setAnalysisTimeFrom] = useState(
    () => searchParams.get('analysis_time_from') ?? '',
  );
  const [analysisTimeTo, setAnalysisTimeTo] = useState(
    () => searchParams.get('analysis_time_to') ?? '',
  );
  const [sortBy, setSortBy] = useState(() => searchParams.get('sort_by') ?? 'created_at');
  const [sortDirection, setSortDirection] = useState(
    () => searchParams.get('sort_direction') ?? 'desc',
  );
  const [overviewUnderlyingId, setOverviewUnderlyingId] = useState(
    () => searchParams.get('underlying_id') ?? '',
  );
  const [savedViews, setSavedViews] = useState<AnalysisOverviewView[]>([]);
  const [overviewUnderlyingLabel, setOverviewUnderlyingLabel] = useState('');
  const [savedViewName, setSavedViewName] = useState('');
  const [selectedSavedViewId, setSelectedSavedViewId] = useState('');
  const analysisLimit = 20;
  const [selectedUnderlyingId, setSelectedUnderlyingId] = useState('');
  const [selectedUnderlyingLabel, setSelectedUnderlyingLabel] = useState('');
  const [underlyingDetail, setUnderlyingDetail] = useState<UnderlyingDetailResponse | null>(null);
  const [listingId, setListingId] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    analysisPreferenceClient
      .list(controller.signal)
      .then(setSavedViews)
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          setMessage(
            error instanceof Error
              ? error.message
              : 'Gespeicherte Ansichten konnten nicht geladen werden.',
          );
        }
      });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    const params = new URLSearchParams();
    if (analysisOffset > 0) params.set('offset', String(analysisOffset));
    if (overviewUnderlyingId) params.set('underlying_id', overviewUnderlyingId);
    if (statusFilter) params.set('status', statusFilter);
    if (qualityFilter) params.set('quality_status', qualityFilter);
    if (analysisTimeFrom) params.set('analysis_time_from', analysisTimeFrom);
    if (analysisTimeTo) params.set('analysis_time_to', analysisTimeTo);
    if (sortBy !== 'created_at') params.set('sort_by', sortBy);
    if (sortDirection !== 'desc') params.set('sort_direction', sortDirection);
    setSearchParams(params, { replace: true });
  }, [
    analysisOffset,
    overviewUnderlyingId,
    statusFilter,
    qualityFilter,
    analysisTimeFrom,
    analysisTimeTo,
    sortBy,
    sortDirection,
    setSearchParams,
  ]);

  const loadAnalyses = useCallback(
    async (signal?: AbortSignal) => {
      const page = await analysisApiClient.listPage(
        analysisOffset,
        analysisLimit,
        {
          underlyingId: overviewUnderlyingId || undefined,
          status: statusFilter || undefined,
          qualityStatus: qualityFilter || undefined,
          analysisTimeFrom: analysisTimeFrom || undefined,
          analysisTimeTo: analysisTimeTo || undefined,
          sortBy,
          sortDirection,
        },
        signal,
      );
      setItems(page.items);
      setAnalysisTotal(page.total);
    },
    [
      analysisOffset,
      overviewUnderlyingId,
      statusFilter,
      qualityFilter,
      analysisTimeFrom,
      analysisTimeTo,
      sortBy,
      sortDirection,
    ],
  );

  useEffect(() => {
    const controller = new AbortController();
    loadAnalyses(controller.signal)
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          setMessage(
            error instanceof Error ? error.message : 'Analysen konnten nicht geladen werden.',
          );
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [loadAnalyses]);

  useEffect(() => {
    if (selectedUnderlyingId === '') {
      setUnderlyingDetail(null);
      setListingId('');
      return;
    }
    const controller = new AbortController();
    marketApiClient
      .getUnderlying(selectedUnderlyingId, controller.signal)
      .then((detail) => {
        setUnderlyingDetail(detail);
        const primary = detail.listings.find(
          (listing) => listing.is_primary && listing.lifecycle_status === 'ACTIVE',
        );
        const firstActive = detail.listings.find(
          (listing) => listing.lifecycle_status === 'ACTIVE',
        );
        setListingId(primary?.id ?? firstActive?.id ?? '');
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          setMessage(
            error instanceof Error ? error.message : 'Listings konnten nicht geladen werden.',
          );
        }
      });
    return () => controller.abort();
  }, [selectedUnderlyingId]);

  const activeListings = useMemo(
    () =>
      underlyingDetail?.listings.filter((listing) => listing.lifecycle_status === 'ACTIVE') ?? [],
    [underlyingDetail],
  );

  const activeFilters = [
    overviewUnderlyingId
      ? {
          key: 'underlying',
          label: `Basiswert: ${overviewUnderlyingLabel || overviewUnderlyingId}`,
        }
      : null,
    statusFilter
      ? { key: 'status', label: `Status: ${statusLabels[statusFilter] ?? statusFilter}` }
      : null,
    qualityFilter
      ? { key: 'quality', label: `Qualität: ${qualityLabels[qualityFilter] ?? qualityFilter}` }
      : null,
    analysisTimeFrom
      ? { key: 'from', label: `Ab: ${new Date(analysisTimeFrom).toLocaleString('de-DE')}` }
      : null,
    analysisTimeTo
      ? { key: 'to', label: `Bis: ${new Date(analysisTimeTo).toLocaleString('de-DE')}` }
      : null,
  ].filter((filter): filter is { key: string; label: string } => filter !== null);

  function removeFilter(key: string) {
    if (key === 'underlying') {
      setOverviewUnderlyingId('');
      setOverviewUnderlyingLabel('');
    }
    if (key === 'status') setStatusFilter('');
    if (key === 'quality') setQualityFilter('');
    if (key === 'from') setAnalysisTimeFrom('');
    if (key === 'to') setAnalysisTimeTo('');
    setAnalysisOffset(0);
  }

  function resetFilters() {
    setOverviewUnderlyingId('');
    setOverviewUnderlyingLabel('');
    setStatusFilter('');
    setQualityFilter('');
    setAnalysisTimeFrom('');
    setAnalysisTimeTo('');
    setSortBy('created_at');
    setSortDirection('desc');
    setAnalysisOffset(0);
  }

  function applySavedView(viewId: string) {
    setSelectedSavedViewId(viewId);
    const view = savedViews.find((item) => item.id === viewId);
    if (!view) return;
    setOverviewUnderlyingId(view.underlyingId);
    setOverviewUnderlyingLabel(view.underlyingLabel);
    setStatusFilter(view.status);
    setQualityFilter(view.qualityStatus);
    setAnalysisTimeFrom(view.analysisTimeFrom);
    setAnalysisTimeTo(view.analysisTimeTo);
    setSortBy(view.sortBy);
    setSortDirection(view.sortDirection);
    setAnalysisOffset(0);
  }

  async function saveCurrentView() {
    const name = savedViewName.trim();
    if (!name) return;
    try {
      const view = await analysisPreferenceClient.create({
        name,
        underlyingId: overviewUnderlyingId,
        underlyingLabel: overviewUnderlyingLabel,
        status: statusFilter,
        qualityStatus: qualityFilter,
        analysisTimeFrom,
        analysisTimeTo,
        sortBy,
        sortDirection,
      });
      setSavedViews((current) =>
        [...current, view].sort((left, right) => left.name.localeCompare(right.name)),
      );
      setSavedViewName('');
      setSelectedSavedViewId(view.id);
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : 'Ansicht konnte nicht gespeichert werden.',
      );
    }
  }

  async function deleteSelectedView() {
    if (!selectedSavedViewId) return;
    try {
      await analysisPreferenceClient.delete(selectedSavedViewId);
      setSavedViews((current) => current.filter((item) => item.id !== selectedSavedViewId));
      setSelectedSavedViewId('');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Ansicht konnte nicht gelöscht werden.');
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      await analysisApiClient.create(selectedUnderlyingId, listingId);
      setSelectedUnderlyingId('');
      setSelectedUnderlyingLabel('');
      setUnderlyingDetail(null);
      setListingId('');
      await loadAnalyses();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : 'Marktanalyse konnte nicht angelegt werden.',
      );
    }
  }

  return (
    <section className="w-full space-y-8">
      <header>
        <p className="text-sm uppercase tracking-wider text-slate-400">FT-006</p>
        <h1 className="text-3xl font-semibold">Marktanalyse</h1>
        <p className="mt-2 max-w-3xl text-slate-400">
          Nachvollziehbare, reproduzierbare Auswertung persistierter EOD-Marktdaten. Keine
          Handelsentscheidung.
        </p>
      </header>

      <form
        onSubmit={(event) => void submit(event)}
        className="grid gap-4 rounded-xl border border-slate-800 p-5 md:grid-cols-3"
      >
        <label className="text-sm">
          Basiswert suchen
          <div className="mt-2">
            <UnderlyingSearchCombobox
              value={selectedUnderlyingId}
              selectedLabel={selectedUnderlyingLabel}
              selectLabel="Basiswert"
              emptyOptionLabel="Basiswert auswählen"
              required
              onChange={(id, label) => {
                setSelectedUnderlyingId(id);
                setSelectedUnderlyingLabel(label);
              }}
            />
          </div>
        </label>
        <label className="text-sm">
          Listing
          <select
            required
            aria-label="Listing"
            value={listingId}
            disabled={selectedUnderlyingId === '' || activeListings.length === 0}
            onChange={(event) => setListingId(event.target.value)}
            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 disabled:opacity-50"
          >
            <option value="">Listing auswählen</option>
            {activeListings.map((listing) => (
              <option key={listing.id} value={listing.id}>
                {listing.ticker} ·{' '}
                {listing.trading_venue_name ?? listing.trading_venue_mic ?? 'Markt'} ·{' '}
                {listing.currency_code}
                {listing.is_primary ? ' · Primär' : ''}
              </option>
            ))}
          </select>
        </label>
        <button
          disabled={selectedUnderlyingId === '' || listingId === ''}
          className="self-end rounded-lg bg-slate-100 px-4 py-2 text-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Analyse anlegen
        </button>
      </form>

      {message ? (
        <p role="alert" className="rounded-lg border border-amber-700 p-3 text-amber-200">
          {message}
        </p>
      ) : null}

      <div className="space-y-4 rounded-xl border border-slate-800 p-4">
        <div className="grid gap-3 md:grid-cols-3">
          <label className="text-sm">
            Basiswert
            <UnderlyingSearchCombobox
              value={overviewUnderlyingId}
              selectedLabel={overviewUnderlyingLabel}
              onChange={(id, label) => {
                setOverviewUnderlyingId(id);
                setOverviewUnderlyingLabel(label);
                setAnalysisOffset(0);
              }}
            />
          </label>
          <label className="text-sm">
            Status
            <select
              aria-label="Status filtern"
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value);
                setAnalysisOffset(0);
              }}
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
            >
              <option value="">Alle</option>
              <option value="COMPLETED">Abgeschlossen</option>
              <option value="COMPLETED_WITH_WARNINGS">Mit Hinweisen</option>
              <option value="NOT_EVALUABLE">Nicht auswertbar</option>
              <option value="FAILED">Fehlgeschlagen</option>
            </select>
          </label>
          <label className="text-sm">
            Qualität
            <select
              aria-label="Qualität filtern"
              value={qualityFilter}
              onChange={(event) => {
                setQualityFilter(event.target.value);
                setAnalysisOffset(0);
              }}
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
            >
              <option value="">Alle</option>
              <option value="GOOD">Gut</option>
              <option value="LIMITED">Eingeschränkt</option>
              <option value="INSUFFICIENT">Unzureichend</option>
            </select>
          </label>
          <label className="text-sm">
            Analysezeit ab
            <input
              aria-label="Analysezeit ab"
              type="datetime-local"
              value={analysisTimeFrom}
              max={analysisTimeTo || undefined}
              onChange={(event) => {
                setAnalysisTimeFrom(event.target.value);
                setAnalysisOffset(0);
              }}
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
            />
          </label>
          <label className="text-sm">
            Analysezeit bis
            <input
              aria-label="Analysezeit bis"
              type="datetime-local"
              value={analysisTimeTo}
              min={analysisTimeFrom || undefined}
              onChange={(event) => {
                setAnalysisTimeTo(event.target.value);
                setAnalysisOffset(0);
              }}
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
            />
          </label>
          <label className="text-sm">
            Sortierung
            <select
              aria-label="Sortieren nach"
              value={sortBy}
              onChange={(event) => {
                setSortBy(event.target.value);
                setAnalysisOffset(0);
              }}
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
            >
              <option value="created_at">Erstellt</option>
              <option value="underlying_name">Basiswert</option>
              <option value="latest_analysis_time">Letzte Analyse</option>
              <option value="latest_status">Status</option>
              <option value="latest_quality_status">Qualität</option>
            </select>
          </label>
          <label className="text-sm">
            Richtung
            <select
              aria-label="Sortierrichtung"
              value={sortDirection}
              onChange={(event) => {
                setSortDirection(event.target.value);
                setAnalysisOffset(0);
              }}
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
            >
              <option value="desc">Absteigend</option>
              <option value="asc">Aufsteigend</option>
            </select>
          </label>
        </div>
        <div className="grid gap-2 border-t border-slate-800 pt-4 md:grid-cols-[1fr_1fr_auto_auto]">
          <label className="text-sm">
            Gespeicherte Ansicht
            <select
              aria-label="Gespeicherte Ansicht"
              value={selectedSavedViewId}
              onChange={(event) => applySavedView(event.target.value)}
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
            >
              <option value="">Ansicht auswählen</option>
              {savedViews.map((view) => (
                <option key={view.id} value={view.id}>
                  {view.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Neue Ansicht
            <input
              aria-label="Name der Ansicht"
              value={savedViewName}
              onChange={(event) => setSavedViewName(event.target.value)}
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
              placeholder="z. B. Gute Siemens-Analysen"
            />
          </label>
          <button
            type="button"
            onClick={() => void saveCurrentView()}
            disabled={!savedViewName.trim()}
            className="self-end rounded-lg border border-slate-700 px-3 py-2 disabled:opacity-40"
          >
            Ansicht speichern
          </button>
          <button
            type="button"
            onClick={() => void deleteSelectedView()}
            disabled={!selectedSavedViewId}
            className="self-end rounded-lg border border-slate-700 px-3 py-2 disabled:opacity-40"
          >
            Ansicht löschen
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {activeFilters.map((filter) => (
            <button
              key={filter.key}
              type="button"
              aria-label={`${filter.label} entfernen`}
              onClick={() => removeFilter(filter.key)}
              className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-200"
            >
              {filter.label} ×
            </button>
          ))}
          <button
            type="button"
            onClick={resetFilters}
            disabled={
              activeFilters.length === 0 && sortBy === 'created_at' && sortDirection === 'desc'
            }
            className="ml-auto rounded-lg border border-slate-700 px-3 py-1.5 text-sm disabled:opacity-40"
          >
            Filter zurücksetzen
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between text-sm text-slate-400">
        <div className="flex items-center gap-4">
          <span>{analysisTotal} Analysen</span>
          <a
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-200"
            href={analysisApiClient.exportUrl({
              underlyingId: overviewUnderlyingId || undefined,
              status: statusFilter || undefined,
              qualityStatus: qualityFilter || undefined,
              analysisTimeFrom: analysisTimeFrom || undefined,
              analysisTimeTo: analysisTimeTo || undefined,
              sortBy,
              sortDirection,
            })}
          >
            CSV exportieren
          </a>
        </div>
        <div className="flex gap-3">
          <button
            type="button"
            disabled={analysisOffset === 0}
            onClick={() => setAnalysisOffset(Math.max(0, analysisOffset - analysisLimit))}
          >
            Zurück
          </button>
          <button
            type="button"
            disabled={analysisOffset + analysisLimit >= analysisTotal}
            onClick={() => setAnalysisOffset(analysisOffset + analysisLimit)}
          >
            Weiter
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="p-3">Analyse</th>
              <th className="p-3">Basiswert</th>
              <th className="p-3">Listing</th>
              <th className="p-3">Letzter Lauf</th>
              <th className="p-3">Erstellt</th>
            </tr>
          </thead>
          <tbody>
            {!loading && items.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-6 text-center text-slate-400">
                  Noch keine Marktanalysen vorhanden.
                </td>
              </tr>
            ) : null}
            {items.map((item) => (
              <tr key={item.id} className="border-t border-slate-800">
                <td className="p-3">
                  <Link className="font-medium underline" to={`/market-analyses/${item.id}`}>
                    Details öffnen
                  </Link>
                  <div className="font-mono text-xs text-slate-500">{item.id}</div>
                </td>
                <td className="p-3">
                  <div className="font-medium">{item.underlying_name}</div>
                  <div className="font-mono text-xs text-slate-500">{item.underlying_id}</div>
                </td>
                <td className="p-3">
                  <div>
                    {item.ticker} · {item.trading_venue_name} ({item.trading_venue_mic}) ·{' '}
                    {item.currency_code}
                  </div>
                  <div className="font-mono text-xs text-slate-500">{item.listing_id}</div>
                </td>
                <td className="p-3">
                  {item.latest_status ? (
                    <>
                      <div>
                        <span className="flex flex-wrap gap-2">
                          <AnalysisStatusBadge value={item.latest_status} kind="status" />
                          {item.latest_quality_status ? (
                            <AnalysisStatusBadge
                              value={item.latest_quality_status}
                              kind="quality"
                            />
                          ) : null}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500">
                        Version {item.latest_version} ·{' '}
                        {item.latest_analysis_time
                          ? new Date(item.latest_analysis_time).toLocaleString('de-DE')
                          : '—'}
                      </div>
                    </>
                  ) : (
                    <span className="text-slate-500">Noch nicht ausgeführt</span>
                  )}
                </td>
                <td className="p-3">{new Date(item.created_at).toLocaleString('de-DE')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
