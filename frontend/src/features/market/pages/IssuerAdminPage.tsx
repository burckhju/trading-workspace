import { FormEvent, useEffect, useState } from 'react';

import { marketApiClient } from '../services/client';
import { MarketApiError } from '../services/http';
import type { IssuerAdminResponse } from '../types/api';

const EMPTY_FORM = { legal_name: '', display_name: '', country_code: '', lei: '' };

export function IssuerAdminPage() {
  const [issuers, setIssuers] = useState<IssuerAdminResponse[]>([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const response = await marketApiClient.listIssuersForAdmin();
    setIssuers(response.items);
  }

  useEffect(() => {
    void load().catch((value: unknown) => {
      setError(value instanceof Error ? value.message : 'Emittenten konnten nicht geladen werden.');
    });
  }, []);

  function startEdit(issuer: IssuerAdminResponse) {
    setEditingId(issuer.id);
    setForm({
      legal_name: issuer.legal_name,
      display_name: issuer.display_name,
      country_code: issuer.country_code ?? '',
      lei: issuer.lei ?? '',
    });
    setError(null);
  }

  function resetForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = {
        legal_name: form.legal_name,
        display_name: form.display_name,
        country_code: form.country_code || null,
        lei: form.lei || null,
      };
      if (editingId) {
        const current = issuers.find((issuer) => issuer.id === editingId);
        if (!current) throw new Error('Emittent wurde zwischenzeitlich entfernt.');
        await marketApiClient.updateIssuer(editingId, {
          expected_version: current.version,
          ...payload,
        });
      } else {
        await marketApiClient.createIssuer(payload);
      }
      await load();
      resetForm();
    } catch (value: unknown) {
      if (
        value instanceof MarketApiError &&
        value.response.code === 'ISSUER_CONCURRENT_MODIFICATION'
      ) {
        setError('Der Emittent wurde zwischenzeitlich geändert. Bitte aktuellen Stand neu laden.');
      } else if (
        value instanceof MarketApiError &&
        value.response.code === 'DUPLICATE_ISSUER_LEI'
      ) {
        setError('Diese LEI ist bereits einem anderen Emittenten zugeordnet.');
      } else {
        setError(
          value instanceof Error ? value.message : 'Emittent konnte nicht gespeichert werden.',
        );
      }
    } finally {
      setBusy(false);
    }
  }

  async function toggleStatus(issuer: IssuerAdminResponse) {
    setBusy(true);
    setError(null);
    try {
      if (issuer.is_active) {
        await marketApiClient.deactivateIssuer(issuer.id, issuer.version);
      } else {
        await marketApiClient.reactivateIssuer(issuer.id, issuer.version);
      }
      await load();
    } catch (value: unknown) {
      setError(value instanceof Error ? value.message : 'Status konnte nicht geändert werden.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="w-full space-y-8">
      <header>
        <p className="text-xs uppercase tracking-wide text-slate-500">Administration · FT-003</p>
        <h1 className="mt-1 text-2xl font-semibold">Emittenten</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Zentrale Referenzdatenpflege für Ausnahmefälle. Im normalen Trading-Workflow wird der
          Emittent aus Produkt- und Referenzdatenkontext übernommen; technische IDs oder Versionen
          müssen nicht eingegeben werden.
        </p>
      </header>

      {error && (
        <p className="rounded-lg border border-rose-800 p-3 text-sm text-rose-200">{error}</p>
      )}

      <form
        onSubmit={(event) => void submit(event)}
        className="rounded-xl border border-slate-800 p-5"
      >
        <h2 className="text-lg font-medium">
          {editingId ? 'Emittent bearbeiten' : 'Emittent anlegen'}
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          Juristischer Name und Anzeigename sind Stammdaten. Land und LEI bleiben optional.
        </p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="text-sm">
            Juristischer Name *
            <input
              aria-label="Juristischer Name"
              required
              maxLength={200}
              value={form.legal_name}
              onChange={(event) => setForm({ ...form, legal_name: event.target.value })}
              className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2"
            />
          </label>
          <label className="text-sm">
            Anzeigename *
            <input
              aria-label="Anzeigename"
              required
              maxLength={200}
              value={form.display_name}
              onChange={(event) => setForm({ ...form, display_name: event.target.value })}
              className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2"
            />
          </label>
          <label className="text-sm">
            Land
            <input
              aria-label="Land"
              maxLength={2}
              value={form.country_code}
              onChange={(event) =>
                setForm({ ...form, country_code: event.target.value.toUpperCase() })
              }
              className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2 font-mono"
            />
          </label>
          <label className="text-sm">
            LEI
            <input
              aria-label="LEI"
              maxLength={20}
              value={form.lei}
              onChange={(event) => setForm({ ...form, lei: event.target.value.toUpperCase() })}
              className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2 font-mono"
            />
            <span className="mt-1 block text-xs text-slate-500">
              Optionaler externer Identifier; nicht die interne Emittenten-ID.
            </span>
          </label>
        </div>
        <div className="mt-5 flex gap-3">
          <button
            disabled={busy}
            className="rounded-lg bg-sky-700 px-4 py-2 text-sm disabled:opacity-50"
          >
            {editingId ? 'Änderungen speichern' : 'Emittent anlegen'}
          </button>
          {editingId && (
            <button
              type="button"
              onClick={resetForm}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm"
            >
              Abbrechen
            </button>
          )}
        </div>
      </form>

      <section className="rounded-xl border border-slate-800">
        <div className="border-b border-slate-800 px-5 py-4">
          <h2 className="font-medium">Vorhandene Emittenten</h2>
          <p className="mt-1 text-xs text-slate-500">
            Deaktivieren entfernt keine historische Referenz; die interne ID bleibt stabil.
          </p>
        </div>
        <div className="divide-y divide-slate-800">
          {issuers.map((issuer) => (
            <div
              key={issuer.id}
              className="flex flex-col gap-3 px-5 py-4 md:flex-row md:items-center md:justify-between"
            >
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{issuer.display_name}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${issuer.is_active ? 'bg-emerald-950 text-emerald-300' : 'bg-slate-800 text-slate-400'}`}
                  >
                    {issuer.is_active ? 'Aktiv' : 'Inaktiv'}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-400">{issuer.legal_name}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {issuer.country_code ?? 'Land nicht hinterlegt'} ·{' '}
                  {issuer.lei ? `LEI ${issuer.lei}` : 'keine LEI hinterlegt'}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => startEdit(issuer)}
                  className="rounded border border-slate-700 px-3 py-1.5 text-sm"
                >
                  Bearbeiten
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void toggleStatus(issuer)}
                  className="rounded border border-slate-700 px-3 py-1.5 text-sm"
                >
                  {issuer.is_active ? 'Deaktivieren' : 'Reaktivieren'}
                </button>
              </div>
            </div>
          ))}
          {issuers.length === 0 && (
            <p className="px-5 py-6 text-sm text-slate-500">Keine Emittenten vorhanden.</p>
          )}
        </div>
      </section>
    </div>
  );
}
