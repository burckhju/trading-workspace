import { closedListUrl, parseClosedContext } from './closedReportNavigation';
import { parseRealizedContext, realizedListUrl } from './realizedReportNavigation';

/** A return destination preserves report selection, never monetary or source evidence. */
export function reportReturnLink(query: URLSearchParams): { href: string; label: string } | null {
  if (query.get('report_context') === 'closed-trades') {
    const { context } = parseClosedContext(query);
    return context
      ? { href: closedListUrl(context), label: 'Zur ursprünglichen Abschlussauswahl' }
      : null;
  }
  if (query.get('report_context') === 'realized-gross') {
    const { context } = parseRealizedContext(query);
    return context
      ? { href: realizedListUrl(context), label: 'Zur ursprünglichen Verkaufsauswahl' }
      : null;
  }
  return null;
}
