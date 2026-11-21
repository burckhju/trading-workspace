import { useState } from 'react';
import { Link } from 'react-router-dom';

import { WorkspaceActionLinks } from '../public/WorkspaceActionLinks';

export function ExecutionWorkspacePage() {
  const [tradeId, setTradeId] = useState('');
  return (
    <section className="w-full min-w-0 space-y-6">
      <header>
        <h1 className="text-3xl font-semibold text-white">Ausführungen</h1>
        <p className="mt-2 text-sm text-slate-400">
          Tatsächliche Käufe und Verkäufe erfassen und vorhandene Buchungen prüfen.
        </p>
      </header>
      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
          <h2 className="text-xl font-semibold">Ersten Kauf erfassen</h2>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Die Kauferfassung verwendet das ausgewählte Produkt eines konkreten Tradeplans. Öffne
            eine vorhandene Auswahl oder bereite deinen manuellen Tradeplan vor.
          </p>
          <div className="mt-4 flex flex-wrap gap-4 text-sm">
            <Link to="/product-selection" className="text-sky-300 underline">
              Produktauswahl öffnen
            </Link>
            <Link to="/trade-plans" className="text-sky-300 underline">
              Manuellen Tradeplan anlegen
            </Link>
          </div>
        </section>
        <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
          <h2 className="text-xl font-semibold">Bestehenden Trade bearbeiten</h2>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Öffne eine Position, um einen weiteren Kauf, einen Teil- oder Vollverkauf zu erfassen.
            Im Trade bleiben auch Buchungskorrekturen und die Stornierung erreichbar.
          </p>
          <div className="mt-4 flex flex-wrap gap-4 text-sm">
            <Link to="/workspace" className="text-sky-300 underline">
              Offene Position finden
            </Link>
            <Link to="/performance/closed-trades" className="text-sky-300 underline">
              Vollabschlüsse im Zeitraum
            </Link>
          </div>
        </section>
      </div>
      <WorkspaceActionLinks scope="purchase" />
      <details className="rounded-xl border border-slate-800 p-4">
        <summary className="cursor-pointer text-sm font-medium">
          Trade über bekannte Kennung öffnen
        </summary>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <label className="min-w-0 flex-1 text-sm text-slate-300">
            Trade-Kennung
            <input
              value={tradeId}
              onChange={(event) => setTradeId(event.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            />
          </label>
          {tradeId.trim() && (
            <Link
              to={`/trade-management?trade_id=${encodeURIComponent(tradeId.trim())}#execution-dates`}
              className="rounded-lg bg-sky-950 px-3 py-2 text-sm text-sky-100"
            >
              Buchungen öffnen
            </Link>
          )}
        </div>
      </details>
    </section>
  );
}
