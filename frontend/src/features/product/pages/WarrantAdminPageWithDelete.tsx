import { useState } from 'react';

import { warrantApiClient } from '../services/client';
import type { WarrantResponse } from '../types/api';
import { WarrantAdminPage as WarrantAdminCorePage } from './WarrantAdminPage';

const LOAD_ERROR = 'Optionsscheine konnten nicht geladen werden.';
const DELETE_ERROR =
  'Optionsschein konnte nicht gelöscht werden. Historische Verwendungen bleiben geschützt.';

export function WarrantAdminPageWithDelete() {
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [warrants, setWarrants] = useState<WarrantResponse[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [adminRevision, setAdminRevision] = useState(0);

  async function openDeletePanel() {
    setDeleteOpen(true);
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await warrantApiClient.list();
      setWarrants(response);
      setSelectedId(response[0]?.id ?? '');
    } catch (value: unknown) {
      setError(value instanceof Error ? value.message : LOAD_ERROR);
    } finally {
      setBusy(false);
    }
  }

  async function deleteSelected() {
    const selected = warrants.find((item) => item.id === selectedId);
    if (!selected) return;

    const confirmed = window.confirm(
      `Optionsschein „${selected.display_name}“ endgültig löschen? ` +
        'Das ist nur möglich, solange keine historische oder operative Verwendung existiert.',
    );
    if (!confirmed) return;

    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await warrantApiClient.delete(selected.id, selected.version);
      const remaining = warrants.filter((item) => item.id !== selected.id);
      setWarrants(remaining);
      setSelectedId(remaining[0]?.id ?? '');
      setAdminRevision((current) => current + 1);
      setMessage(`Optionsschein „${selected.display_name}“ wurde gelöscht.`);
    } catch (value: unknown) {
      setError(value instanceof Error ? value.message : DELETE_ERROR);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <WarrantAdminCorePage key={adminRevision} />

      <section
        className="rounded-xl border border-slate-800 p-5"
        aria-labelledby="warrant-delete-heading"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 id="warrant-delete-heading" className="text-lg font-medium">
              Optionsschein löschen
            </h2>
            <p className="mt-1 max-w-3xl text-sm text-slate-400">
              Nur versehentlich angelegte und noch nicht historisch oder operativ verwendete
              Optionsscheine können physisch gelöscht werden. Verwendete Produkte bleiben geschützt.
            </p>
          </div>
          {!deleteOpen && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void openDeletePanel()}
              className="rounded border border-rose-800 px-3 py-1.5 text-sm text-rose-200 disabled:opacity-50"
            >
              Löschverwaltung öffnen
            </button>
          )}
        </div>

        {deleteOpen && (
          <div className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
            <label className="text-sm">
              Optionsschein
              <select
                value={selectedId}
                onChange={(event) => setSelectedId(event.target.value)}
                disabled={busy || warrants.length === 0}
                className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2"
              >
                {warrants.length === 0 && (
                  <option value="">Keine Optionsscheine vorhanden</option>
                )}
                {warrants.map((warrant) => (
                  <option key={warrant.id} value={warrant.id}>
                    {warrant.display_name} · {warrant.isin ?? warrant.wkn ?? 'ohne Kennnummer'}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              disabled={busy || !selectedId}
              onClick={() => void deleteSelected()}
              className="rounded bg-rose-900 px-4 py-2 text-sm text-rose-100 disabled:opacity-50"
            >
              Endgültig löschen
            </button>
          </div>
        )}

        {error && (
          <p
            role="alert"
            className="mt-3 rounded border border-rose-800 p-3 text-sm text-rose-200"
          >
            {error}
          </p>
        )}
        {message && (
          <p
            role="status"
            className="mt-3 rounded border border-emerald-800 p-3 text-sm text-emerald-200"
          >
            {message}
          </p>
        )}
      </section>
    </div>
  );
}
