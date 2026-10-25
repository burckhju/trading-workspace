import { useLayoutEffect, useRef, useState, type FormEvent } from 'react';

import { MarketApiError } from '../../market/services/http';
import { warrantApiClient } from '../services/client';
import type { WarrantResponse } from '../types/api';

export function WarrantIdentifierCorrection({
  warrant,
  onSaved,
  embedded = false,
  disabled = false,
  onCancel,
  onDirtyChange,
  onBusyChange,
  onReload,
}: {
  warrant: WarrantResponse;
  onSaved: (value: WarrantResponse) => void;
  embedded?: boolean;
  disabled?: boolean;
  onCancel?: () => void;
  onDirtyChange?: (dirty: boolean) => void;
  onBusyChange?: (busy: boolean) => void;
  onReload?: () => void;
}) {
  // A refresh must not rebase an already open correction onto a newer version.
  const [basis] = useState(() => ({ ...warrant }));
  const [isin, setIsin] = useState(basis.isin ?? '');
  const [wkn, setWkn] = useState(basis.wkn ?? '');
  const [evidence, setEvidence] = useState('');
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [conflict, setConflict] = useState(false);
  const inFlight = useRef(false);
  const mounted = useRef(true);
  useLayoutEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  function change(nextIsin: string, nextWkn: string, nextEvidence: string) {
    if (inFlight.current || saved || disabled) return;
    setIsin(nextIsin);
    setWkn(nextWkn);
    setEvidence(nextEvidence);
    onDirtyChange?.(
      nextIsin !== (basis.isin ?? '') || nextWkn !== (basis.wkn ?? '') || nextEvidence !== '',
    );
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (inFlight.current || saved || disabled) return;
    inFlight.current = true;
    setBusy(true);
    onBusyChange?.(true);
    setMessage('');
    setError('');
    setConflict(false);
    try {
      const updated = await warrantApiClient.correctIdentifiers(basis.id, {
        expected_version: basis.version,
        isin: isin.trim().toUpperCase(),
        wkn: wkn.trim().toUpperCase() || null,
        evidence: evidence.trim(),
      });
      if (!mounted.current) return;
      if (updated.id !== basis.id)
        throw new Error('Die gespeicherte Produktidentität passt nicht zur geöffneten Korrektur.');
      setSaved(true);
      onDirtyChange?.(false);
      setMessage('Kennungen gespeichert. Kurszuordnungen müssen nun erneut geprüft werden.');
      onSaved(updated);
    } catch (cause) {
      if (!mounted.current) return;
      setError(cause instanceof Error ? cause.message : 'Korrektur fehlgeschlagen');
      setConflict(cause instanceof MarketApiError && cause.status === 409);
    } finally {
      inFlight.current = false;
      if (mounted.current) {
        setBusy(false);
        onBusyChange?.(false);
      }
    }
  }

  const content = (
    <>
      <p className="my-2 text-sm text-slate-400">
        ISIN und WKN aus der Abrechnung oder einem offiziellen Produktdokument übernehmen. Nur
        Erfassungsfehler desselben Produkts korrigieren. Trade und Historie bleiben erhalten;
        bestehende Kurszuordnungen müssen erneut geprüft werden.
      </p>
      <form onSubmit={(event) => void save(event)}>
        <fieldset disabled={busy || saved || disabled} className="grid min-w-0 gap-3">
          <label>
            Verifizierte ISIN
            <input
              className="mt-1 block w-full min-w-0 rounded bg-slate-900 p-2"
              required
              minLength={12}
              maxLength={12}
              value={isin}
              onChange={(event) => change(event.target.value, wkn, evidence)}
            />
          </label>
          <label>
            Verifizierte WKN (optional)
            <input
              className="mt-1 block w-full min-w-0 rounded bg-slate-900 p-2"
              minLength={6}
              maxLength={6}
              value={wkn}
              onChange={(event) => change(isin, event.target.value, evidence)}
            />
          </label>
          <label>
            Beleg / Quelle der Korrektur
            <input
              className="mt-1 block w-full min-w-0 rounded bg-slate-900 p-2"
              required
              maxLength={500}
              value={evidence}
              onChange={(event) => change(isin, wkn, event.target.value)}
            />
          </label>
          <button className="rounded border border-slate-600 p-2" type="submit">
            Kennungen speichern
          </button>
        </fieldset>
      </form>
      {error && <p role="alert">{error}</p>}
      {conflict && (
        <div className="mt-3 space-y-2 text-sm">
          <p>
            Die Eingaben bleiben erhalten. Aktuellen Produktstand bewusst neu laden und die
            Korrektur einschließlich Beleg erneut prüfen.
          </p>
          {onReload && (
            <button
              type="button"
              disabled={busy || disabled}
              onClick={onReload}
              className="rounded border border-slate-600 p-2"
            >
              Produkt neu laden und prüfen
            </button>
          )}
        </div>
      )}
      {message && <p role="status">{message}</p>}
      {onCancel && (
        <button
          type="button"
          disabled={busy || disabled}
          onClick={onCancel}
          className="mt-3 rounded border border-slate-600 p-2"
        >
          {saved ? 'Korrektur schließen' : 'Korrektur abbrechen'}
        </button>
      )}
    </>
  );
  return embedded ? (
    <section aria-label="Kennungen korrigieren" className="min-w-0 space-y-3">
      <h3 className="font-semibold">Kennungen korrigieren</h3>
      {content}
    </section>
  ) : (
    <details className="min-w-0 rounded border border-slate-700 p-3">
      <summary>Kennungen korrigieren</summary>
      {content}
    </details>
  );
}
