import type { LifecycleStatus, QualityStatus } from '../types/api';

type Status = LifecycleStatus | QualityStatus;

const labels: Record<Status, string> = {
  ACTIVE: 'Aktiv',
  INACTIVE: 'Deaktiviert',
  DRAFT: 'Entwurf',
  COMPLETE: 'Vollständig',
  VERIFIED: 'Verifiziert',
};

export function StatusBadge({ status }: { status: Status }) {
  const tone =
    status === 'ACTIVE' || status === 'VERIFIED'
      ? 'border-emerald-700 bg-emerald-950 text-emerald-300'
      : status === 'INACTIVE'
        ? 'border-slate-700 bg-slate-900 text-slate-400'
        : status === 'COMPLETE'
          ? 'border-sky-700 bg-sky-950 text-sky-300'
          : 'border-amber-700 bg-amber-950 text-amber-300';
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${tone}`}>{labels[status]}</span>;
}
