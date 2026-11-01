import { Link } from 'react-router-dom';

import type { NoticeCardProps, NoticeView } from './types';

const presentationStyles = {
  information: { label: 'Hinweis', className: 'border-slate-600 text-slate-200' },
  warning: { label: 'Warnung', className: 'border-amber-700 text-amber-200' },
};

function ContextActionLink({ action }: { action: NoticeView['action'] }) {
  const { href, label } = action;
  if (!href.startsWith('/') || href.startsWith('//') || /[\\\s]/u.test(href)) {
    return <span className="[overflow-wrap:anywhere]">{label}</span>;
  }
  return (
    <Link
      to={href}
      className="inline-block max-w-full rounded text-sky-300 underline [overflow-wrap:anywhere] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
    >
      {label}
    </Link>
  );
}

/** Static owner facts: mounting, opening details and replacing props announce nothing. */
export function NoticeCard({ notice, headingLevel, detailsId }: NoticeCardProps) {
  const Heading: 'h2' | 'h3' | 'h4' = `h${headingLevel}`;
  const headingId = `${detailsId}-title`;
  const style = presentationStyles[notice.presentation];
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
      <p>{notice.cause}</p>
      <p>{notice.impact}</p>
      {notice.automatic && <p>{notice.automatic}</p>}
      {notice.userNeed && <p>{notice.userNeed}</p>}
      <ContextActionLink action={notice.action} />
      {notice.details.length > 0 && (
        <details id={detailsId} className="min-w-0 text-sm">
          <summary className="cursor-pointer rounded [overflow-wrap:anywhere] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950">
            Ursache und Quellen
          </summary>
          <dl className="mt-3 space-y-3">
            {notice.details.map((row, index) => (
              <div key={`${row.label}:${index}`} className="min-w-0">
                <dt className="font-medium [overflow-wrap:anywhere]">{row.label}</dt>
                <dd className="mt-1 whitespace-pre-wrap text-slate-300 [overflow-wrap:anywhere]">
                  {row.value}
                </dd>
              </div>
            ))}
          </dl>
        </details>
      )}
    </section>
  );
}
