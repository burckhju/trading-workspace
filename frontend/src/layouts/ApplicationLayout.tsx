import { Outlet } from 'react-router-dom';

export function ApplicationLayout() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center px-6">
          <span className="text-lg font-semibold tracking-tight">Trading Workspace</span>
        </div>
      </header>
      <main className="mx-auto flex max-w-7xl px-6 py-12">
        <Outlet />
      </main>
    </div>
  );
}
