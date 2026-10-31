import { useEffect } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';

import { closedListUrl, parseClosedContext } from './closedReportNavigation';
import { closedContextKeys, pinKeys } from './context';
import { tradeWorkspaceLink, type TradeWorkspaceView } from './links';

const areas: { label: string; view: TradeWorkspaceView; hash: string; activeOnly?: boolean }[] = [
  { label: 'Überblick', view: 'management', hash: '#trade-overview' },
  {
    label: 'Kursverlauf',
    view: 'management',
    hash: '#position-price-history',
    activeOnly: true,
  },
  { label: 'Buchungen', view: 'management', hash: '#execution-dates' },
  { label: 'Risiko und Management', view: 'management', hash: '#trade-risk', activeOnly: true },
  { label: 'Plan und Quellen', view: 'sources', hash: '#trade-plan-sources' },
  { label: 'Journal und Lessons', view: 'journal', hash: '#trade-journal' },
];
const anchors = new Set([
  ...areas.map((area) => area.hash),
  '#sale-capture',
  '#trade-management-state',
  '#trade-journal-sources',
  '#trade-evidence-sources',
]);

/** Links keep existing owners mounted; a section change never creates a new draft or read. */
export function TradeWorkspaceNavigation({
  tradeId,
  view,
  cancelled = false,
  showBackLinks = true,
}: {
  tradeId: string;
  view: TradeWorkspaceView;
  cancelled?: boolean;
  showBackLinks?: boolean;
}) {
  const location = useLocation();
  const [query] = useSearchParams();
  const reportContext = parseClosedContext(query).context;
  const allowedKeys = new Set<string>(['trade_id', 'view', ...pinKeys, ...closedContextKeys]);
  const sameQuery = [...query.keys()].every((key) => allowedKeys.has(key));
  useEffect(() => {
    if (!anchors.has(location.hash)) return;
    const target = document.getElementById(location.hash.slice(1));
    target?.scrollIntoView?.({ block: 'start' });
    target?.focus({ preventScroll: true });
  }, [location.hash, location.key]);

  return (
    <nav aria-label="Trade-Arbeitsbereiche" className="min-w-0 space-y-3">
      <p className="text-sm text-slate-400">
        Arbeitsbereiche für{' '}
        <span className="font-medium text-slate-200">TR-{tradeId.slice(0, 8).toUpperCase()}</span>
      </p>
      <ul className="flex flex-wrap gap-2">
        {areas
          .filter((area) => !cancelled || !area.activeOnly)
          .map((area) => {
            const sameView = area.view === view;
            // Preserve the exact search string for hash-only navigation. Reordering
            // parameters would unnecessarily trigger the existing pending-input guard.
            const href =
              sameView && sameQuery
                ? `${location.pathname}${location.search}${area.hash}`
                : tradeWorkspaceLink(area.view, tradeId, query, area.hash);
            const current =
              sameView &&
              (area.hash === location.hash ||
                view !== 'management' ||
                (!location.hash && area.hash === '#trade-overview') ||
                (location.hash === '#sale-capture' && area.hash === '#execution-dates') ||
                (location.hash === '#trade-management-state' && area.hash === '#trade-risk'));
            return (
              <li key={area.hash} className="min-w-0">
                <Link
                  to={href}
                  aria-current={current ? 'location' : undefined}
                  className={`inline-flex min-h-11 items-center rounded-lg border px-3 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-300 ${current ? 'border-sky-600 bg-sky-950 text-sky-200' : 'border-slate-700 text-slate-200 hover:border-sky-700'}`}
                >
                  {area.label}
                </Link>
              </li>
            );
          })}
      </ul>
      {showBackLinks && (
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
          <Link className="text-sky-400 underline" to="/workspace">
            Zur Positionsübersicht
          </Link>
          {reportContext && (
            <Link className="text-sky-400 underline" to={closedListUrl(reportContext)}>
              Zur ursprünglichen Abschlussauswahl
            </Link>
          )}
        </div>
      )}
    </nav>
  );
}
