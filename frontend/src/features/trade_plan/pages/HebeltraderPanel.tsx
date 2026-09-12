import { useState } from 'react';
import type { FormEvent } from 'react';

import { tradePlanApiClient } from '../services/client';
import { previewHebeltrader } from '../services/hebeltraderClient';
import type { HebeltraderPreview } from '../services/hebeltraderClient';

interface Props {
  underlyingId: string;
  onCreated: (tradePlanId: string) => void;
}

const initialForm = {
  bid: '',
  ask: '',
  gd200: '',
  gd50: '',
  band: '',
  buffer: '0',
  tick: '0.01',
  currency: 'EUR',
  observedAt: '',
  analysisDate: '',
  source: '',
};

function decimal(value: string): string {
  const normalized = value.trim().replace(',', '.');
  if (!/^\d+(\.\d+)?$/.test(normalized)) {
    throw new Error('Dezimalzahlen ohne Tausendertrennzeichen eingeben.');
  }
  return normalized;
}

export function HebeltraderPanel({ underlyingId, onCreated }: Props) {
  const [form, setForm] = useState(initialForm);
  const [support, setSupport] = useState<'GD200' | 'GD50'>('GD200');
  const [fundamentalOk, setFundamentalOk] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const [preview, setPreview] = useState<HebeltraderPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function invalidate() {
    setPreview(null);
    setReviewed(false);
    setError(null);
  }

  function change(key: keyof typeof initialForm, value: string) {
    setForm((previous) => ({ ...previous, [key]: value }));
    invalidate();
  }

  async function calculate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    invalidate();
    setBusy(true);
    try {
      const result = await previewHebeltrader({
        as_of: new Date().toISOString(),
        analysis_date: form.analysisDate,
        source_ref: form.source,
        quote: {
          bid: decimal(form.bid),
          ask: decimal(form.ask),
          observed_at: form.observedAt,
          currency: form.currency.toUpperCase(),
          source: form.source,
        },
        gd200: decimal(form.gd200),
        ...(form.gd50.trim() ? { gd50: decimal(form.gd50) } : {}),
        band_width: decimal(form.band),
        support_source: support,
        buffer_fraction: decimal(form.buffer),
        tick: decimal(form.tick),
        fundamental_ok: fundamentalOk,
      });
      setPreview(result);
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : 'Vorschau konnte nicht berechnet werden.');
    } finally {
      setBusy(false);
    }
  }

  async function createDraft() {
    if (!preview?.trade_plan_content || !preview.assessment.eligible || !reviewed || busy) return;
    setBusy(true);
    setError(null);
    try {
      const result = await tradePlanApiClient.create({
        ...preview.trade_plan_content,
        origin_type: 'MANUAL',
        underlying_id: underlyingId,
      });
      onCreated(result.plan.id);
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : 'Entwurf konnte nicht gespeichert werden.');
    } finally {
      setBusy(false);
    }
  }

  const numericFields: [keyof typeof initialForm, string][] = [
    ['bid', 'Geldkurs Aktie'],
    ['ask', 'Briefkurs Aktie'],
    ['gd200', 'GD200'],
    ['gd50', 'GD50 (optional)'],
    ['band', 'Explizite Bandbreite B'],
    ['buffer', 'Stopp-Puffer als Anteil (0,01 = 1 %)'],
    ['tick', 'Tickgröße'],
  ];

  return (
    <details className="rounded-xl border border-slate-800 p-5">
      <summary className="cursor-pointer text-lg font-semibold">Hebeltrader-Regelvorschau</summary>
      <p className="mt-3 text-sm text-slate-400">
        Manuell belegter Snapshot, kein Livefeed. Aktienmarken in Hauptwährungseinheiten eingeben (GBP
        statt GBp). B ist eine offengelegte Annahme; die Original-Volatilitätsformel ist unbekannt.
        Diese Vorschau erstellt keine Order und ändert keine bestehende Position.
      </p>
      <form onSubmit={(event) => void calculate(event)} className="mt-4">
        <fieldset disabled={busy} className="grid gap-3 md:grid-cols-2">
          {numericFields.map(([key, label]) => (
            <label key={key} className="text-sm">
              {label}
              <input
                aria-label={label}
                inputMode="decimal"
                required={key !== 'gd50' || support === 'GD50'}
                value={form[key]}
                onChange={(event) => change(key, event.target.value)}
                className="mt-1 block w-full rounded border border-slate-700 bg-slate-950 p-2"
              />
            </label>
          ))}
          <label className="text-sm">
            Unterstützung
            <select
              aria-label="Unterstützung"
              value={support}
              onChange={(event) => {
                setSupport(event.target.value as 'GD200' | 'GD50');
                invalidate();
              }}
              className="mt-1 block w-full rounded border border-slate-700 bg-slate-950 p-2"
            >
              <option value="GD200">GD200</option>
              <option value="GD50">GD50</option>
            </select>
          </label>
          {(
            [
              ['currency', 'Währung (ISO, z. B. EUR)'],
              ['observedAt', 'Kurszeit mit Zeitzone (ISO 8601)'],
              ['analysisDate', 'Analysedatum (YYYY-MM-DD)'],
              ['source', 'Quellennachweis und Begründung für B'],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="text-sm">
              {label}
              <input
                aria-label={label}
                required
                value={form[key]}
                onChange={(event) => change(key, event.target.value)}
                className="mt-1 block w-full rounded border border-slate-700 bg-slate-950 p-2"
              />
            </label>
          ))}
          <label className="text-sm md:col-span-2">
            <input
              type="checkbox"
              checked={fundamentalOk}
              onChange={(event) => {
                setFundamentalOk(event.target.checked);
                invalidate();
              }}
            />{' '}
            Fundamentale These separat geprüft
          </label>
          <button type="submit" className="rounded border border-sky-700 px-4 py-2">
            Regelvorschau berechnen
          </button>
        </fieldset>
      </form>
      {error && (
        <p role="alert" className="mt-3 text-sm text-red-400">
          {error}
        </p>
      )}
      {preview && (
        <section aria-label="Hebeltrader-Ergebnis" className="mt-4 space-y-3 text-sm">
          <p>
            Stopp: {preview.levels.stop} · Ziel 1: {preview.levels.target1} · Ziel 2:{' '}
            {preview.levels.target2} · CRV (50/50, vor Kosten):{' '}
            {preview.assessment.reward_risk === null
              ? 'nicht berechenbar'
              : Number(preview.assessment.reward_risk).toFixed(2)}
          </p>
          <p className="text-slate-400">
            T1: Hälfte verkaufen, Reststopp erst nach bestätigtem Verkauf auf Einstand. Nach weiteren
            20 Handelssitzungen: max(bisheriger Stopp, 80 % von T1). Kein Stopp wird abgesenkt.
            Verlustpositionen ab 20 Handelssitzungen prüfen; Calls spätestens 20 Sitzungen vor dem
            letzten Handelstag schließen. Call-Marken sind separat zu bewerten, nicht per Omega.
          </p>
          {!preview.assessment.eligible && (
            <p role="alert">
              Einstiegsbedingungen nicht erfüllt: {preview.assessment.reasons.join(', ')}
            </p>
          )}
          <p className="text-xs text-slate-500">Hinweise: {preview.warnings.join(', ')}</p>
          {preview.trade_plan_content && preview.assessment.eligible && (
            <>
              <label className="block">
                <input
                  type="checkbox"
                  checked={reviewed}
                  disabled={busy}
                  onChange={(event) => setReviewed(event.target.checked)}
                />{' '}
                Rekonstruktion, Annahmen und Marken geprüft; als neuen Aktien-TradePlan vormerken
              </label>
              <button
                type="button"
                disabled={!reviewed || busy}
                onClick={() => void createDraft()}
                className="rounded border border-sky-700 px-4 py-2 disabled:opacity-40"
              >
                Geprüften Entwurf anlegen
              </button>
            </>
          )}
        </section>
      )}
    </details>
  );
}
