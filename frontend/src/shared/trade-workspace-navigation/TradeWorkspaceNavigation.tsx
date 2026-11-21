import { useEffect } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';

import { closedContextKeys, pinKeys } from './context';
import { tradeWorkspaceLink, type TradeWorkspaceView } from './links';
import { reportReturnLink } from './reportReturn';
import { tradeManagementArea } from './managementArea';

const areas: { label: string; view: TradeWorkspaceView; hash: string; activeOnly?: boolean }[] = [
  { label: 'Überblick', view: 'management', hash: '#trade-overview' },
  {
    label: 'Kursverlauf',
    view: 'management',
    hash: '#position-price-history',
    activeOnly: true,
  },
  { label: 'Buchungen', view: 'management', hash: '#execution-dates' },
  { label: 'Überwachung', view: 'management', hash: '#trade-risk', activeOnly: true },
  { label: 'Bearbeiten', view: 'management', hash: '#trade-management-state' },
  { label: 'Plan und Belege', view: 'sources', hash: '#trade-plan-sources' },
];
const anchors = new Set([
  ...areas.map((area) => area.hash),
  '#sale-capture',
  '#trade-management-state',
  '#trade-journal-sources',
  '#trade-review-sources',
  '#trade-evidence-sources',
  '#trade-monitoring',
  '#trade-cancellation',
  '#additional-purchase',
  '#post-trade-review',
  '#trade-review',
  '#trade-journal',
  '#trade-lessons',
]);

/** Links keep existing owners mounted; a section change never creates a new draft or read. */
export function TradeWorkspaceNavigation({
  tradeId,
  view,
  cancelled = false,
  showBackLinks = true,
  showObjectLinks = true,
}: {
  tradeId: string;
  view: TradeWorkspaceView;
  cancelled?: boolean;
  showBackLinks?: boolean;
  showObjectLinks?: boolean;
}) {
  const location = useLocation();
  const [query] = useSearchParams();
  const reportReturn = reportReturnLink(query);
  const allowedKeys = new Set<string>(['trade_id', 'view', ...pinKeys, ...closedContextKeys]);
  const sameQuery = [...query.keys()].every((key) => allowedKeys.has(key));
  const hrefFor = (targetView: TradeWorkspaceView, hash: string) =>
    targetView === view && sameQuery
      ? `${location.pathname}${location.search}${hash}`
      : tradeWorkspaceLink(targetView, tradeId, query, hash);
  useEffect(() => {
    if (!anchors.has(location.hash)) return;
    const target = document.getElementById(
      location.hash === '#trade-monitoring' ? 'trade-risk' : location.hash.slice(1),
    );
    target?.scrollIntoView?.({ block: 'start' });
    target?.focus({ preventScroll: true });
  }, [location.hash, location.key]);

  return (
    <nav aria-label="Trade-Arbeitsbereiche" className="min-w-0 space-y-3">
      <p className="text-sm text-slate-400">
        Arbeitsbereiche für{' '}
        <span className="font-medium text-slate-200">TR-{tradeId.slice(0, 8).toUpperCase()}</span>
      </p>
      {showObjectLinks && (
        <ul className="flex flex-wrap gap-2">
          {areas
            .filter((area) => !cancelled || !area.activeOnly)
            .map((area) => {
              const sameView = area.view === view;
              // Preserve the exact search string for hash-only navigation. Reordering
              // parameters would unnecessarily trigger the existing pending-input guard.
              const cancellation = cancelled && area.hash === '#trade-management-state';
              const href = hrefFor(area.view, cancellation ? '#trade-cancellation' : area.hash);
              const current =
                sameView &&
                (area.hash === location.hash ||
                  view === 'sources' ||
                  (!location.hash && area.hash === '#trade-overview') ||
                  (view === 'management' &&
                    tradeManagementArea(location.hash) === tradeManagementArea(area.hash)));
              return (
                <li key={area.hash} className="min-w-0">
                  <Link
                    to={href}
                    aria-current={current ? 'location' : undefined}
                    className={`inline-flex min-h-11 items-center rounded-lg border px-3 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-300 ${current ? 'border-sky-600 bg-sky-950 text-sky-200' : 'border-slate-700 text-slate-200 hover:border-sky-700'}`}
                  >
                    {cancellation ? 'Stornierung' : area.label}
                  </Link>
                </li>
              );
            })}
        </ul>
      )}
      {showObjectLinks ? (
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
          <Link
            className="rounded text-sky-300 underline focus-visible:outline-2 focus-visible:outline-sky-300"
            to={hrefFor('journal', '#post-trade-review')}
            aria-current={
              view === 'journal' && location.hash !== '#trade-journal' ? 'location' : undefined
            }
          >
            Nachbereitung
          </Link>
          <Link
            className="rounded text-sky-300 underline focus-visible:outline-2 focus-visible:outline-sky-300"
            to={hrefFor('journal', '#trade-journal')}
            aria-current={
              view === 'journal' && location.hash === '#trade-journal' ? 'location' : undefined
            }
          >
            Journal
          </Link>
        </div>
      ) : (
        <Link
          className="inline-block rounded text-sm text-sky-300 underline focus-visible:outline-2 focus-visible:outline-sky-300"
          to={hrefFor('sources', '#trade-plan-sources')}
        >
          Plan und Belege
        </Link>
      )}
      {showBackLinks && (
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
          <Link className="text-sky-400 underline" to="/workspace">
            Zur Positionsübersicht
          </Link>
          {reportReturn && (
            <Link className="text-sky-400 underline" to={reportReturn.href}>
              {reportReturn.label}
            </Link>
          )}
        </div>
      )}
    </nav>
  );
}
