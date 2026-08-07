import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { AnalysisStatusBadge } from '../components/AnalysisStatusBadge';
import { analysisApiClient } from '../services/client';
import {
  defaultAnalysisParameters,
  type AnalysisDetail,
  type AnalysisEvent,
  type AnalysisParameters,
  type AnalysisRunDetail,
  type AnalysisVerification,
  type SnapshotPage,
} from '../types/api';

function isoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}
function fmt(value: string): string {
  return new Date(value).toLocaleString('de-DE');
}

function MetricTable({ metrics }: { metrics: Record<string, string | null> }) {
  return (
    <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {Object.entries(metrics).map(([name, value]) => (
        <div key={name} className="rounded-lg border border-slate-800 p-3">
          <dt className="text-xs uppercase tracking-wide text-slate-500">
            {name.replaceAll('_', ' ')}
          </dt>
          <dd className="mt-1 font-mono text-sm">{value ?? 'nicht verfügbar'}</dd>
        </div>
      ))}
    </dl>
  );
}

export function MarketAnalysisDetailPage() {
  const { analysisId = '' } = useParams();
  const [detail, setDetail] = useState<AnalysisDetail | null>(null);
  const [runDetail, setRunDetail] = useState<AnalysisRunDetail | null>(null);
  const [events, setEvents] = useState<AnalysisEvent[]>([]);
  const [verification, setVerification] = useState<AnalysisVerification | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [startDate, setStartDate] = useState(isoDate(new Date(Date.now() - 365 * 86400000)));
  const [endDate, setEndDate] = useState(isoDate(new Date()));
  const [parameters, setParameters] = useState<AnalysisParameters>(defaultAnalysisParameters);
  const [message, setMessage] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  const [replacementVersion, setReplacementVersion] = useState('');
  const [showSnapshot, setShowSnapshot] = useState(false);
  const [snapshotPage, setSnapshotPage] = useState<SnapshotPage | null>(null);
  const [snapshotOffset, setSnapshotOffset] = useState(0);
  const snapshotLimit = 50;

  const refresh = useCallback(
    async (signal?: AbortSignal) => {
      const [analysis, lifecycle] = await Promise.all([
        analysisApiClient.get(analysisId, signal),
        analysisApiClient.events(analysisId, signal),
      ]);
      setDetail(analysis);
      setEvents(lifecycle);
      return analysis;
    },
    [analysisId],
  );

  useEffect(() => {
    const c = new AbortController();

    void refresh(c.signal)
      .then((analysis) => {
        setSelectedVersion(analysis.runs.at(-1)?.version ?? null);
      })
      .catch((e: unknown) => {
        if (!(e instanceof DOMException && e.name === 'AbortError')) {
          setMessage(e instanceof Error ? e.message : 'Analyse konnte nicht geladen werden.');
        }
      });

    return () => c.abort();
  }, [refresh]);
  useEffect(() => {
    if (selectedVersion === null) {
      setRunDetail(null);
      return;
    }
    const c = new AbortController();
    analysisApiClient
      .getRun(analysisId, selectedVersion, c.signal)
      .then((r) => {
        setRunDetail(r);
        setVerification(null);
        setShowSnapshot(false);
        setSnapshotPage(null);
        setSnapshotOffset(0);
      })
      .catch((e: unknown) => {
        if (!(e instanceof DOMException && e.name === 'AbortError'))
          setMessage(
            e instanceof Error ? e.message : 'Analyseversion konnte nicht geladen werden.',
          );
      });
    return () => c.abort();
  }, [analysisId, selectedVersion]);
  useEffect(() => {
    if (!showSnapshot || selectedVersion === null) return;
    const c = new AbortController();
    analysisApiClient
      .getSnapshot(analysisId, selectedVersion, snapshotOffset, snapshotLimit, c.signal)
      .then(setSnapshotPage)
      .catch((e: unknown) => {
        if (!(e instanceof DOMException && e.name === 'AbortError'))
          setMessage(e instanceof Error ? e.message : 'Snapshot konnte nicht geladen werden.');
      });
    return () => c.abort();
  }, [analysisId, selectedVersion, showSnapshot, snapshotOffset]);

  const parameterEntries = useMemo(() => Object.entries(runDetail?.parameters ?? {}), [runDetail]);
  const selectedRun = detail?.runs.find((r) => r.version === selectedVersion) ?? null;
  const supersedeEvent =
    events.find((e) => e.event_type === 'SUPERSEDED' && e.source_version === selectedVersion) ??
    null;
  const retryable = selectedRun?.status === 'FAILED' || selectedRun?.status === 'NOT_EVALUABLE';
  const replacementCandidates = (detail?.runs ?? []).filter(
    (r) =>
      selectedVersion !== null &&
      r.version > selectedVersion &&
      ['COMPLETED', 'COMPLETED_WITH_WARNINGS', 'NOT_EVALUABLE'].includes(r.status),
  );
  function numberParameter(name: keyof AnalysisParameters, value: string) {
    setParameters((current) => ({ ...current, [name]: Number(value) }));
  }

  async function run(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      const created = await analysisApiClient.run(analysisId, {
        start_date: startDate,
        end_date: endDate,
        parameters,
      });
      await refresh();
      setSelectedVersion(created.version);
      setMessage(`Version ${created.version} wurde ausgeführt.`);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Analyse konnte nicht ausgeführt werden.');
    }
  }
  async function verify() {
    if (selectedVersion === null) return;
    setMessage(null);
    try {
      setVerification(await analysisApiClient.verify(analysisId, selectedVersion));
    } catch (e) {
      setMessage(
        e instanceof Error ? e.message : 'Reproduzierbarkeit konnte nicht geprüft werden.',
      );
    }
  }
  async function retry() {
    if (selectedVersion === null) return;
    setMessage(null);
    try {
      const created = await analysisApiClient.retry(analysisId, selectedVersion, reason);
      await refresh();
      setSelectedVersion(created.version);
      setReason('');
      setMessage(
        `Retry als Version ${created.version} ausgeführt; Version ${selectedVersion} wurde nachvollziehbar ersetzt.`,
      );
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Retry konnte nicht ausgeführt werden.');
    }
  }
  async function supersede() {
    if (selectedVersion === null || !replacementVersion) return;
    setMessage(null);
    try {
      await analysisApiClient.supersede(
        analysisId,
        selectedVersion,
        Number(replacementVersion),
        reason,
      );
      await refresh();
      setReason('');
      setReplacementVersion('');
      setMessage(`Version ${selectedVersion} wurde durch Version ${replacementVersion} ersetzt.`);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Version konnte nicht ersetzt werden.');
    }
  }

  if (!detail)
    return (
      <section className="space-y-4">
        <Link to="/market-analyses">Zurück zu Marktanalysen</Link>
        <p>{message ?? 'Analyse wird geladen …'}</p>
      </section>
    );

  return (
    <section className="space-y-8">
      <header>
        <Link className="text-sm text-slate-400 underline" to="/market-analyses">
          Zurück zu Marktanalysen
        </Link>
        <h1 className="mt-3 text-3xl font-semibold">Marktanalyse</h1>
        <p className="mt-2 font-mono text-xs text-slate-500">{detail.analysis.id}</p>
        <p className="mt-2 text-sm text-slate-400">
          Basiswert {detail.analysis.underlying_id} · Listing {detail.analysis.listing_id}
        </p>
      </header>

      <form
        onSubmit={(event) => void run(event)}
        className="space-y-4 rounded-xl border border-slate-800 p-5"
      >
        <h2 className="text-xl font-semibold">Neue Analyseversion</h2>
        <div className="grid gap-4 md:grid-cols-4">
          <label className="text-sm">
            Von
            <input
              aria-label="Von"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
            />
          </label>
          <label className="text-sm">
            Bis
            <input
              aria-label="Bis"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
            />
          </label>
          <label className="text-sm">
            Kurzfristiges Fenster
            <input
              aria-label="Kurzfristiges Fenster"
              type="number"
              min="1"
              value={parameters.short_window}
              onChange={(e) => numberParameter('short_window', e.target.value)}
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
            />
          </label>
          <label className="text-sm">
            Langfristiges Fenster
            <input
              aria-label="Langfristiges Fenster"
              type="number"
              min="1"
              value={parameters.long_window}
              onChange={(e) => numberParameter('long_window', e.target.value)}
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
            />
          </label>
        </div>
        <button className="rounded-lg bg-slate-100 px-4 py-2 text-slate-950">
          Analyse ausführen
        </button>
      </form>

      {message ? (
        <p role="alert" className="rounded-lg border border-amber-700 p-3 text-amber-200">
          {message}
        </p>
      ) : null}

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Versionshistorie</h2>
          {detail.runs.length ? (
            <select
              aria-label="Analyseversion"
              value={selectedVersion ?? ''}
              onChange={(e) => setSelectedVersion(Number(e.target.value))}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
            >
              {detail.runs.map((r) => (
                <option key={r.version} value={r.version}>
                  Version {r.version} · {r.status}
                </option>
              ))}
            </select>
          ) : null}
        </div>
        <div className="overflow-hidden rounded-xl border border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900 text-slate-400">
              <tr>
                <th className="p-3">Version</th>
                <th className="p-3">Status</th>
                <th className="p-3">Qualität</th>
                <th className="p-3">Zeitpunkt</th>
                <th className="p-3">Lebenszyklus</th>
              </tr>
            </thead>
            <tbody>
              {detail.runs.map((r) => {
                const ev = events.find(
                  (e) => e.event_type === 'SUPERSEDED' && e.source_version === r.version,
                );
                return (
                  <tr key={r.version} className="border-t border-slate-800">
                    <td className="p-3">{r.version}</td>
                    <td className="p-3">
                      <AnalysisStatusBadge value={r.status} kind="status" />
                    </td>
                    <td className="p-3">
                      <AnalysisStatusBadge value={r.quality_status} kind="quality" />
                    </td>
                    <td className="p-3">{fmt(r.analysis_time)}</td>
                    <td className="p-3">
                      {ev
                        ? `Ersetzt durch Version ${ev.replacement_version}`
                        : 'Aktiv/historisch unverändert'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {runDetail ? (
        <div className="space-y-8">
          <section className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-xl font-semibold">Ergebnis · Version {runDetail.run.version}</h2>
              <AnalysisStatusBadge value={runDetail.run.status} kind="status" />
              <AnalysisStatusBadge value={runDetail.run.quality_status} kind="quality" />
              {supersedeEvent ? (
                <span className="rounded-full border border-slate-600 px-2 py-1 text-xs">
                  Ersetzt durch Version {supersedeEvent.replacement_version}
                </span>
              ) : null}
            </div>
            <MetricTable metrics={runDetail.metrics} />
            {runDetail.notes.length ? (
              <div>
                <h3 className="font-medium">Hinweise</h3>
                <ul className="list-disc pl-5 text-sm text-slate-300">
                  {runDetail.notes.map((n) => (
                    <li key={n}>{n}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-semibold">Bewertungskriterien</h2>
            <div className="overflow-hidden rounded-xl border border-slate-800">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-900 text-slate-400">
                  <tr>
                    <th className="p-3">Kriterium</th>
                    <th className="p-3">Klassifikation</th>
                    <th className="p-3">Wert</th>
                    <th className="p-3">Erklärung</th>
                  </tr>
                </thead>
                <tbody>
                  {runDetail.criteria.map((c) => (
                    <tr key={c.code} className="border-t border-slate-800">
                      <td className="p-3 font-mono text-xs">{c.code}</td>
                      <td className="p-3">{c.classification}</td>
                      <td className="p-3 font-mono">{c.value ?? '–'}</td>
                      <td className="p-3 text-slate-300">{c.explanation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">Reproduzierbarkeit</h2>
              <button
                type="button"
                onClick={() => void verify()}
                className="rounded-lg border border-slate-700 px-3 py-2"
              >
                Reproduzierbarkeit prüfen
              </button>
            </div>
            <dl className="grid gap-3 md:grid-cols-2">
              <div className="rounded-lg border border-slate-800 p-3">
                <dt className="text-xs text-slate-500">Eingabe-Hash</dt>
                <dd className="mt-1 break-all font-mono text-xs">{runDetail.run.input_hash}</dd>
              </div>
              <div className="rounded-lg border border-slate-800 p-3">
                <dt className="text-xs text-slate-500">Analysezeitpunkt</dt>
                <dd className="mt-1">{fmt(runDetail.run.analysis_time)}</dd>
              </div>
            </dl>
            {verification ? (
              <div className="rounded-xl border border-slate-800 p-4">
                <strong>
                  {verification.verified ? 'Reproduktion bestätigt' : 'Abweichung festgestellt'}
                </strong>
                <div className="mt-2 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(verification)
                    .filter(([k]) => k !== 'verified')
                    .map(([k, v]) => (
                      <span key={k}>
                        {k.replaceAll('_', ' ')}: {v ? 'OK' : 'abweichend'}
                      </span>
                    ))}
                </div>
              </div>
            ) : null}
            <div className="overflow-hidden rounded-xl border border-slate-800">
              <table className="w-full text-left text-sm">
                <tbody>
                  {parameterEntries.map(([name, value]) => (
                    <tr key={name} className="border-t border-slate-800 first:border-t-0">
                      <th className="p-3 text-slate-400">{name}</th>
                      <td className="p-3 font-mono text-xs">{JSON.stringify(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-semibold">Lifecycle-Aktionen</h2>
            <label className="block text-sm">
              Begründung (optional)
              <input
                aria-label="Begründung"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
              />
            </label>
            <div className="flex flex-wrap gap-3">
              {retryable && !supersedeEvent ? (
                <button
                  type="button"
                  onClick={() => void retry()}
                  className="rounded-lg border border-slate-700 px-3 py-2"
                >
                  Retry aus Snapshot
                </button>
              ) : null}
              {replacementCandidates.length && !supersedeEvent ? (
                <>
                  <select
                    aria-label="Ersatzversion"
                    value={replacementVersion}
                    onChange={(e) => setReplacementVersion(e.target.value)}
                    className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
                  >
                    <option value="">Ersatzversion wählen</option>
                    {replacementCandidates.map((r) => (
                      <option key={r.version} value={r.version}>
                        Version {r.version} · {r.status}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    disabled={!replacementVersion}
                    onClick={() => void supersede()}
                    className="rounded-lg border border-slate-700 px-3 py-2 disabled:opacity-40"
                  >
                    Als ersetzt markieren
                  </button>
                </>
              ) : null}
            </div>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-semibold">Lifecycle-Events</h2>
            {events.length ? (
              <div className="space-y-2">
                {events.map((e) => (
                  <article key={e.id} className="rounded-lg border border-slate-800 p-3 text-sm">
                    <div className="flex flex-wrap justify-between gap-2">
                      <strong>{e.event_type}</strong>
                      <span className="text-slate-500">{fmt(e.occurred_at)}</span>
                    </div>
                    <p className="text-slate-300">
                      Version {e.version ?? '–'}: {e.from_status ?? '–'} → {e.to_status}
                      {e.replacement_version ? ` · Ersatzversion ${e.replacement_version}` : ''}
                    </p>
                    {e.reason ? <p className="mt-1 text-slate-400">Grund: {e.reason}</p> : null}
                  </article>
                ))}
              </div>
            ) : (
              <p className="text-slate-400">Keine Lifecycle-Events vorhanden.</p>
            )}
          </section>

          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">Verwendeter Marktdaten-Snapshot</h2>
              <button
                type="button"
                onClick={() => setShowSnapshot((v) => !v)}
                className="rounded-lg border border-slate-700 px-3 py-2 text-sm"
              >
                {showSnapshot
                  ? 'Snapshot ausblenden'
                  : `Snapshot anzeigen (${runDetail.run.observation_count})`}
              </button>
            </div>
            {showSnapshot ? (
              <>
                <div className="max-h-96 overflow-auto rounded-xl border border-slate-800">
                  <table className="w-full text-left text-xs">
                    <thead className="sticky top-0 bg-slate-900 text-slate-400">
                      <tr>
                        <th className="p-3">Datum</th>
                        <th className="p-3">Close</th>
                        <th className="p-3">Adjusted</th>
                        <th className="p-3">Quelle</th>
                        <th className="p-3">Qualität</th>
                      </tr>
                    </thead>
                    <tbody>
                      {snapshotPage?.items.map((row) => (
                        <tr key={row.trading_date} className="border-t border-slate-800">
                          <td className="p-3">{row.trading_date}</td>
                          <td className="p-3">{row.close}</td>
                          <td className="p-3">{row.adjusted_close ?? '–'}</td>
                          <td className="p-3">
                            {row.provider} · {row.provider_symbol}
                          </td>
                          <td className="p-3">{row.quality_status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>
                    {snapshotPage
                      ? `${snapshotPage.offset + 1}–${Math.min(snapshotPage.offset + snapshotPage.items.length, snapshotPage.total)} von ${snapshotPage.total}`
                      : 'Snapshot wird geladen …'}
                  </span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      disabled={snapshotOffset === 0}
                      onClick={() => setSnapshotOffset(Math.max(0, snapshotOffset - snapshotLimit))}
                    >
                      Zurück
                    </button>
                    <button
                      type="button"
                      disabled={
                        snapshotPage === null ||
                        snapshotOffset + snapshotLimit >= snapshotPage.total
                      }
                      onClick={() => setSnapshotOffset(snapshotOffset + snapshotLimit)}
                    >
                      Weiter
                    </button>
                  </div>
                </div>
              </>
            ) : null}
          </section>
        </div>
      ) : null}
    </section>
  );
}
