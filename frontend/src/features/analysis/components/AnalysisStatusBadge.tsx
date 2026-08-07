type BadgeKind = 'status' | 'quality';
const labels: Record<BadgeKind, Record<string, string>> = {
  status: {
    DRAFT: 'Entwurf',
    RUNNING: 'Wird ausgeführt',
    COMPLETED: 'Abgeschlossen',
    COMPLETED_WITH_WARNINGS: 'Mit Hinweisen',
    NOT_EVALUABLE: 'Nicht auswertbar',
    FAILED: 'Fehlgeschlagen',
    SUPERSEDED: 'Ersetzt',
  },
  quality: { GOOD: 'Gut', LIMITED: 'Eingeschränkt', INSUFFICIENT: 'Unzureichend' },
};
const classes: Record<string, string> = {
  COMPLETED: 'border-emerald-700 bg-emerald-950 text-emerald-200',
  GOOD: 'border-emerald-700 bg-emerald-950 text-emerald-200',
  COMPLETED_WITH_WARNINGS: 'border-amber-700 bg-amber-950 text-amber-200',
  LIMITED: 'border-amber-700 bg-amber-950 text-amber-200',
  NOT_EVALUABLE: 'border-slate-600 bg-slate-900 text-slate-300',
  INSUFFICIENT: 'border-slate-600 bg-slate-900 text-slate-300',
  FAILED: 'border-red-700 bg-red-950 text-red-200',
};
export function AnalysisStatusBadge({ value, kind }: { value: string; kind: BadgeKind }) {
  return (
    <span
      className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${classes[value] ?? 'border-slate-600 bg-slate-900 text-slate-300'}`}
    >
      {labels[kind][value] ?? value}
    </span>
  );
}
