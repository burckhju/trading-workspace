import { MarketApiError } from '../services/http';

export function ErrorNotice({ error }: { error: unknown }) {
  const message = error instanceof MarketApiError ? error.response.message : 'Die Daten konnten nicht geladen werden.';
  return <div role="alert" className="rounded-xl border border-red-800 bg-red-950/70 p-4 text-sm text-red-200">{message}</div>;
}

export function LoadingNotice({ label = 'Daten werden geladen …' }: { label?: string }) {
  return <div role="status" className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-sm text-slate-300">{label}</div>;
}
