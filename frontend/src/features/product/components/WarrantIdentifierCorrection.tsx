import { useState, type FormEvent } from 'react';

import { warrantApiClient } from '../services/client';
import type { WarrantResponse } from '../types/api';

export function WarrantIdentifierCorrection({
  warrant,
  onSaved,
}: {
  warrant: WarrantResponse;
  onSaved: (value: WarrantResponse) => void;
}) {
  const [isin, setIsin] = useState(warrant.isin ?? '');
  const [wkn, setWkn] = useState(warrant.wkn ?? '');
  const [evidence, setEvidence] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    try {
      const updated = await warrantApiClient.correctIdentifiers(warrant.id, {
        expected_version: warrant.version,
        isin: isin.trim().toUpperCase(),
        wkn: wkn.trim().toUpperCase() || null,
        evidence: evidence.trim(),
      });
      onSaved(updated);
      setMessage('Kennungen gespeichert. Kurszuordnungen müssen nun erneut geprüft werden.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Korrektur fehlgeschlagen');
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="rounded border border-slate-700 p-3">
      <summary>Kennungen korrigieren</summary>
      <p className="my-2 text-sm text-slate-400">
        ISIN und WKN aus der Abrechnung oder einem offiziellen Produktdokument übernehmen. Nur
        Erfassungsfehler desselben Produkts korrigieren. Trade und Historie bleiben erhalten;
        bestehende Kurszuordnungen müssen erneut geprüft werden.
      </p>
      <form onSubmit={(event) => void save(event)} className="grid gap-2">
        <label>
          Verifizierte ISIN
          <input
            className="ml-2 rounded bg-slate-900 p-2"
            required
            minLength={12}
            maxLength={12}
            value={isin}
            onChange={(event) => setIsin(event.target.value)}
          />
        </label>
        <label>
          Verifizierte WKN (optional)
          <input
            className="ml-2 rounded bg-slate-900 p-2"
            minLength={6}
            maxLength={6}
            value={wkn}
            onChange={(event) => setWkn(event.target.value)}
          />
        </label>
        <label>
          Beleg / Quelle der Korrektur
          <input
            className="ml-2 rounded bg-slate-900 p-2"
            required
            maxLength={500}
            value={evidence}
            onChange={(event) => setEvidence(event.target.value)}
          />
        </label>
        <button disabled={busy} className="rounded border border-slate-600 p-2" type="submit">
          Kennungen speichern
        </button>
        {message && <p role="status">{message}</p>}
      </form>
    </details>
  );
}
