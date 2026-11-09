import { useCallback, useEffect, useRef, useState } from 'react';
import { chartRangeStart } from '../services/chartRanges';
import { watchlistClient } from '../services/watchlistClient';
import type { ChartWatchlist } from '../types/watchlist';
import { WatchlistChartCard } from './WatchlistChartCard';
import { useWatchlistSeries } from './useWatchlistSeries';

const noItems: ChartWatchlist['items'] = [];

export function ChartWatchlistOverview({
  end,
  period,
  field,
  onOpenDetail,
  chartParams,
}: {
  end: string;
  period: string;
  field: 'CLOSE' | 'ADJUSTED_CLOSE';
  onOpenDetail: (targets: string[]) => void;
  chartParams?: URLSearchParams;
}) {
  const [data, setData] = useState<ChartWatchlist | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [activating, setActivating] = useState(false);
  const [activationMessage, setActivationMessage] = useState('');
  const [activationUncertain, setActivationUncertain] = useState(false);
  const [query, setQuery] = useState('');
  const [group, setGroup] = useState('');
  const [selectedTargets, setSelectedTargets] = useState<string[]>([]);
  const mounted = useRef(false);
  const readController = useRef<AbortController | null>(null);
  const readGeneration = useRef(0);
  const reading = useRef(false);
  const activationLock = useRef(false);

  const read = useCallback(async () => {
    if (activationLock.current) return;
    const generation = ++readGeneration.current;
    readController.current?.abort();
    const controller = new AbortController();
    readController.current = controller;
    reading.current = true;
    setLoading(true);
    try {
      const value = await watchlistClient.read(controller.signal);
      if (!mounted.current || controller.signal.aborted || generation !== readGeneration.current)
        return;
      setData(value);
      setError('');
      setActivationUncertain(false);
    } catch (reason: unknown) {
      if (!mounted.current || controller.signal.aborted || generation !== readGeneration.current)
        return;
      setError(reason instanceof Error ? reason.message : 'Marktübersicht nicht lesbar.');
    } finally {
      if (mounted.current && generation === readGeneration.current) {
        reading.current = false;
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    void read();
    const poll = () => {
      if (document.visibilityState === 'visible' && !reading.current && !activationLock.current)
        void read();
    };
    const timer = window.setInterval(poll, 60_000);
    document.addEventListener('visibilitychange', poll);
    return () => {
      mounted.current = false;
      readController.current?.abort();
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', poll);
    };
  }, [read]);

  async function activate() {
    if (!data || data.enabled || activationLock.current || activationUncertain) return;
    activationLock.current = true;
    readController.current?.abort();
    ++readGeneration.current;
    reading.current = false;
    setLoading(false);
    setActivating(true);
    setActivationMessage('');
    setError('');
    try {
      const value = await watchlistClient.activate(data.catalog_version);
      if (!mounted.current) return;
      if (
        value.items.length !== data.items.length ||
        !value.items.every((item) => data.items.some((shown) => shown.code === item.code))
      )
        throw new Error('Die Aktivierungsantwort bestätigt nicht die angezeigte Auswahl.');
      setData(value);
      setActivationMessage(
        'Marktübersicht dauerhaft aktiviert. Der Hintergrundauftrag richtet fehlende Datenbasen ein und liest abgeschlossene Tageskurse. Der Fortschritt steht bei jeder Reihe.',
      );
    } catch (reason: unknown) {
      if (!mounted.current) return;
      setActivationUncertain(true);
      setError(
        (reason instanceof Error ? reason.message : 'Aktivierungsantwort nicht lesbar.') +
          ' Der Ausgang ist nicht bestätigt. Zuerst den gespeicherten Stand erneut lesen.',
      );
    } finally {
      activationLock.current = false;
      if (mounted.current) setActivating(false);
    }
  }

  const items = data?.items ?? noItems;
  const { states, retry } = useWatchlistSeries(items, chartRangeStart(end, period), end, field);
  const selected = selectedTargets.filter((target) =>
    items.some((item) => item.target_key === target),
  );
  const groups = [...new Set(items.map((item) => item.group))];
  const needle = query.trim().toLocaleLowerCase('de-DE');
  const visibleItems = items.filter(
    (item) =>
      (!group || item.group === group) &&
      (!needle ||
        [item.name, item.code, item.ticker, item.isin]
          .join(' ')
          .toLocaleLowerCase('de-DE')
          .includes(needle)),
  );
  const button = 'rounded border border-slate-600 px-3 py-2 text-sm disabled:opacity-50';

  return (
    <section aria-labelledby="chart-watchlist-title" className="min-w-0 space-y-5">
      <header className="space-y-3 rounded-xl border border-slate-700 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 id="chart-watchlist-title" className="text-xl font-semibold">
              {data?.name ?? 'Marktübersicht'}
            </h2>
            <p className="mt-1 text-sm text-slate-300">
              Ein eigenes Diagramm je Reihe. US-gelistete Analyse-ETFs und ein direkter S&P 500;
              keine Rangliste.
            </p>
          </div>
          <button
            type="button"
            className={button}
            disabled={loading || activating}
            onClick={() => void read()}
          >
            {loading ? 'Stand wird gelesen …' : 'Gespeicherten Stand erneut lesen'}
          </button>
        </div>
        <p className="text-sm text-slate-300">
          Gespeicherte abgeschlossene Tageskurse (EOD), keine Intraday-Kurse. Eigene Einheiten und
          Preisachsen, keine Währungsumrechnung; Quellen und letzter Handelstag stehen an jeder
          Karte. Kalenderlücken werden nicht aufgefüllt.
        </p>
        {error && (
          <p className="break-words rounded border border-amber-700 p-3 text-sm text-amber-200">
            {error}
            {data ? ' Der zuvor gelesene Stand bleibt sichtbar.' : ''}
          </p>
        )}
        {activationMessage && (
          <p role="status" className="rounded border border-sky-700 p-3 text-sm">
            {activationMessage}
          </p>
        )}
        {data && !data.enabled && (
          <div className="space-y-3 rounded border border-sky-800 bg-sky-950/30 p-3">
            <p className="text-sm">
              Die unten aufgeführte Auswahl mit {items.length} Reihen und ihren Quellen wird
              einmalig für diesen Workspace gespeichert. Die Einrichtung verwendet vorhandene
              Identitäten und ruft über EODHD fehlende Daten ab. Die Liste bleibt auch bei
              geschlossenem Browser eingerichtet; die laufende EOD-Aktualisierung folgt dem unten
              angezeigten Betriebszustand des Backends.
            </p>
            <p className="text-sm">
              Der direkte S&P 500 wird gemäß Quellenbeleg als Kursindex ohne Dividenden
              eingerichtet.{' '}
              <a
                className="text-sky-300 underline"
                href="https://fred.stlouisfed.org/series/SP500"
                target="_blank"
                rel="noreferrer"
              >
                Quellenbeleg bei FRED / S&P Dow Jones Indices
              </a>
            </p>
            <button
              type="button"
              className="rounded border border-sky-500 bg-sky-950 px-4 py-2 text-sm font-semibold disabled:opacity-50"
              disabled={activating || loading || activationUncertain}
              onClick={() => void activate()}
            >
              {activating ? 'Aktivierung wird gespeichert …' : 'Marktübersicht einrichten'}
            </button>
          </div>
        )}
        {data?.enabled && (
          <p className="text-sm">
            Diese Auswahl ist dauerhaft gespeichert. Einrichtung und laufende Kursaktualisierung
            werden vom Backend ausgeführt.
          </p>
        )}
        {data && (
          <div className="space-y-1 text-xs text-slate-300">
            <p>
              Automatische Aktualisierung:{' '}
              {data.scheduler.enabled ? 'eingeschaltet' : 'ausgeschaltet'} · Runtime:{' '}
              {data.scheduler.running ? 'läuft' : 'läuft derzeit nicht'} · Aktiver Worker in diesem
              Backend: {data.scheduler.leader ? 'ja' : 'nein'}
            </p>
            {data.scheduler.last_error && (
              <p className="break-words text-amber-200">
                Aktualisierungsfehler: {data.scheduler.last_error}
              </p>
            )}
            {!data.scheduler.enabled && (
              <p className="text-amber-200">
                Die automatische Kursaktualisierung ist derzeit ausgeschaltet. Gespeicherte Werte
                bleiben lesbar.
              </p>
            )}
            {data.scheduler.provider_enabled === false && (
              <p className="text-amber-200">
                EODHD ist ausgeschaltet. Neue Providerabrufe sind nicht verfügbar; gespeicherte
                Daten und der Einrichtungsstand bleiben sichtbar.
              </p>
            )}
            <p>
              Katalog: {data.catalog_version}
              {data.scheduler.settings?.underlyings_interval_seconds != null
                ? ' · Konfiguriertes EOD-Intervall: ' +
                  data.scheduler.settings.underlyings_interval_seconds +
                  ' Sekunden'
                : ''}
            </p>
          </div>
        )}
      </header>
      {data && (
        <>
          <div className="flex flex-wrap items-end gap-3">
            <label className="grid min-w-0 flex-1 gap-1 text-sm">
              Übersicht filtern
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Name, Ticker oder ISIN"
                className="min-w-0 rounded border border-slate-600 bg-slate-950 p-2"
              />
            </label>
            <label className="grid min-w-0 gap-1 text-sm">
              Gruppe
              <select
                value={group}
                onChange={(event) => setGroup(event.target.value)}
                className="max-w-full rounded border border-slate-600 bg-slate-950 p-2"
              >
                <option value="">Alle Gruppen</option>
                {groups.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className={button}
              disabled={selected.length < 2}
              onClick={() => onOpenDetail(selected)}
            >
              Auswahl vergleichen ({selected.length}/4)
            </button>
          </div>
          <p className="text-xs text-slate-400">
            {visibleItems.length} von {items.length} Reihen sichtbar. Filtern und Vergleichsauswahl
            ändern keine Daten und lösen keinen Providerabruf aus.
          </p>
          {visibleItems.length === 0 && <p>Keine Reihe entspricht diesem lokalen Filter.</p>}
          <div className="grid min-w-0 grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {visibleItems.map((item) => (
              <WatchlistChartCard
                key={item.code}
                item={item}
                chartParams={chartParams}
                state={
                  states[item.code] ?? {
                    loading: Boolean(item.target_key),
                    result: null,
                    error: null,
                  }
                }
                selected={Boolean(item.target_key && selected.includes(item.target_key))}
                comparisonFull={selected.length >= 4}
                onSelect={() => {
                  const target = item.target_key;
                  if (!target) return;
                  setSelectedTargets((current) => {
                    const present = current.filter((value) =>
                      items.some((entry) => entry.target_key === value),
                    );
                    return present.includes(target)
                      ? present.filter((value) => value !== target)
                      : [...present, target].slice(0, 4);
                  });
                }}
                onOpen={() => item.target_key && onOpenDetail([item.target_key])}
                onRetry={() => retry(item.code)}
              />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
