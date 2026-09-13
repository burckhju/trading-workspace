import type { OperationalPosition } from '../types';
import { statusLabel } from '../services/statusLabels';
import { positionTone } from '../services/positionsView';

const tones = {
  critical: 'border-rose-700 bg-rose-950/50 text-rose-200',
  attention: 'border-amber-700 bg-amber-950/40 text-amber-200',
  data: 'border-amber-800 bg-amber-950/30 text-amber-200',
  ok: 'border-emerald-800 bg-emerald-950/30 text-emerald-200',
  indicative: 'border-sky-800 bg-sky-950/40 text-sky-200',
  missing: 'border-slate-600 bg-slate-800 text-slate-200',
} as const;
export function StatusBadge({
  tone,
  children,
}: {
  tone: keyof typeof tones;
  children: React.ReactNode;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}
export function PositionStatus({ position: p }: { position: OperationalPosition }) {
  const tone = positionTone(p);
  const label =
    tone === 'critical'
      ? '! Kritischer Hinweis'
      : tone === 'attention'
        ? '! Fachlicher Hinweis'
        : tone === 'data'
          ? '? Daten prüfen'
          : '✓ Unauffällig';
  return <StatusBadge tone={tone}>{label}</StatusBadge>;
}
export function QuoteStatus({ position: p }: { position: OperationalPosition }) {
  const tone =
    p.valuation_status === 'AVAILABLE' && !p.analysis_warning
      ? 'ok'
      : p.valuation_status === 'INDICATIVE'
        ? 'indicative'
        : ['STALE', 'LAST_AVAILABLE'].includes(p.valuation_status) || p.analysis_warning
          ? 'data'
          : 'missing';
  return <StatusBadge tone={tone}>Produktkurs: {statusLabel(p.valuation_status)}</StatusBadge>;
}
