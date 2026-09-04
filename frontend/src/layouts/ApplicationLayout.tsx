import { NavLink, Outlet } from 'react-router-dom';

const navigationLinkClassName = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 ${
    isActive ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'
  }`;

export function ApplicationLayout() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between px-6">
          <NavLink to="/underlyings" className="text-lg font-semibold tracking-tight">
            Trading Workspace
          </NavLink>
          <nav aria-label="Hauptnavigation">
            <NavLink to="/underlyings" className={navigationLinkClassName}>
              Stammdaten · Basiswerte
            </NavLink>
            <NavLink to="/issuers-admin" className={navigationLinkClassName}>
              Stammdaten · Emittenten
            </NavLink>
            <NavLink to="/warrants-admin" className={navigationLinkClassName}>
              Produkte · Optionsscheine
            </NavLink>
            <NavLink to="/candidates" className={navigationLinkClassName}>
              Kandidaten
            </NavLink>
            <NavLink to="/trade-plans" className={navigationLinkClassName}>
              TradePlans
            </NavLink>
            <NavLink to="/product-selection" className={navigationLinkClassName}>
              Produktauswahl
            </NavLink>
            <NavLink to="/learning-imports" className={navigationLinkClassName}>
              Learning · Import
            </NavLink>
            <NavLink to="/market-analyses" className={navigationLinkClassName}>
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
