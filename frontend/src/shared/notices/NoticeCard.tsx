import { Link } from 'react-router-dom';

import type { ContextActionLinkProps, NoticeCardProps, NoticeDetailsProps } from './types';

const presentationStyles = {
  information: { label: 'Hinweis', className: 'border-slate-600 text-slate-200' },
  warning: { label: 'Warnung', className: 'border-amber-700 text-amber-200' },
  blocker: { label: 'Blockierung', className: 'border-red-700 text-red-200' },
  error: { label: 'Fehler', className: 'border-red-700 text-red-200' },
  success: { label: 'Bestätigt', className: 'border-emerald-700 text-emerald-200' },
};

export function ContextActionLink({ action }: ContextActionLinkProps) {
  const href = action.destination.href;
  if (!href.startsWith('/') || href.startsWith('//') || /[\\\s]/u.test(href)) {
    return <span className="[overflow-wrap:anywhere]">{action.label}</span>;
  }
  return (
    <Link
      to={href}
      className="inline-block max-w-full rounded text-sky-300 underline [overflow-wrap:anywhere] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
    >
      {action.label}
    </Link>
  );
}

export function NoticeDetails({ id, rows, time, actions = [] }: NoticeDetailsProps) {
  const times = [
    { label: 'Fachlicher Zeitpunkt', value: time.observedAt },
    { label: 'Prüfzeit', value: time.checkedAt },
    { label: 'Gültig ab', value: time.validFrom },
    { label: 'Gültig bis ausschließlich', value: time.validTo },
  ].filter((entry) => entry.value !== null);
  if (rows.length === 0 && times.length === 0 && !time.explanation && actions.length === 0) {
    return null;
  }

  return (
    <details id={id} className="min-w-0 text-sm">
      <summary className="cursor-pointer rounded [overflow-wrap:anywhere] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950">
        Ursache und Quellen
      </summary>
      {(rows.length > 0 || times.length > 0) && (
        <dl className="mt-3 space-y-3">
          {rows.map((row, index) => (
            <div key={`${row.label}:${index}`} className="min-w-0">
              <dt className="font-medium [overflow-wrap:anywhere]">{row.label}</dt>
              <dd className="mt-1 whitespace-pre-wrap text-slate-300 [overflow-wrap:anywhere]">
                {row.value}
              </dd>
            </div>
          ))}
          {times.map(({ label, value }) => (
            <div key={label} className="min-w-0">
              <dt className="font-medium">{label}</dt>
              <dd className="mt-1 text-slate-300 [overflow-wrap:anywhere]">
                <time dateTime={value ?? undefined}>{value}</time>
              </dd>
            </div>
          ))}
        </dl>
      )}
      {time.explanation && (
        <p className="mt-3 text-slate-300 [overflow-wrap:anywhere]">{time.explanation}</p>
      )}
      {actions.length > 0 && (
        <ul className="mt-3 space-y-2">
          {actions.map((action, index) => (
            <li key={`${action.destination.href}:${index}`}>
              <ContextActionLink action={action} />
            </li>
          ))}
        </ul>
      )}
    </details>
  );
}

/** Static owner facts: mounting, opening details and replacing props announce nothing. */
export function NoticeCard({ notice, headingLevel, detailsId }: NoticeCardProps) {
  const Heading: 'h2' | 'h3' | 'h4' = `h${headingLevel}`;
  const headingId = `${detailsId}-title`;
  const style = presentationStyles[notice.presentation.kind];
  const [primaryAction, ...secondaryActions] = notice.actions;
  return (
    <section
      aria-labelledby={headingId}
      data-notice-id={notice.id}
      className={`min-w-0 max-w-full space-y-3 rounded-lg border bg-slate-950/50 p-4 text-sm [overflow-wrap:anywhere] ${style.className}`}
    >
      <header className="space-y-1">
        <p className="text-xs font-semibold">{style.label}</p>
        <Heading id={headingId} className="font-semibold">
          {notice.title}
        </Heading>
      </header>
      <p>{notice.cause.explanation}</p>
      <p>{notice.impact}</p>
      {notice.automatic.explanation && <p>{notice.automatic.explanation}</p>}
      {notice.userNeed.explanation && <p>{notice.userNeed.explanation}</p>}
      {primaryAction && <ContextActionLink action={primaryAction} />}
      <NoticeDetails
        id={detailsId}
        rows={notice.details}
        time={notice.time}
        actions={secondaryActions}
      />
    </section>
  );
}
