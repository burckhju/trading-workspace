import { Link } from 'react-router-dom';

import { MarketDataRefreshPanel } from './MarketDataRefreshPanel';

export function DataSourcesPage() {
  return (
    <section className="w-full min-w-0 space-y-6">
      <header>
        <h1 className="text-3xl font-semibold text-white">Datenquellen &amp; Diagnose</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Datenstand und Versorgung prüfen. Instrumentbezogene Fehler bearbeitest du direkt am
          betroffenen Basiswert oder Produkt.
        </p>
      </header>
      <nav aria-label="Datenprobleme gezielt bearbeiten" className="grid gap-3 md:grid-cols-3">
        <Link to="/workspace" className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <span className="font-semibold text-white">Positionsüberwachung</span>
          <span className="mt-2 block text-sm text-slate-400">
            Überwachungszustand und entscheidungsrelevante Datenprobleme einer Position.
          </span>
        </Link>
        <Link to="/chart-setup" className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <span className="font-semibold text-white">Kursdaten einrichten</span>
          <span className="mt-2 block text-sm text-slate-400">
            Zuordnungen, Kursabdeckung und historische Daten.
          </span>
        </Link>
        <Link
          to="/warrants-admin"
          className="rounded-xl border border-slate-800 bg-slate-900/40 p-4"
        >
          <span className="font-semibold text-white">Produktdaten prüfen</span>
          <span className="mt-2 block text-sm text-slate-400">
            Identität, Kurse, Fälligkeit und Handelsschluss des Optionsscheins.
          </span>
        </Link>
      </nav>
      <MarketDataRefreshPanel />
    </section>
  );
}
