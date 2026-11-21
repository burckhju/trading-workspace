import { describe, expect, it } from 'vitest';
import { currentNavigation, navigationGroups } from './navigation';

describe('canonical task homes', () => {
  it.each([
    ['/', 'today'],
    ['/aktuelles', 'today'],
    ['/workspace', 'positions'],
    ['/executions', 'executions'],
    ['/trade-management?trade_id=a#trade-risk', 'positions'],
    ['/trade-management?trade_id=a#sale-capture', 'executions'],
    ['/trade-management?trade_id=a#additional-purchase', 'executions'],
    ['/trade-management?trade_id=a#execution-dates', 'executions'],
    ['/performance', 'performance'],
    ['/performance/realized-gross', 'performance'],
    ['/performance/closed-trades', 'closed'],
    ['/market-charts?underlying=a', 'markets'],
    ['/market-analyses', 'analyses'],
    ['/market-analyses/setup', 'analyses'],
    ['/market-analyses/123', 'analyses'],
    ['/candidates', 'ideas'],
    ['/trade-plans', 'plans'],
    ['/trade-plans/overview', 'plans'],
    ['/product-selection?run_id=exact#selection', 'selection'],
    ['/product-selection?run_id=exact#purchase', 'executions'],
    ['/learning', 'review'],
    ['/journal', 'journal'],
    ['/post-trade?trade_id=a#post-trade-review', 'review'],
    ['/post-trade?trade_id=a#trade-journal', 'journal'],
    ['/post-trade?trade_id=a&tab=reflection', 'journal'],
    ['/post-trade?trade_id=a&journal_version_id=historical', 'journal'],
    ['/post-trade?trade_id=a#trade-lessons', 'lessons'],
    ['/lessons', 'lessons'],
    ['/lessons/a?lesson_version_id=exact#model-improvement', 'models'],
    ['/lessons/a?lesson_version_id=exact', 'lessons'],
    ['/model-improvements', 'models'],
    ['/learning-imports', 'imports'],
    ['/underlyings', 'underlyings'],
    ['/underlyings/new', 'underlyings'],
    ['/underlyings/a/edit', 'underlyings'],
    ['/warrants-admin', 'products'],
    ['/issuers-admin', 'issuers'],
    ['/trading-venues-admin', 'venues'],
    ['/currencies-admin', 'currencies'],
    ['/top-down-admin', 'references'],
    ['/data-sources', 'data'],
    ['/chart-setup', 'references'],
  ])('keeps %s in %s without changing the URL', (href, expected) => {
    const url = new URL(href, 'https://workspace.test');
    expect(currentNavigation(url.pathname, url.search, url.hash)?.item.id).toBe(expected);
    expect(url.href).toBe(`https://workspace.test${href}`);
  });
  it('has no duplicate item homes and does not invent an unknown route home', () => {
    const ids = navigationGroups.flatMap((group) => group.items.map((item) => item.id));
    expect(new Set(ids).size).toBe(ids.length);
    expect(currentNavigation('/unbekannt')).toBeNull();
  });
});
