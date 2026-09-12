import { useEffect, useState } from 'react';

import {
  currencyAdminClient,
  type AdminCurrency,
  type CatalogPreview,
  type CurrencyAdminResponse,
  type CurrencyAudit,
} from '../services/currencies';

const button = 'rounded-lg border border-slate-600 px-3 py-2 text-sm disabled:opacity-50';
const changeLabel = {
  NEW: 'Neu im Katalog',
  UNCHANGED: 'Unverändert',
  CHANGED: 'Referenzangaben geändert',
  NOT_IN_NEW_CATALOG: 'Nicht im neuen Katalog',
};
function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Währungsverwaltung konnte nicht geladen werden.';
}

export function CurrencyAdminPage() {
  const [data, setData] = useState<CurrencyAdminResponse | null>(null);
  const [history, setHistory] = useState<CurrencyAudit[]>([]);
  const [query, setQuery] = useState('');
  const [activeOnly, setActiveOnly] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [file, setFile] = useState<{ name: string; text: string } | null>(null);
  const [preview, setPreview] = useState<(CatalogPreview & { input: string | null }) | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [pending, setPending] = useState<AdminCurrency | null>(null);

  async function load(signal?: AbortSignal) {
    const [response, audit] = await Promise.all([
      currencyAdminClient.list(signal),
      currencyAdminClient.history(signal),
    ]);
    if (!signal?.aborted) {
      setData(response);
      setHistory(audit.items);
    }
  }
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal).catch((e: unknown) => {
      if (!controller.signal.aborted) setError(errorMessage(e));
    });
    return () => controller.abort();
  }, []);

  async function reload() {
    setBusy(true);
    setError(null);
    setPending(null);
    setPreview(null);
    setReviewed(false);
    try {
      await load();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  async function selectFile(selected: File | undefined) {
    setPreview(null);
    setReviewed(false);
    setFile(null);
    setError(null);
    if (!selected) return;
    setBusy(true);
    try {
      if (selected.size > 256_000) throw new Error('Katalogdatei ist zu groß (maximal 256 kB).');
      const text = await selected.text();
      setFile({ name: selected.name, text });
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  async function showPreview(input: string | null) {
    setBusy(true);
    setError(null);
    setMessage(null);
    setPreview(null);
    setReviewed(false);
    try {
      setPreview({ ...(await currencyAdminClient.preview(input)), input });
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  async function applyCatalog() {
    if (!preview || !reviewed) return;
    setBusy(true);
    setError(null);
    try {
      const result = await currencyAdminClient.import(preview.input, preview.preview_token);
      setPreview(null);
      setReviewed(false);
      setPending(null);
      setMessage(
        result.applied
          ? 'Katalog übernommen. Keine Währung wurde automatisch aktiviert.'
          : 'Dieser Katalog ist bereits übernommen.',
      );
      await load();
    } catch (e) {
      setError(errorMessage(e));
      setPreview(null);
      setReviewed(false);
    } finally {
      setBusy(false);
    }
  }
  async function confirmStatus() {
    if (!pending) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await currencyAdminClient.changeStatus(
        pending.code,
        !pending.is_active,
        pending.state_token,
      );
      setMessage(
        `${result.code} wurde ${result.is_active ? 'aktiviert' : 'deaktiviert'}. Bestehende Produktbedingungen bleiben unverändert.`,
      );
      setPending(null);
      await load();
    } catch (e) {
      setError(errorMessage(e));
      setPending(null);
    } finally {
      setBusy(false);
    }
  }

  const rows = (data?.items ?? []).filter(
    (row) =>
      (!activeOnly || row.is_active) &&
      `${row.code} ${row.name} ${row.catalog_name ?? ''}`
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
  );
  return (
    <div className="w-full space-y-6">
      <header>
        <p className="text-xs uppercase text-slate-400">Administration</p>
        <h1 className="mt-1 text-2xl font-semibold">Währungen</h1>
        <p className="mt-2 text-sm text-slate-400">
          Katalogwissen und lokale Freigabe sind getrennt. Aktivierung bietet eine Währung für neue
          Eingaben an; sie ändert keine Strikes, Kurse oder historischen Daten und richtet keine
          Wechselkursversorgung ein.
        </p>
      </header>
      {error && (
        <p role="alert" className="rounded border border-rose-700 p-3">
          {error}
        </p>
      )}
      {message && (
        <p role="status" className="rounded border border-slate-600 p-3">
          {message}
        </p>
      )}
      {!data && !error && <p role="status">Währungsstammdaten werden geladen.</p>}
      <button className={button} disabled={busy} onClick={() => void reload()}>
        Stand neu laden
      </button>

      <section
        aria-label="Referenzkatalog"
        className="space-y-3 rounded-xl border border-slate-700 p-5"
      >
        <h2 className="text-lg font-semibold">Referenzkatalog</h2>
        <p>
          {data?.catalog
            ? `Übernommen: ${data.catalog.version} · Quellenstand: ${data.catalog.source_published_on}`
            : 'Noch kein Katalog übernommen. Bestehende Währungsfreigaben bleiben erhalten.'}
        </p>
        {data?.catalog && <p className="text-sm text-slate-400">{data.catalog.scope}</p>}
        <p className="text-sm text-slate-400">
          Keine automatische Online-Aktualisierung. Neue Version zuerst prüfen und übernehmen,
          danach gewünschte Währungen einzeln aktivieren. Lokale Bezeichnungen und Untereinheiten
          werden beim Import nicht überschrieben.
        </p>
        <button className={button} disabled={busy} onClick={() => void showPreview(null)}>
          Mitgelieferten Katalog prüfen
        </button>
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-sm">
            Geprüfte Katalogdatei (JSON)
            <input
              type="file"
              accept=".json,application/json"
              disabled={busy}
              className="mt-1 block"
              onChange={(e) => void selectFile(e.target.files?.[0])}
            />
          </label>
          <button
            className={button}
            disabled={busy || !file}
            onClick={() => void showPreview(file?.text ?? null)}
          >
            Datei prüfen
          </button>
          {file && <span className="text-sm">{file.name}</span>}
        </div>
        {preview && (
          <div className="space-y-3 border-t border-slate-700 pt-4">
            <h3 className="font-semibold">Änderungsvorschau: {preview.catalog.version}</h3>
            <p className="text-sm">
              Quelle:{' '}
              <a
                className="underline"
                href={preview.catalog.source_url}
                target="_blank"
                rel="noreferrer"
              >
                SIX List One
              </a>{' '}
              · Stand: {preview.catalog.source_published_on}
            </p>
            <p className="break-all font-mono text-xs">Katalog-SHA-256: {preview.checksum}</p>
            <p className="break-all font-mono text-xs">
              Quelldatei-SHA-256: {preview.catalog.source_sha256}
            </p>
            <p className="text-sm">{preview.catalog.scope}</p>
            <div className="max-h-64 overflow-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Änderung</th>
                    <th>Bisher im Katalog</th>
                    <th>Neuer Katalog</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.changes.map((row) => (
                    <tr key={row.code} className="border-t border-slate-800">
                      <td className="py-2">{row.code}</td>
                      <td>{changeLabel[row.change]}</td>
                      <td>
                        {row.before
                          ? `${row.before.name} · Untereinheit ${row.before.minor_unit}`
                          : '—'}
                      </td>
                      <td>
                        {row.after
                          ? `${row.after.name} · Untereinheit ${row.after.minor_unit}`
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-sm">
              Auch entfallende Katalogeinträge löschen oder deaktivieren keine lokalen Währungen.
              Abweichende Untereinheiten werden nicht automatisch korrigiert.
            </p>
            {preview.already_current ? (
              <p>Dieser Katalog ist bereits übernommen.</p>
            ) : (
              <>
                <label className="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={reviewed}
                    onChange={(e) => setReviewed(e.target.checked)}
                    disabled={busy}
                  />
                  Ich habe Quelle und Änderungen geprüft. Der Import verändert nur den
                  Referenzkatalog.
                </label>
                <button
                  className={button}
                  disabled={busy || !reviewed}
                  onClick={() => void applyCatalog()}
                >
                  Katalog übernehmen
                </button>
              </>
            )}
          </div>
        )}
      </section>

      <section aria-label="Lokale Währungsfreigaben" className="space-y-3">
        <h2 className="text-lg font-semibold">Lokale Währungsfreigaben</h2>
        <div className="flex flex-wrap items-center gap-4">
          <label>
            Währung suchen
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="ml-2 rounded border border-slate-600 bg-slate-950 p-2"
            />
          </label>
          <label className="flex gap-2">
            <input
              type="checkbox"
              checked={activeOnly}
              onChange={(e) => setActiveOnly(e.target.checked)}
            />
            Nur aktive Währungen
          </label>
        </div>
        {data && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr>
                  <th>Währung</th>
                  <th>Untereinheit</th>
                  <th>Lokale Freigabe</th>
                  <th>Katalogabgleich</th>
                  <th>Aktion</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.code} className="border-t border-slate-800">
                    <td className="py-3">
                      {row.code} – {row.name}
                    </td>
                    <td>{row.minor_unit}</td>
                    <td>
                      {row.is_active
                        ? 'Aktiv'
                        : row.local_exists
                          ? 'Deaktiviert'
                          : 'Noch nicht freigeschaltet'}
                    </td>
                    <td>
                      {row.minor_unit_conflict
                        ? `Konflikt: Katalog nennt Untereinheit ${row.catalog_minor_unit}`
                        : row.catalog_available
                          ? 'Im Katalog'
                          : 'Nicht im aktuellen Katalog'}
                      {row.catalog_name && row.name !== row.catalog_name && (
                        <p>Katalogname: {row.catalog_name}; lokale Bezeichnung bleibt erhalten.</p>
                      )}
                    </td>
                    <td>
                      <button
                        className={button}
                        disabled={busy || (!row.is_active && !row.can_activate)}
                        onClick={() => {
                          setPending(row);
                          setMessage(null);
                        }}
                        aria-label={`${row.code} ${row.is_active ? 'deaktivieren' : 'aktivieren'}`}
                      >
                        {row.is_active ? 'Deaktivieren' : 'Aktivieren'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length === 0 && <p className="py-3">Keine passenden Währungen.</p>}
          </div>
        )}
        {pending && (
          <section
            aria-label="Währungsfreigabe bestätigen"
            className="space-y-3 rounded border border-amber-700 p-4"
          >
            <h3>
              {pending.code} {pending.is_active ? 'deaktivieren' : 'aktivieren'}?
            </h3>
            <p className="text-sm">
              {pending.is_active
                ? 'Für neue Eingaben nicht mehr anbieten. Historische Produktbedingungen und gespeicherte Beträge bleiben erhalten.'
                : 'Diese Währung aus dem übernommenen Katalog für neue Eingaben freischalten. Bestehende lokale Angaben werden nicht überschrieben.'}
            </p>
            <button className={button} disabled={busy} onClick={() => void confirmStatus()}>
              Freigabe bestätigen
            </button>
            <button className={`${button} ml-2`} disabled={busy} onClick={() => setPending(null)}>
              Abbrechen
            </button>
          </section>
        )}
      </section>
      <details className="rounded border border-slate-700 p-4">
        <summary>Änderungsprotokoll (letzte 100 Vorgänge)</summary>
        {history.map((item) => (
          <details className="mt-3" key={item.id}>
            <summary>
              {item.occurred_at} · {item.actor} · {item.action}
            </summary>
            <pre className="overflow-auto text-xs">{JSON.stringify(item.changes, null, 2)}</pre>
          </details>
        ))}
        {history.length === 0 && (
          <p className="mt-2">Noch keine protokollierten Währungsänderungen.</p>
        )}
      </details>
    </div>
  );
}
