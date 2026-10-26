import { useState } from 'react';
import { Link } from 'react-router-dom';
import { chartSetupClient, type SectorProposal } from '../../analysis/services/chartSetupClient';
import type { SetupDraft } from '../services/referenceSetup';

export function SetupProposals({
  busy,
  onPrepare,
}: {
  busy: boolean;
  onPrepare: (action: 'sector' | 'reference', draft: Partial<SetupDraft>) => void;
}) {
  const [proposals, setProposals] = useState<SectorProposal[] | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  async function toggle() {
    if (busy || loading) return;
    setOpen((value) => !value);
    if (proposals) return;
    setLoading(true);
    setError('');
    try {
      setProposals(await chartSetupClient.proposals());
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'Vorschläge nicht verfügbar.');
    } finally {
      setLoading(false);
    }
  }
  const buttonClass = 'rounded border border-slate-600 px-3 py-2 disabled:opacity-50';
  return (
    <section className="min-w-0 space-y-3 rounded border border-slate-700 p-4">
      <button
        type="button"
        aria-expanded={open}
        disabled={busy || loading}
        className="text-sky-300 underline disabled:opacity-50"
        onClick={() => void toggle()}
      >
        Sektor- und ETF-Vorschläge {open ? 'ausblenden' : 'anzeigen'}
      </button>
      {error && <p role="alert">{error}</p>}
      {open && (
        <>
          <h2 className="text-lg font-semibold">Einrichtungshilfe mit Quellen</h2>
          <p className="text-sm text-slate-300">
            Vorbereiten eines Vorschlags schreibt nichts. Vorhandene Systematik und echte
            Wertpapieridentitäten bleiben maßgeblich. Providerabdeckung und verfügbare Historie sind
            damit nicht bestätigt.
          </p>
          <div className="grid min-w-0 gap-3 sm:grid-cols-2">
            {proposals?.map((hint) => (
              <article
                key={hint.code}
                className="min-w-0 space-y-2 break-words rounded border border-slate-700 p-3 text-sm"
              >
                <h3 className="font-semibold">
                  {hint.code} · {hint.sector}
                </h3>
                <p>{hint.benchmark}</p>
                <p>
                  {hint.ticker} · ETF-Proxy · {hint.isin} · {hint.mic} · {hint.currency}
                </p>
                <p className="text-xs text-slate-400">
                  Quellenstand: {hint.reviewed_on} · {hint.classification_system}{' '}
                  {hint.classification_version} · Providerabdeckung: {hint.provider_coverage}
                </p>
                <div className="flex flex-wrap gap-3">
                  <a
                    className="text-sky-300 underline"
                    href={hint.source_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Emittentenbeleg
                  </a>
                  <a
                    className="text-sky-300 underline"
                    href={hint.taxonomy_source}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Taxonomie
                  </a>
                  <a
                    className="text-sky-300 underline"
                    href={hint.venue_source}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Handelsplatzbeleg
                  </a>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    className={buttonClass}
                    onClick={() =>
                      onPrepare('sector', {
                        code: hint.code,
                        name: hint.sector,
                        system: hint.classification_system,
                        version: hint.classification_version,
                      })
                    }
                  >
                    Sektorformular vorbereiten
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    className={buttonClass}
                    onClick={() =>
                      onPrepare('reference', {
                        code: `SELECT_${hint.ticker}`,
                        name: hint.benchmark,
                        version: hint.reviewed_on,
                        region: 'US',
                      })
                    }
                  >
                    Benchmarkformular vorbereiten
                  </button>
                </div>
                <Link
                  className="block text-sky-300 underline"
                  to={`/underlyings/new?${new URLSearchParams({ type: 'ETF', name: `State Street ${hint.benchmark.replace(' Index', '')} SPDR ETF`, isin: hint.isin, ticker: hint.ticker, mic: hint.mic, currency: hint.currency }).toString()}`}
                >
                  ETF-Stammdaten prüfen / anlegen
                </Link>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
