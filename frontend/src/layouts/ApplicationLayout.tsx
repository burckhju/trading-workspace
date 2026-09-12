import { NavLink, Outlet } from 'react-router-dom';

const navigationLinkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 ${
    isActive ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'
  }`;

export function ApplicationLayout() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between px-6">
          <NavLink
            to="/underlyings"
            className="rounded-lg text-lg font-semibold tracking-tight focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
          >
            Trading Workspace
          </NavLink>
          <nav aria-label="Hauptnavigation" className="flex flex-wrap justify-end gap-1">
            <NavLink to="/workspace" className={navigationLinkClass}>
              Arbeitsbereich
            </NavLink>
            <NavLink to="/underlyings" className={navigationLinkClass}>
              Stammdaten · Basiswerte
            </NavLink>
            <NavLink to="/issuers-admin" className={navigationLinkClass}>
              Stammdaten · Emittenten
            </NavLink>
            <NavLink to="/currencies-admin" className={navigationLinkClass}>
              Administration · Währungen
            </NavLink>
            <NavLink to="/warrants-admin" className={navigationLinkClass}>
              Produkte · Optionsscheine
            </NavLink>
            <NavLink to="/candidates" className={navigationLinkClass}>
              Kandidaten
            </NavLink>
            <NavLink to="/trade-plans/overview" className={navigationLinkClass}>
              TradePlans
            </NavLink>
            <NavLink to="/product-selection" className={navigationLinkClass}>
              Produktauswahl
            </NavLink>
            <NavLink to="/learning-imports" className={navigationLinkClass}>
              Learning · Import
            </NavLink>
            <NavLink to="/market-analyses" className={navigationLinkClass}>
              Marktanalyse
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto flex max-w-7xl px-6 py-10">
        <Outlet />
      </main>
    </div>
  );
}
