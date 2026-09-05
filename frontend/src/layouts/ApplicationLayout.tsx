import { NavLink, Outlet } from 'react-router-dom';

export function ApplicationLayout() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between px-6">
          <NavLink to="/underlyings" className="text-lg font-semibold tracking-tight">
            Trading Workspace
          </NavLink>
          <nav aria-label="Hauptnavigation">
            <NavLink
              to="/underlyings"
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm ${isActive ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'}`
              }
            >
              Stammdaten · Basiswerte
            </NavLink>
            <NavLink
              to="/issuers-admin"
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm ${isActive ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'}`
              }
            >
              Stammdaten · Emittenten
            </NavLink>
            <NavLink
              to="/warrants-admin"
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm ${isActive ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'}`
              }
            >
              Produkte · Optionsscheine
            </NavLink>
            <NavLink
              to="/candidates"
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm ${isActive ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'}`
              }
            >
              Kandidaten
            </NavLink>
            <NavLink
              to="/trade-plans/overview"
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm ${isActive ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'}`
              }
            >
              TradePlans
            </NavLink>
            <NavLink
              to="/product-selection"
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm ${isActive ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'}`
              }
            >
              Produktauswahl
            </NavLink>
            <NavLink
              to="/learning-imports"
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm ${isActive ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'}`
              }
            >
              Learning · Import
            </NavLink>
            <NavLink
              to="/market-analyses"
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm ${isActive ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'}`
              }
            >
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
