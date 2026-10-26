import { useLayoutEffect, useRef, useState } from 'react';
import { MarketApiError } from '../../market/services/http';
import { dataEvidenceApi } from '../services/dataEvidence';
import type { WarrantResponse, WarrantTermsResponse } from '../types/api';
import type { ValuationEvidenceView, ValuationFacts } from '../types/dataEvidence';

const empty: ValuationFacts = {
  product_type: null,
  exercise_style: null,
  quanto: null,
  ratio_convention: null,
  expiry_at: null,
  document_reference: '',
  source_url: null,
  reviewed_at: '',
  note: '',
};
const cls = 'block w-full min-w-0 rounded border border-slate-600 bg-slate-950 p-2';

export function WarrantValuationEvidence({
  warrant,
  terms,
  embedded = false,
  disabled = false,
  onCancel,
  onDirtyChange,
  onBusyChange,
  onReload,
}: {
  warrant: WarrantResponse;
  terms: WarrantTermsResponse;
  embedded?: boolean;
  disabled?: boolean;
  onCancel?: () => void;
  onDirtyChange?: (dirty: boolean) => void;
  onBusyChange?: (busy: boolean) => void;
  onReload?: () => void;
}) {
  const [basis] = useState(() => ({ warrant: { ...warrant }, terms: { ...terms } }));
  const [view, setView] = useState<ValuationEvidenceView | null>(null);
  const [facts, setFacts] = useState<ValuationFacts>(empty);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [conflict, setConflict] = useState(false);
  const active = useRef<AbortController | null>(null);
  const inFlight = useRef(false);
  const initialFacts = useRef<ValuationFacts>(empty);
  const dirty = useRef(false);
  useLayoutEffect(() => () => active.current?.abort(), []);

  function markDirty(value: boolean) {
    dirty.current = value;
    onDirtyChange?.(value);
  }
  function hasChanges(next: ValuationFacts) {
    return (Object.keys(empty) as (keyof ValuationFacts)[]).some(
      (key) => next[key] !== initialFacts.current[key],
    );
  }
  function change(next: ValuationFacts) {
    if (inFlight.current || disabled) return;
    setFacts(next);
    setConfirmed(false);
    setMessage('');
    markDirty(hasChanges(next));
  }
  async function run(save: boolean) {
    if (inFlight.current || disabled || (save && (!view || !confirmed || !basis.warrant.isin)))
      return;
    if (
      !save &&
      dirty.current &&
      !window.confirm('Ungespeicherte Belegangaben verwerfen und gespeicherte Belege neu laden?')
    )
      return;
    inFlight.current = true;
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setBusy(true);
    onBusyChange?.(true);
    setMessage('');
    setError('');
    setConflict(false);
    try {
      const next =
        save && view
          ? await dataEvidenceApi.recordFacts(
              basis.warrant.id,
              {
                terms_id: basis.terms.id,
                expected_version: basis.warrant.version,
                expected_revision: view.revision,
                facts,
                confirmation: 'CONFIRM_DOCUMENT_REVIEW',
              },
              controller.signal,
            )
          : await dataEvidenceApi.facts(basis.warrant.id, controller.signal);
      if (!controller.signal.aborted) {
        setView(next);
        initialFacts.current = { ...(next.current?.facts ?? empty) };
        setFacts(initialFacts.current);
        setConfirmed(false);
        markDirty(false);
        if (save)
          setMessage(
            `Belegrevision ${next.revision} gespeichert. Eine Live-IV ist dadurch noch nicht freigeschaltet.`,
          );
      }
    } catch (cause) {
      if (!controller.signal.aborted) {
        setError(
          cause instanceof MarketApiError
            ? `${cause.message} Bitte Produkt/Belege neu laden oder die Angaben einschließlich Zeitzonen prüfen.`
            : 'Belege nicht erreichbar. Ein Speichererfolg ist nicht bestätigt; bitte neu laden.',
        );
        setConflict(cause instanceof MarketApiError && cause.status === 409);
      }
    } finally {
      inFlight.current = false;
      if (!controller.signal.aborted) {
        setBusy(false);
        onBusyChange?.(false);
      }
    }
  }
  const content = (
    <>
      <p>
        Manuell geprüfte Produktbedingungen, keine Anbieterprüfung durch die Anwendung. Belege
        gelten für ISIN {basis.warrant.isin ?? 'unbekannt'} und Bedingungsversion{' '}
        {basis.terms.version_no}.
      </p>
      <button
        type="button"
        disabled={busy || disabled}
        className="rounded border px-3 py-2"
        onClick={() => void run(false)}
      >
        Produktbelege laden
      </button>
      {error && <p role="alert">{error}</p>}
      {conflict && (
        <div className="space-y-2 text-sm">
          <p>
            Die Eingaben bleiben erhalten. Produkt und Belege bewusst neu laden und vor einer
            weiteren Speicherung erneut prüfen.
          </p>
          {onReload && (
            <button
              type="button"
              disabled={busy || disabled}
              onClick={onReload}
              className="rounded border px-3 py-2"
            >
              Produkt neu laden und prüfen
            </button>
          )}
        </div>
      )}
      {message && <p role="status">{message}</p>}
      {view && (
        <>
          <p>
            Revision {view.revision} ·{' '}
            {view.status === 'CURRENT'
              ? 'Beleg passt zur aktuellen Produktidentität'
              : view.status === 'MISSING'
                ? 'Noch kein Beleg'
                : 'Identität oder Bedingungen geändert; erneute Prüfung erforderlich'}
            .
          </p>
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (confirmed) void run(true);
            }}
          >
            <fieldset disabled={busy || disabled} className="grid min-w-0 gap-3 sm:grid-cols-2">
              <label>
                Produktart
                <select
                  className={cls}
                  value={facts.product_type ?? ''}
                  onChange={(e) =>
                    change({
                      ...facts,
                      product_type: (e.target.value || null) as ValuationFacts['product_type'],
                    })
                  }
                >
                  <option value="">Unbekannt</option>
                  <option value="VANILLA_WARRANT">Klassischer Vanilla-Optionsschein</option>
                  <option value="OTHER_STRUCTURED">Anderes strukturiertes Produkt</option>
                </select>
              </label>
              <label>
                Ausübungsart
                <select
                  className={cls}
                  value={facts.exercise_style ?? ''}
                  onChange={(e) =>
                    change({
                      ...facts,
                      exercise_style: (e.target.value || null) as ValuationFacts['exercise_style'],
                    })
                  }
                >
                  <option value="">Unbekannt</option>
                  <option value="EUROPEAN">Europäisch</option>
                  <option value="AMERICAN">Amerikanisch</option>
                  <option value="OTHER">Andere</option>
                </select>
              </label>
              <label>
                Quanto-Eigenschaft
                <select
                  className={cls}
                  value={facts.quanto === null ? '' : String(facts.quanto)}
                  onChange={(e) =>
                    change({
                      ...facts,
                      quanto: e.target.value === '' ? null : e.target.value === 'true',
                    })
                  }
                >
                  <option value="">Unbekannt</option>
                  <option value="false">Kein Quanto laut Bedingungen</option>
                  <option value="true">Quanto laut Bedingungen</option>
                </select>
              </label>
              <label>
                Bezugsverhältnis-Konvention
                <select
                  className={cls}
                  value={facts.ratio_convention ?? ''}
                  onChange={(e) =>
                    change({
                      ...facts,
                      ratio_convention: e.target.value ? 'UNDERLYING_UNITS_PER_WARRANT' : null,
                    })
                  }
                >
                  <option value="">Unbekannt / nicht unterstützt</option>
                  <option value="UNDERLYING_UNITS_PER_WARRANT">Basiswerteinheiten je Schein</option>
                </select>
              </label>
              <label>
                Bewertungszeitpunkt mit Zeitzone (optional)
                <input
                  className={cls}
                  value={facts.expiry_at ?? ''}
                  placeholder="2026-12-18T17:30:00+01:00"
                  onChange={(e) => change({ ...facts, expiry_at: e.target.value || null })}
                />
              </label>
              <label>
                Beleg geprüft am, mit Zeitzone
                <input
                  required
                  className={cls}
                  value={facts.reviewed_at}
                  placeholder="2026-10-12T12:00:00+02:00"
                  onChange={(e) => change({ ...facts, reviewed_at: e.target.value })}
                />
              </label>
              <label>
                Dokument und Fundstelle
                <input
                  required
                  minLength={3}
                  maxLength={500}
                  className={cls}
                  value={facts.document_reference}
                  onChange={(e) => change({ ...facts, document_reference: e.target.value })}
                />
              </label>
              <label>
                Quellen-URL (optional)
                <input
                  type="url"
                  maxLength={2000}
                  className={cls}
                  value={facts.source_url ?? ''}
                  onChange={(e) => change({ ...facts, source_url: e.target.value || null })}
                />
              </label>
              <label className="sm:col-span-2">
                Prüfnotiz / Grund der Berichtigung
                <textarea
                  required
                  minLength={3}
                  maxLength={1000}
                  className={cls}
                  value={facts.note}
                  onChange={(e) => change({ ...facts, note: e.target.value })}
                />
              </label>
            </fieldset>
            <p>
              Jede Speicherung ist eine neue vollständige Belegrevision. „Unbekannt“ nimmt eine
              frühere Feststellung zurück. URLs werden nur gespeichert, nicht automatisch abgerufen.
              Zeitpunkte benötigen einen UTC-Versatz. Gespeicherte Belege bleiben erhalten und
              sperren die endgültige Löschung des Produkts.
            </p>
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                checked={confirmed}
                disabled={busy || disabled}
                onChange={(e) => {
                  if (inFlight.current || disabled) return;
                  setConfirmed(e.target.checked);
                  markDirty(e.target.checked || hasChanges(facts));
                }}
              />
              <span>
                Ich habe die genannten Angaben am Beleg für diese ISIN und Bedingungsversion
                geprüft.
              </span>
            </label>
            <button
              disabled={busy || disabled || !confirmed || !basis.warrant.isin}
              className="rounded border px-3 py-2 disabled:opacity-50"
            >
              Belegrevision speichern
            </button>
          </form>
          <details className="min-w-0 space-y-2">
            <summary className="cursor-pointer">Letzte 20 Belegrevisionen</summary>
            {view.history.map((item) => (
              <div key={item.id} className="min-w-0 border-t border-slate-700 py-2">
                <p>
                  Revision {item.revision} · erfasst {item.recorded_at} · geprüft{' '}
                  {item.facts.reviewed_at}
                </p>
                <p>
                  ISIN {item.identity?.isin ?? 'unbekannt'} · WKN{' '}
                  {item.identity?.wkn ?? 'unbekannt'} · Emittent-ID{' '}
                  {item.identity?.issuer_id ?? 'unbekannt'} · Basiswert-ID{' '}
                  {item.identity?.underlying_id ?? 'unbekannt'}
                </p>
                <p>
                  {item.facts.document_reference} · {item.facts.note}
                </p>
                <p>
                  Produktart {item.facts.product_type ?? 'unbekannt'} · Ausübung{' '}
                  {item.facts.exercise_style ?? 'unbekannt'} · Quanto{' '}
                  {item.facts.quanto === null ? 'unbekannt' : item.facts.quanto ? 'ja' : 'nein'} ·
                  Verhältnis {item.facts.ratio_convention ?? 'unbekannt'}
                </p>
                <p>
                  Bewertungszeitpunkt {item.facts.expiry_at ?? 'unbekannt'} · Bedingungs-ID{' '}
                  {item.terms_id}
                </p>
                <p>
                  Quelle {item.facts.source_url ?? 'Dokumentreferenz'} · Erfasst durch{' '}
                  {item.actor_id}
                </p>
              </div>
            ))}
          </details>
        </>
      )}
      {onCancel && (
        <button
          type="button"
          disabled={busy || disabled}
          onClick={onCancel}
          className="rounded border px-3 py-2"
        >
          Belegeditor schließen
        </button>
      )}
    </>
  );
  return embedded ? (
    <section aria-label="Bewertungsbelege" className="min-w-0 space-y-3 break-words">
      <h3 className="font-semibold">Produktmerkmale für IV mit Beleg erfassen</h3>
      {content}
    </section>
  ) : (
    <details className="min-w-0 space-y-3 break-words rounded border border-slate-700 p-3">
      <summary className="cursor-pointer font-semibold">
        Produktmerkmale für IV mit Beleg erfassen
      </summary>
      {content}
    </details>
  );
}
