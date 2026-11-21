import { useEffect, useRef, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';

import { currentNavigation, navigationGroups } from '../app/navigation';

const focusClass =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950';

export function ApplicationLayout() {
  const location = useLocation();
  const active = currentNavigation(location.pathname, location.search, location.hash);
  const [menuOpen, setMenuOpen] = useState(false);
  const previousPath = useRef(location.pathname);

  useEffect(() => setMenuOpen(false), [location.pathname, location.search, location.hash]);
  useEffect(() => {
    if (previousPath.current !== location.pathname)
      document.getElementById('page-content')?.focus({ preventScroll: true });
    previousPath.current = location.pathname;
  }, [location.pathname]);
  useEffect(() => {
    document.title = `${active?.item.label ?? 'Seite nicht gefunden'} · Trading Workspace`;
  }, [active?.item.label]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <a
        href="#page-content"
        onClick={(event) => {
          event.preventDefault();
          const content = document.getElementById('page-content');
          content?.focus({ preventScroll: true });
          content?.scrollIntoView?.({ block: 'start' });
        }}
        className={`sr-only absolute left-4 top-3 z-50 rounded-lg bg-slate-100 px-4 py-2 text-slate-950 focus:not-sr-only ${focusClass}`}
      >
        Zum Inhalt
      </a>
      <header className="border-b border-slate-800 bg-slate-950/95">
        <div className="mx-auto flex min-h-16 max-w-[1800px] items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Link to="/" className={`rounded-lg text-lg font-semibold tracking-tight ${focusClass}`}>
            Trading Workspace
          </Link>
          <p className="hidden text-sm text-slate-400 lg:block">{active?.group.question}</p>
          <button
            type="button"
            aria-expanded={menuOpen}
            aria-controls="workspace-navigation"
            onClick={() => setMenuOpen((open) => !open)}
            className={`rounded-lg border border-slate-700 px-3 py-2 text-sm lg:hidden ${focusClass}`}
          >
            {menuOpen ? 'Navigation schließen' : 'Navigation öffnen'}
          </button>
        </div>
      </header>
      <div className="mx-auto flex max-w-[1800px] flex-col lg:flex-row">
        <aside
          id="workspace-navigation"
          className={`${menuOpen ? 'block' : 'hidden'} border-b border-slate-800 p-4 lg:block lg:w-60 lg:shrink-0 lg:border-b-0 lg:border-r lg:py-6`}
        >
          <nav aria-label="Hauptnavigation" className="space-y-2">
            {navigationGroups.map((group) => {
              const selected = group.id === active?.group.id;
              return (
                <div key={group.id}>
                  <Link
                    to={group.to}
                    aria-current={selected ? 'location' : undefined}
                    className={`block rounded-lg px-3 py-2.5 text-sm font-semibold ${focusClass} ${selected ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-900 hover:text-white'}`}
                  >
                    {group.label}
                  </Link>
                  {selected && (
                    <nav
                      aria-label={`${group.label}: Unterbereiche`}
                      className="ml-3 mt-1 space-y-1 border-l border-slate-700 pl-2"
                    >
                      {group.items.map((item) => (
                        <Link
                          key={item.id}
                          to={item.to}
                          aria-current={item.id === active?.item.id ? 'page' : undefined}
                          className={`block rounded-lg px-3 py-2 text-sm ${focusClass} ${item.id === active?.item.id ? 'bg-sky-950/60 text-sky-200' : 'text-slate-400 hover:bg-slate-900 hover:text-white'}`}
                        >
                          {item.label}
                        </Link>
                      ))}
                    </nav>
                  )}
                </div>
              );
            })}
          </nav>
        </aside>
        <div className="min-w-0 flex-1 px-3 py-5 sm:px-6 lg:px-8">
          {active && (
            <nav
              aria-label="Aktueller Ort"
              className="mb-5 flex flex-wrap items-center gap-2 text-sm text-slate-400"
            >
              <Link to={active.group.to} className={`rounded ${focusClass}`}>
                {active.group.label}
              </Link>
              <span aria-hidden="true">/</span>
              <span aria-current="page" className="text-slate-200">
                {active.item.label}
              </span>
            </nav>
          )}
          <main id="page-content" tabIndex={-1} className="min-w-0 outline-none">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
