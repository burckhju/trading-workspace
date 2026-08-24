import { ChangeEvent, useEffect, useMemo, useState } from 'react';

import { marketApiClient } from '../../market/services/client';
import type { UnderlyingSummaryResponse } from '../../market/types/api';
import { warrantApiClient } from '../../product/services/client';
import type { WarrantResponse } from '../../product/types/api';
import {
  bulkImportClient,
  type BulkImportJob,
  type BulkImportReviewRow,
} from '../services/bulkImportClient';

type ReviewSelection = { underlyingId: string; productId: string };

function payloadText(row: BulkImportReviewRow, key: string): string {
  const value = row.payload[key];
  if (value === undefined || value === null) return '–';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return '–';
}

export function BulkImportPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [job, setJob] = useState<BulkImportJob | null>(null);
  const [reviewRows, setReviewRows] = useState<BulkImportReviewRow[]>([]);
  const [underlyings, setUnderlyings] = useState<UnderlyingSummaryResponse[]>([]);
  const [warrants, setWarrants] = useState<WarrantResponse[]>([]);
  const [selections, setSelections] = useState<Record<string, ReviewSelection>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmedCount, setConfirmedCount] = useState<number | null>(null);

  useEffect(() => {
    void Promise.all([
      marketApiClient.searchUnderlyings({ lifecycleStatus: 'ACTIVE', limit: 100 }),
      warrantApiClient.list(),
    ])
      .then(([underlyingResponse, warrantResponse]) => {
        setUnderlyings(underlyingResponse.items);
        setWarrants(warrantResponse.filter((item) => item.lifecycle_status === 'ACTIVE'));
      })
      .catch((value: unknown) =>
        setError(value instanceof Error ? value.message : 'Stammdaten konnten nicht geladen werden.'),
      );
  }, []);

  const readyForConfirmation = useMemo(
    () =>
      job !== null &&
      job.status !== 'COMPLETED' &&
      reviewRows.length === 0 &&
      !job.files.some((item) => item.status === 'FAILED'),
    [job, reviewRows],
  );

  function onFilesChanged(event: ChangeEvent<HTMLInputElement>) {
    setFiles(Array.from(event.target.files ?? []));
    setConfirmedCount(null);
  }

  async function refresh(jobId: string) {
    const [jobResponse, reviewResponse] = await Promise.all([
      bulkImportClient.getJob(jobId),
      bulkImportClient.reviewRows(jobId),
    ]);
    setJob(jobResponse);
    setReviewRows(reviewResponse);
  }

  async function upload() {
    if (files.length === 0) return;
    setBusy(true);
    setError(null);
    setConfirmedCount(null);
    try {
      const response = await bulkImportClient.upload(files);
      setJob(response);
      setReviewRows(await bulkImportClient.reviewRows(response.job_id));
    } catch (value: unknown) {
      setError(value instanceof Error ? value.message : 'PDF-Import ist fehlgeschlagen.');
    } finally {
      setBusy(false);
    }
  }

  function selectionFor(row: BulkImportReviewRow): ReviewSelection {
    return (
      selections[row.id] ?? {
        underlyingId: row.underlying_id ?? '',
        productId: row.product_id ?? '',
      }
    );
  }

  async function resolve(row: BulkImportReviewRow) {
    if (!job) return;
    const selection = selectionFor(row);
    if (!selection.underlyingId || !selection.productId) {
      setError('Für die Zuordnung müssen Basiswert und Optionsschein ausgewählt werden.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await bulkImportClient.resolve(job.job_id, row.id, selection.underlyingId, selection.productId);
      await refresh(job.job_id);
    } catch (value: unknown) {
      setError(value instanceof Error ? value.message : 'Review-Fall konnte nicht zugeordnet werden.');
    } finally {
      setBusy(false);
    }
  }

  async function discard(row: BulkImportReviewRow) {
    if (!job) return;
    setBusy(true);
    setError(null);
    try {
      await bulkImportClient.discard(job.job_id, row.id);
      await refresh(job.job_id);
    } catch (value: unknown) {
      setError(value instanceof Error ? value.message : 'Review-Fall konnte nicht verworfen werden.');
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!job) return;
    setBusy(true);
    setError(null);
    try {
      const response = await bulkImportClient.confirm(job.job_id);
      setConfirmedCount(response.accepted_observation_version_ids.length);
      await refresh(job.job_id);
    } catch (value: unknown) {
      setError(value instanceof Error ? value.message : 'Import konnte nicht bestätigt werden.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="w-full space-y-8">
      <header>
        <p className="text-xs uppercase tracking-wide text-slate-500">Learning · Historical Evidence</p>
        <h1 className="mt-1 text-2xl font-semibold">Hebeltrader PDF-Import</h1>
        <p className="mt-2 max-w-4xl text-sm text-slate-400">
          Viele historische Ausgaben in einem Job hochladen, automatisch per WKN zuordnen und nur
          die Ausnahmen manuell prüfen. Erst die Bestätigung übernimmt valide Zeilen als externe
          Beobachtungen; es werden keine Trades erzeugt.
        </p>
      </header>

      {error && (
        <p className="rounded-lg border border-rose-800 p-3 text-sm text-rose-200">{error}</p>
      )}
      {confirmedCount !== null && (
        <p className="rounded-lg border border-emerald-800 p-3 text-sm text-emerald-200">
          Import abgeschlossen: {confirmedCount} Beobachtungen wurden übernommen.
        </p>
      )}

      <section className="rounded-xl border border-slate-800 p-5">
        <h2 className="text-lg font-medium">PDFs auswählen</h2>
        <p className="mt-1 text-sm text-slate-400">
          Mehrfachauswahl ist vorgesehen; identische Dateien werden über ihren Inhaltshash erkannt.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-4">
          <input
            aria-label="Hebeltrader PDFs"
            type="file"
            accept="application/pdf,.pdf"
            multiple
            onChange={onFilesChanged}
            className="text-sm text-slate-300"
          />
          <button
            type="button"
            disabled={busy || files.length === 0}
            onClick={() => void upload()}
            className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
          >
            {busy ? 'Verarbeite …' : `${files.length || 0} PDF${files.length === 1 ? '' : 's'} importieren`}
          </button>
        </div>
      </section>

      {job && (
        <section className="rounded-xl border border-slate-800 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-medium">Import-Job</h2>
              <p className="mt-1 text-xs text-slate-500">{job.job_id}</p>
            </div>
            <span className="rounded-full border border-slate-700 px-3 py-1 text-xs font-medium">
              {job.status}
            </span>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(job.files_by_status).map(([status, count]) => (
              <div key={status} className="rounded-lg border border-slate-800 p-3">
                <div className="text-xl font-semibold">{count}</div>
                <div className="text-xs text-slate-500">{status}</div>
              </div>
            ))}
          </div>
          <div className="mt-5 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-500">
                <tr>
                  <th className="py-2 pr-4">Datei</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2">Hinweis</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {job.files.map((item) => (
                  <tr key={item.id}>
                    <td className="py-3 pr-4">{item.filename}</td>
                    <td className="py-3 pr-4">{item.status}</td>
                    <td className="py-3 text-slate-400">
                      {item.failure_detail ??
                        (item.duplicate_of_file_id ? 'Duplikat – nicht erneut übernommen' : '–')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {reviewRows.length > 0 && (
        <section className="space-y-4">
          <div>
            <h2 className="text-lg font-medium">Ausnahmen prüfen</h2>
            <p className="mt-1 text-sm text-slate-400">
              Nur uneindeutige oder widersprüchliche Zuordnungen landen hier.
            </p>
          </div>
          {reviewRows.map((row) => {
            const selection = selectionFor(row);
            const compatibleWarrants = warrants.filter(
              (item) => !selection.underlyingId || item.underlying_id === selection.underlyingId,
            );
            return (
              <article key={row.id} className="rounded-xl border border-amber-900/70 p-5">
                <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-amber-400">
                      {row.validation_status}
                    </div>
                    <h3 className="mt-1 font-medium">{payloadText(row, 'recommendation_title')}</h3>
                    <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
                      <dt className="text-slate-500">Basiswert</dt>
                      <dd>{payloadText(row, 'underlying_name')}</dd>
                      <dt className="text-slate-500">Basiswert-WKN</dt>
                      <dd>{payloadText(row, 'underlying_wkn')}</dd>
                      <dt className="text-slate-500">Produkt-WKN</dt>
                      <dd>{payloadText(row, 'derivative_wkn')}</dd>
                      <dt className="text-slate-500">Ausgabe</dt>
                      <dd>
                        #{payloadText(row, 'issue_number')} · {payloadText(row, 'issue_date')}
                      </dd>
                    </dl>
                  </div>
                  <div className="grid gap-3">
                    <label className="text-sm">
                      Basiswert
                      <select
                        value={selection.underlyingId}
                        onChange={(event) =>
                          setSelections((current) => ({
                            ...current,
                            [row.id]: { underlyingId: event.target.value, productId: '' },
                          }))
                        }
                        className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2"
                      >
                        <option value="">Bitte auswählen</option>
                        {underlyings.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.name} · {item.wkn ?? 'ohne WKN'}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="text-sm">
                      Optionsschein
                      <select
                        value={selection.productId}
                        onChange={(event) =>
                          setSelections((current) => ({
                            ...current,
                            [row.id]: {
                              underlyingId: selection.underlyingId,
                              productId: event.target.value,
                            },
                          }))
                        }
                        className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2"
                      >
                        <option value="">Bitte auswählen</option>
                        {compatibleWarrants.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.display_name} · {item.wkn ?? 'ohne WKN'}
                          </option>
                        ))}
                      </select>
                    </label>
                    <div className="flex gap-3 pt-1">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void resolve(row)}
                        className="rounded-lg bg-amber-200 px-3 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
                      >
                        Zuordnen
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void discard(row)}
                        className="rounded-lg border border-slate-700 px-3 py-2 text-sm disabled:opacity-50"
                      >
                        Verwerfen
                      </button>
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </section>
      )}

      {job && (
        <section className="flex items-center justify-between gap-4 rounded-xl border border-slate-800 p-5">
          <div>
            <h2 className="font-medium">Fachliche Übernahme</h2>
            <p className="mt-1 text-sm text-slate-400">
              Bestätigen ist erst möglich, wenn keine offenen Review-Fälle oder fehlgeschlagenen
              Dateien mehr vorhanden sind.
            </p>
          </div>
          <button
            type="button"
            disabled={busy || !readyForConfirmation}
            onClick={() => void confirm()}
            className="shrink-0 rounded-lg bg-emerald-200 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-40"
          >
            Import bestätigen
          </button>
        </section>
      )}
    </div>
  );
}
