import { useEffect, useState } from 'react';

import { tradePlanApiClient } from '../services/client';
import {
  loadHebeltraderSources,
  reviewHebeltraderSource,
} from '../services/hebeltraderSourcesClient';
import type {
  HebeltraderSource,
  SourceAxis,
  SourceReview,
  SourceReviewRequest,
} from '../services/hebeltraderSourcesClient';

interface Props {
  underlyingId: string;
  onCreated: (tradePlanId: string) => void;
}

const emptyQuote = { bid: '', ask: '', observedAt: '', source: '' };
const fieldLabels: Record<string, string> = {
  entry: 'Veröffentlichter Einstieg',
  stop: 'Stopp 1',
  target1: 'Ziel 1',
  target2: 'Ziel 2',
  gd200: 'GD200',
  gd50: 'GD50',
};

function AxisView({ axis, label }: { axis: SourceAxis; label: string }) {
  return (
    <section aria-label={label} className="space-y-2">
      <h3 className="font-semibold">{label}</h3>
      <dl className="grid grid-cols-2 gap-2 text-sm">
        {Object.entries(axis.values).map(([key, value]) => (
          <div key={key}>
            <dt className="text-slate-400">{fieldLabels[key] ?? key}</dt>
            <dd>{value === null ? 'Nicht verfügbar' : `${value} ${axis.currency ?? ''}`}</dd>
          </div>
        ))}
      </dl>
      <p>Quellen-CRV (50/50, vor Kosten): {axis.reward_risk ?? 'Nicht berechenbar'}</p>
      {axis.issues.map((issue) => (
        <p key={issue} className="text-sm text-amber-300">{issue}</p>
      ))}
    </section>
  );
}

export function HebeltraderPanel({ underlyingId, onCreated }: Props) {
  // Keying this subtree also protects against stale responses after a basiswert change.
  return <SourcePanel key={underlyingId} underlyingId={underlyingId} onCreated={onCreated} />;
}

function SourcePanel({ underlyingId, onCreated }: Props) {
  const [items, setItems] = useState<HebeltraderSource[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [quote, setQuote] = useState(emptyQuote);
  const [fundamentalOk, setFundamentalOk] = useState(false);
  const [targetHistory, setTargetHistory] = useState<SourceReviewRequest['target_history']>('UNKNOWN');
  const [review, setReview] = useState<SourceReview | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selected = items.find((item) => item.version_id === selectedId);
  const current = review?.current_preview;

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setLoading(true);
    setLoadError(null);
    void loadHebeltraderSources(underlyingId, 0, controller.signal)
      .then((result) => {
        if (!active) return;
        setItems(result.items);
        setSelectedId(result.items[0]?.version_id ?? '');
        setNextOffset(result.next_offset);
      })
      .catch((cause: unknown) => {
        if (active) setLoadError(cause instanceof Error ? cause.message : 'Importdaten fehlen.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [underlyingId, reload]);

  function invalidate() {
    setReview(null);
    setReviewed(false);
    setError(null);
  }

  async function loadMore() {
    if (nextOffset === null || busy) return;
    setBusy(true);
    try {
      const result = await loadHebeltraderSources(underlyingId, nextOffset);
      setItems((previous) => [...previous, ...result.items]);
      setNextOffset(result.next_offset);
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : 'Weitere Empfehlungen fehlen.');
    } finally {
      setBusy(false);
    }
  }

  async function calculate() {
    if (!selected || busy) return;
    invalidate();
    setBusy(true);
    try {
      const hasQuote = Object.values(quote).some((value) => value.trim() !== '');
      if (hasQuote && Object.values(quote).some((value) => value.trim() === '')) {
        throw new Error('Kurs, Kurszeit und Handelsplatz nur vollständig übernehmen oder leer lassen.');
      }
      const body: SourceReviewRequest = {
        underlying_id: underlyingId,
        source_version_id: selected.version_id,
        fundamental_ok: fundamentalOk,
        target_history: targetHistory,
      };
      if (hasQuote) {
        if (!selected.stock.currency) throw new Error('Quellenwährung fehlt.');
        const observed = new Date(quote.observedAt);
        if (!Number.isFinite(observed.getTime())) throw new Error('Kurszeit ist ungültig.');
        for (const value of [quote.bid, quote.ask]) {
          if (!/^\d+(\.\d+)?$/.test(value.trim().replace(',', '.'))) {
            throw new Error('Kurse ohne Tausendertrennzeichen eingeben.');
          }
        }
        body.quote = {
          bid: quote.bid.trim().replace(',', '.'),
          ask: quote.ask.trim().replace(',', '.'),
          observed_at: observed.toISOString(),
          source: quote.source.trim(),
          currency: selected.stock.currency,
        };
      }
      setReview(await reviewHebeltraderSource(body));
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : 'Prüfung fehlgeschlagen.');
    } finally {
      setBusy(false);
    }
  }

  async function createDraft() {
    if (!current?.trade_plan_content || !current.assessment.eligible || !reviewed || busy) return;
    setBusy(true);
    try {
      const result = await tradePlanApiClient.create({
        ...current.trade_plan_content,
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

  return (
    <details className="rounded-xl border border-slate-800 p-5">
      <summary className="cursor-pointer text-lg font-semibold">Hebeltrader-Regelvorschau</summary>
      <p className="mt-3 text-sm text-slate-400">
        Marken werden aus bestätigten PDF-Importen übernommen. Keine Eingabe von Bandbreite,
        Stopp-Puffer, Tickgröße oder anderen Modellannahmen. Fehlende Daten werden nicht geschätzt.
      </p>
      {loading && <p role="status">Importierte Empfehlungen werden geladen.</p>}
      {loadError && <p role="alert">{loadError}</p>}
      {!loading && !loadError && items.length === 0 && (
        <p>Keine bestätigte Hebeltrader-Empfehlung für diesen Basiswert vorhanden. PDF-Import nutzen.</p>
      )}
      <button
        type="button"
        disabled={loading || busy}
        onClick={() => {
          invalidate();
          setQuote(emptyQuote);
          setFundamentalOk(false);
          setTargetHistory('UNKNOWN');
          setReload((value) => value + 1);
        }}
        className="mt-3 rounded border border-slate-700 px-3 py-2"
      >
        Importdaten neu laden
      </button>
      {items.length > 0 && (
        <label className="mt-3 block">
          Importierte Empfehlung
          <select
            aria-label="Importierte Empfehlung"
            disabled={busy || loading}
            value={selectedId}
            onChange={(event) => {
              setSelectedId(event.target.value);
              setQuote(emptyQuote);
              setFundamentalOk(false);
              setTargetHistory('UNKNOWN');
              invalidate();
            }}
            className="mt-1 block w-full rounded border border-slate-700 bg-slate-950 p-2"
          >
            {items.map((item) => (
              <option key={item.version_id} value={item.version_id}>
                {item.label} · {item.issue_date ?? 'Datum unbekannt'}
              </option>
            ))}
          </select>
        </label>
      )}
      {nextOffset !== null && (
        <button type="button" disabled={busy} onClick={() => void loadMore()}>
          Weitere Empfehlungen laden
        </button>
      )}
      {selected && !loading && (
        <div className="mt-4 space-y-4">
          <p className="text-sm">
            Quelle: {selected.filename ?? 'Dateinachweis fehlt'} · Ausgabe: {selected.issue_date}
          </p>
          <p className="text-sm text-amber-300">
            Historische Veröffentlichung, kein aktueller Geld-/Briefkurs und keine Einstiegsfreigabe.
          </p>
          <AxisView axis={selected.stock} label="Aktie: veröffentlichte Werte" />
          <AxisView axis={selected.warrant} label="Optionsschein: veröffentlichte Werte" />
          {selected.source_issues.map((issue) => <p key={issue} role="alert">{issue}</p>)}
          <details>
            <summary>Optional: aktuell sichtbare Aktienkurse prüfen</summary>
            <p className="mt-2 text-sm text-slate-400">
              Nur unmittelbar bei Bank oder Börse ablesbare Werte übernehmen, sonst leer lassen.
              Kurszeit in der lokalen Browser-Zeitzone. Währung: {selected.stock.currency ?? 'unbekannt'}.
            </p>
            <fieldset disabled={busy} className="mt-3 grid gap-3 md:grid-cols-2">
              {([
                ['bid', 'Geldkurs Aktie'],
                ['ask', 'Briefkurs Aktie'],
                ['observedAt', 'Angezeigte Kurszeit'],
                ['source', 'Angezeigter Handelsplatz / Kursanbieter'],
              ] as const).map(([key, label]) => (
                <label key={key} className="text-sm">
                  {label}
                  <input
                    aria-label={label}
                    type={key === 'observedAt' ? 'datetime-local' : 'text'}
                    step={key === 'observedAt' ? '1' : undefined}
                    value={quote[key]}
                    onChange={(event) => {
                      setQuote((previous) => ({ ...previous, [key]: event.target.value }));
                      invalidate();
                    }}
                    className="mt-1 block w-full rounded border border-slate-700 bg-slate-950 p-2"
                  />
                </label>
              ))}
              <label>
                Zielhistorie laut sichtbarem Kursverlauf
                <select
                  aria-label="Zielhistorie laut sichtbarem Kursverlauf"
                  value={targetHistory}
                  onChange={(event) => {
                    setTargetHistory(event.target.value as SourceReviewRequest['target_history']);
                    invalidate();
                  }}
                  className="block bg-slate-950 p-2"
                >
                  <option value="UNKNOWN">Nicht ersichtlich / unbekannt</option>
                  <option value="NOT_REACHED">Noch kein Ziel erreicht</option>
                  <option value="TARGET1_REACHED">Ziel 1 bereits erreicht</option>
                  <option value="TARGET2_REACHED">Ziel 2 bereits erreicht</option>
                </select>
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={fundamentalOk}
                  onChange={(event) => { setFundamentalOk(event.target.checked); invalidate(); }}
                />{' '}
                Fundamentale These separat geprüft
              </label>
            </fieldset>
          </details>
          <button type="button" disabled={busy} onClick={() => void calculate()}>
            Vorhandene Daten prüfen
          </button>
          {review && (
            <section aria-label="Hebeltrader-Ergebnis" className="space-y-3 text-sm">
              {review.missing_data.map((message) => <p key={message}>{message}</p>)}
              {current && (
                <>
                  <p>Aktuelles Brutto-CRV: {current.assessment.reward_risk ?? 'Nicht berechenbar'}</p>
                  {!current.assessment.eligible && (
                    <p role="alert">Nicht freigegeben: {current.assessment.reasons.join(', ')}</p>
                  )}
                  <p>Hinweise: {current.warnings.join(', ')}</p>
                  {current.trade_plan_content && current.assessment.eligible && (
                    <>
                      <label className="block">
                        <input
                          type="checkbox"
                          disabled={busy}
                          checked={reviewed}
                          onChange={(event) => setReviewed(event.target.checked)}
                        />{' '}
                        Quelle, Marken und aktuelle Einstiegsbedingungen geprüft
                      </label>
                      <button
                        type="button"
                        disabled={!reviewed || busy}
                        onClick={() => void createDraft()}
                      >
                        Geprüften Entwurf anlegen
                      </button>
                    </>
                  )}
                </>
              )}
            </section>
          )}
          <p className="text-xs text-slate-500">
            Quellenversion: {selected.version_id} · Datei-Prüfwert: {selected.content_hash ?? 'fehlt'}
          </p>
        </div>
      )}
      {error && <p role="alert" className="mt-3 text-red-400">{error}</p>}
    </details>
  );
}
