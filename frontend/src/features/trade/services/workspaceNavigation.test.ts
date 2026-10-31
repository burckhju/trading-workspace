import { describe, expect, it } from 'vitest';

import {
  closedContextQuery,
  parseClosedContext,
  type ClosedReportContext,
} from '../../performance/services/closedReportContext';
import { sourceQueryError } from './sourceView';
import {
  lessonTradeReturnLink,
  tradeLessonLink,
  tradeWorkspaceLink,
  type TradeWorkspaceView,
} from './workspaceNavigation';

const tradeId = '10000000-0000-4000-8000-000000000001';
const reviewId = '20000000-0000-4000-8000-000000000001';
const journalId = '30000000-0000-4000-8000-000000000001';
const lessonId = '40000000-0000-4000-8000-000000000001';
const lessonVersionId = '50000000-0000-4000-8000-000000000001';
const report: ClosedReportContext = {
  filters: {
    from_date: '2026-10-01',
    to_date: '2026-10-31',
    report_currency: 'EUR',
    report_timezone: 'Europe/Vienna',
  },
  view: 'qualified',
  page: 2,
  basis: 'a'.repeat(64),
};
const localUrl = (href: string) => new URL(href, 'http://workspace.test');
function historicalContext() {
  const query = closedContextQuery(report);
  query.set('trade_id', tradeId);
  query.set('review_version_id', reviewId);
  query.set('journal_version_id', journalId);
  return query;
}

describe('trade workspace navigation context', () => {
  it('retains the selected trade, historical versions and original report through every owner', () => {
    let query = historicalContext();
    const destinations: [TradeWorkspaceView, string, string][] = [
      ['sources', '/trade-management', '#trade-plan-sources'],
      ['journal', '/post-trade', '#trade-journal'],
      ['management', '/trade-management', '#execution-dates'],
    ];
    for (const [view, pathname, hash] of destinations) {
      const destination = localUrl(tradeWorkspaceLink(view, tradeId, query, hash));
      expect(destination.pathname).toBe(pathname);
      expect(destination.hash).toBe(hash);
      expect(destination.searchParams.getAll('trade_id')).toEqual([tradeId]);
      expect(destination.searchParams.getAll('review_version_id')).toEqual([reviewId]);
      expect(destination.searchParams.getAll('journal_version_id')).toEqual([journalId]);
      expect(destination.searchParams.get('view')).toBe(view === 'sources' ? 'sources' : null);
      expect(parseClosedContext(destination.searchParams)).toEqual({
        context: report,
        error: null,
      });
      expect(sourceQueryError(destination.searchParams)).toBeNull();
      query = destination.searchParams;
    }
  });

  it('carries only navigation evidence and leaves the caller query unchanged', () => {
    const query = historicalContext();
    const unrelated: Record<string, string> = {
      returnTo: 'https://elsewhere.invalid/?returnTo=%2F%2Felsewhere.invalid',
      redirect: '//elsewhere.invalid',
      amount: '999999',
      realized_gross_pnl: '999999',
      workspace_id: 'another-workspace',
      trade_plan_version_id: 'a-current-version-is-not-a-historical-binding',
      lesson_version_id: lessonVersionId,
      trade_return_view: 'sources',
      action: 'sell',
    };
    for (const [key, value] of Object.entries(unrelated)) query.set(key, value);
    const original = query.toString();
    for (const view of ['management', 'sources', 'journal'] as const) {
      const destination = localUrl(tradeWorkspaceLink(view, tradeId, query));
      expect(destination.origin).toBe('http://workspace.test');
      for (const key of Object.keys(unrelated))
        expect(destination.searchParams.has(key)).toBe(false);
      expect(parseClosedContext(destination.searchParams).context).toEqual(report);
    }
    expect(query.toString()).toBe(original);
  });

  it.each(['review_version_id', 'journal_version_id'])(
    'keeps duplicate or invalid %s invalid instead of silently selecting a different history',
    (key) => {
      for (const values of [[reviewId, journalId], [''], ['not-a-version']]) {
        const query = historicalContext();
        query.delete(key);
        values.forEach((value) => query.append(key, value));
        expect(sourceQueryError(query)).not.toBeNull();
        for (const view of ['management', 'sources', 'journal'] as const) {
          const next = localUrl(tradeWorkspaceLink(view, tradeId, query)).searchParams;
          expect(next.getAll(key)).toEqual(values);
          expect(sourceQueryError(next)).not.toBeNull();
        }
      }
    },
  );

  it('preserves invalid and incomplete report context as invalid across owners and Lessons', () => {
    const duplicate = historicalContext();
    duplicate.append('report_page', '7');
    const incomplete = new URLSearchParams({
      report_context: 'closed-trades',
      from_date: 'invalid',
    });
    for (const query of [duplicate, incomplete]) {
      expect(parseClosedContext(query).error).not.toBeNull();
      for (const href of [
        tradeWorkspaceLink('sources', tradeId, query),
        tradeWorkspaceLink('journal', tradeId, query),
        tradeLessonLink(lessonId, lessonVersionId, tradeId, query),
      ]) {
        const next = localUrl(href).searchParams;
        expect(next.getAll('report_page')).toEqual(query.getAll('report_page'));
        expect(next.getAll('from_date')).toEqual(query.getAll('from_date'));
        expect(parseClosedContext(next)).toEqual({ context: null, error: expect.any(String) });
      }
    }
  });

  it('does not invent a report, source version or sources view for an ordinary trade entry', () => {
    const url = localUrl(tradeWorkspaceLink('management', tradeId, new URLSearchParams()));
    expect([...url.searchParams.entries()]).toEqual([['trade_id', tradeId]]);
    expect(url.hash).toBe('');
    expect(parseClosedContext(url.searchParams)).toEqual({ context: null, error: null });
  });
});

describe('Lesson context and return navigation', () => {
  it.each(['sources', 'journal'] as const)(
    'opens the exact Lesson version and returns to the original %s owner and historical pins',
    (owner) => {
      const query = historicalContext();
      query.set('lesson_version_id', 'do-not-reuse-this-version');
      query.set('returnTo', 'https://elsewhere.invalid');
      const lesson = localUrl(tradeLessonLink(lessonId, lessonVersionId, tradeId, query, owner));
      expect(lesson.pathname).toBe(`/lessons/${lessonId}`);
      expect(lesson.hash).toBe('#lesson-history');
      expect(lesson.searchParams.getAll('lesson_version_id')).toEqual([lessonVersionId]);
      expect(lesson.searchParams.get('trade_return_view')).toBe(owner);
      expect(lesson.searchParams.has('returnTo')).toBe(false);

      const returnHref = lessonTradeReturnLink(lesson.searchParams);
      expect(returnHref).not.toBeNull();
      const destination = localUrl(returnHref!);
      expect(destination.pathname).toBe(owner === 'sources' ? '/trade-management' : '/post-trade');
      expect(destination.hash).toBe(
        owner === 'sources' ? '#trade-evidence-sources' : '#trade-journal',
      );
      expect(destination.searchParams.get('view')).toBe(owner === 'sources' ? 'sources' : null);
      expect(destination.searchParams.get('trade_id')).toBe(tradeId);
      expect(destination.searchParams.get('review_version_id')).toBe(reviewId);
      expect(destination.searchParams.get('journal_version_id')).toBe(journalId);
      expect(destination.searchParams.has('lesson_version_id')).toBe(false);
      expect(destination.searchParams.has('trade_return_view')).toBe(false);
      expect(parseClosedContext(destination.searchParams).context).toEqual(report);
    },
  );

  it('keeps the default Journal return and does not manufacture a Lesson version', () => {
    const url = localUrl(tradeLessonLink(lessonId, null, tradeId, historicalContext()));
    expect(url.searchParams.has('lesson_version_id')).toBe(false);
    expect(url.searchParams.get('trade_return_view')).toBe('journal');
    expect(lessonTradeReturnLink(url.searchParams)).toContain('/post-trade?trade_id=');
  });

  it('preserves the contextless Lesson fallback and encodes a Lesson path identifier', () => {
    const query = historicalContext();
    query.set('returnTo', '/arbitrary-owner');
    const url = localUrl(tradeLessonLink('lesson/with space', lessonVersionId, '', query));
    expect(url.pathname).toBe('/lessons/lesson%2Fwith%20space');
    expect([...url.searchParams.entries()]).toEqual([['lesson_version_id', lessonVersionId]]);
    expect(lessonTradeReturnLink(url.searchParams)).toBeNull();
    expect(tradeLessonLink(lessonId, null, '', query)).toBe(`/lessons/${lessonId}#lesson-history`);
  });

  it.each([
    '',
    `trade_id=${tradeId}`,
    'trade_return_view=journal',
    'trade_id=&trade_return_view=journal',
    'trade_id=%20%20&trade_return_view=journal',
    `trade_id=${tradeId}&trade_return_view=management`,
    `trade_id=${tradeId}&trade_return_view=https%3A%2F%2Felsewhere.invalid`,
    `trade_id=${tradeId}&trade_id=${tradeId}&trade_return_view=journal`,
    `trade_id=${tradeId}&trade_return_view=journal&trade_return_view=sources`,
  ])('does not invent a trade return target for an absent or ambiguous context: %s', (search) => {
    expect(lessonTradeReturnLink(new URLSearchParams(search))).toBeNull();
  });

  it('retains historical source ambiguity on the return from a Lesson', () => {
    const query = historicalContext();
    query.append('journal_version_id', reviewId);
    const lesson = localUrl(tradeLessonLink(lessonId, lessonVersionId, tradeId, query, 'sources'));
    const destination = localUrl(lessonTradeReturnLink(lesson.searchParams)!);
    expect(destination.searchParams.getAll('journal_version_id')).toEqual([journalId, reviewId]);
    expect(sourceQueryError(destination.searchParams)).not.toBeNull();
  });
});
