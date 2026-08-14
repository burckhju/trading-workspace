import { FormEvent, useEffect, useState } from 'react';

import { MarketApiError } from '../services/http';
import { marketApiClient } from '../services/client';
import type { TradingVenueAdminResponse } from '../types/api';

const EMPTY_FORM = { mic: '', name: '', country_code: 'DE', timezone: 'Europe/Berlin' };

export function TradingVenueAdminPage() {
  const [venues, setVenues] = useState<TradingVenueAdminResponse[]>([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const response = await marketApiClient.listTradingVenuesForAdmin();
    setVenues(response.items);
  }

  useEffect(() => {
    void load().catch((value: unknown) => {
      setError(
        value instanceof Error ? value.message : 'Handelsplätze konnten nicht geladen werden.',
      );
    });
  }, []);

  function startEdit(venue: TradingVenueAdminResponse) {
    setEditingId(venue.id);
    setForm({
      mic: venue.mic,
      name: venue.name,
      country_code: venue.country_code,
      timezone: venue.timezone,
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
      if (editingId) {
        const current = venues.find((venue) => venue.id === editingId);
        if (!current) throw new Error('Handelsplatz wurde zwischenzeitlich entfernt.');
        await marketApiClient.updateTradingVenue(editingId, {
          expected_version: current.version,
          name: form.name,
          country_code: form.country_code,
          timezone: form.timezone,
        });
      } else {
        await marketApiClient.createTradingVenue(form);
      }
      await load();
      resetForm();
    } catch (value: unknown) {
      if (
        value instanceof MarketApiError &&
        value.response.code === 'TRADING_VENUE_CONCURRENT_MODIFICATION'
      ) {
        setError(
          'Der Handelsplatz wurde zwischenzeitlich geändert. Bitte aktuellen Stand neu laden.',
        );
      } else {
        setError(
          value instanceof Error ? value.message : 'Handelsplatz konnte nicht gespeichert werden.',
        );
      }
    } finally {
      setBusy(false);
    }
  }

  async function toggleStatus(venue: TradingVenueAdminResponse) {
    setBusy(true);
    setError(null);
    try {
      if (venue.is_active) {
        await marketApiClient.deactivateTradingVenue(venue.id, venue.version);
      } else {
        await marketApiClient.reactivateTradingVenue(venue.id, venue.version);
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
        <p className="text-xs uppercase tracking-wide text-slate-500">Administration · FT-002</p>
        <h1 className="mt-1 text-2xl font-semibold">Handelsplätze</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Zentrale Stammdatenpflege für Ausnahmefälle. Normale Trading-Workflows übernehmen
          Handelsplätze automatisch aus Listing- und Produktkontext, sofern die Zuordnung eindeutig
          ist.
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
          {editingId ? 'Handelsplatz bearbeiten' : 'Handelsplatz anlegen'}
        </h2>
        <div className="mt-4 grid gap-4 md:grid-cols-4">
          <label className="text-sm">
            MIC
            <input
              aria-label="MIC"
              required
              disabled={editingId !== null}
              maxLength={4}
              value={form.mic}
              onChange={(event) => setForm({ ...form, mic: event.target.value.toUpperCase() })}
              className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2 disabled:text-slate-500"
            />
          </label>
          <label className="text-sm md:col-span-2">
            Name
            <input
              aria-label="Name"
              required
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2"
            />
          </label>
          <label className="text-sm">
            Land
            <input
              aria-label="Land"
              required
              maxLength={2}
              value={form.country_code}
              onChange={(event) =>
                setForm({ ...form, country_code: event.target.value.toUpperCase() })
              }
              className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2"
            />
          </label>
          <label className="text-sm md:col-span-2">
            Zeitzone
            <input
              aria-label="Zeitzone"
              required
              value={form.timezone}
              onChange={(event) => setForm({ ...form, timezone: event.target.value })}
              className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2"
            />
          </label>
        </div>
        <div className="mt-5 flex gap-3">
          <button
            disabled={busy}
            className="rounded-lg bg-sky-700 px-4 py-2 text-sm disabled:opacity-50"
          >
            {editingId ? 'Änderungen speichern' : 'Handelsplatz anlegen'}
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
          <h2 className="font-medium">Vorhandene Handelsplätze</h2>
          <p className="mt-1 text-xs text-slate-500">
            Deaktivieren entfernt keine historischen Listing-Referenzen.
          </p>
        </div>
        <div className="divide-y divide-slate-800">
          {venues.map((venue) => (
            <div
              key={venue.id}
              className="flex flex-col gap-3 px-5 py-4 md:flex-row md:items-center md:justify-between"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm">{venue.mic}</span>
                  <span className="font-medium">{venue.name}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${venue.is_active ? 'bg-emerald-950 text-emerald-300' : 'bg-slate-800 text-slate-400'}`}
                  >
                    {venue.is_active ? 'Aktiv' : 'Inaktiv'}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {venue.country_code} · {venue.timezone}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => startEdit(venue)}
                  className="rounded border border-slate-700 px-3 py-1.5 text-sm"
                >
                  Bearbeiten
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void toggleStatus(venue)}
                  className="rounded border border-slate-700 px-3 py-1.5 text-sm"
                >
                  {venue.is_active ? 'Deaktivieren' : 'Reaktivieren'}
                </button>
              </div>
            </div>
          ))}
          {venues.length === 0 && (
            <p className="px-5 py-6 text-sm text-slate-500">Keine Handelsplätze vorhanden.</p>
          )}
        </div>
      </section>
    </div>
  );
}
