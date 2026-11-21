export interface NavigationItem {
  id: string;
  label: string;
  to: string;
}

export interface NavigationGroup {
  id: string;
  label: string;
  question: string;
  to: string;
  items: NavigationItem[];
}

export const navigationGroups: NavigationGroup[] = [
  {
    id: 'today',
    label: 'Aktuelles',
    question: 'Was erfordert jetzt meine Aufmerksamkeit?',
    to: '/',
    items: [{ id: 'today', label: 'Heute', to: '/' }],
  },
  {
    id: 'portfolio',
    label: 'Depot',
    question: 'Welche Positionen und Trades habe ich?',
    to: '/workspace',
    items: [
      { id: 'positions', label: 'Offene Positionen', to: '/workspace' },
      { id: 'executions', label: 'Ausführungen', to: '/executions' },
      { id: 'closed', label: 'Vollabschlüsse im Zeitraum', to: '/performance/closed-trades' },
      { id: 'performance', label: 'Performance', to: '/performance/realized-gross' },
    ],
  },
  {
    id: 'analysis',
    label: 'Marktanalyse',
    question: 'Welche Märkte und Handelsideen untersuche ich?',
    to: '/market-charts',
    items: [
      { id: 'markets', label: 'Marktüberblick', to: '/market-charts' },
      { id: 'analyses', label: 'Analysen', to: '/market-analyses' },
      { id: 'ideas', label: 'Handelsideen', to: '/candidates' },
      { id: 'plans', label: 'Tradepläne', to: '/trade-plans/overview' },
      { id: 'selection', label: 'Produktauswahl', to: '/product-selection' },
    ],
  },
  {
    id: 'learning',
    label: 'Lessons Learned',
    question: 'Was lerne ich aus meinen Entscheidungen?',
    to: '/learning',
    items: [
      { id: 'review', label: 'Nachbeobachtung & Exit Review', to: '/learning' },
      { id: 'journal', label: 'Journal', to: '/journal' },
      { id: 'lessons', label: 'Erkenntnisse', to: '/lessons' },
      { id: 'models', label: 'Modellverbesserung', to: '/model-improvements' },
      { id: 'imports', label: 'Lernimporte', to: '/learning-imports' },
    ],
  },
  {
    id: 'reference',
    label: 'Basisdaten',
    question: 'Welche Instrumente und Datenquellen bilden die Grundlage?',
    to: '/underlyings',
    items: [
      { id: 'underlyings', label: 'Basiswerte', to: '/underlyings' },
      { id: 'products', label: 'Optionsscheine', to: '/warrants-admin' },
      { id: 'issuers', label: 'Emittenten', to: '/issuers-admin' },
      { id: 'venues', label: 'Handelsplätze', to: '/trading-venues-admin' },
      { id: 'currencies', label: 'Währungen', to: '/currencies-admin' },
      { id: 'references', label: 'Markt- und Sektorzuordnungen', to: '/chart-setup' },
      { id: 'data', label: 'Datenquellen & Diagnose', to: '/data-sources' },
    ],
  },
];

function navigationItemId(pathname: string, search: string, hash: string): string | null {
  if (pathname === '/' || pathname === '/aktuelles') return 'today';
  if (pathname === '/workspace') return 'positions';
  if (pathname === '/executions') return 'executions';
  if (pathname === '/trade-management') {
    return ['#execution-dates', '#sale-capture', '#additional-purchase'].includes(hash)
      ? 'executions'
      : 'positions';
  }
  if (pathname === '/performance/closed-trades') return 'closed';
  if (pathname.startsWith('/performance')) return 'performance';
  if (pathname === '/market-charts') return 'markets';
  if (pathname.startsWith('/market-analyses')) return 'analyses';
  if (pathname === '/candidates') return 'ideas';
  if (pathname.startsWith('/trade-plans')) return 'plans';
  if (pathname === '/product-selection') return hash === '#purchase' ? 'executions' : 'selection';
  if (pathname === '/post-trade') {
    if (hash === '#trade-lessons') return 'lessons';
    if (
      hash === '#trade-journal' ||
      (!hash &&
        (new URLSearchParams(search).has('journal_version_id') ||
          new URLSearchParams(search).get('tab') === 'reflection'))
    )
      return 'journal';
    return 'review';
  }
  if (pathname === '/learning') return 'review';
  if (pathname === '/journal') return 'journal';
  if (pathname.startsWith('/lessons')) return hash === '#model-improvement' ? 'models' : 'lessons';
  if (pathname === '/model-improvements') return 'models';
  if (pathname === '/learning-imports') return 'imports';
  if (pathname.startsWith('/underlyings')) return 'underlyings';
  if (pathname === '/warrants-admin') return 'products';
  if (pathname === '/issuers-admin') return 'issuers';
  if (pathname === '/trading-venues-admin') return 'venues';
  if (pathname === '/currencies-admin') return 'currencies';
  if (pathname === '/top-down-admin' || pathname === '/chart-setup') return 'references';
  if (pathname === '/data-sources') return 'data';
  return null;
}

/** Location presentation only. Financial pins and return parameters stay untouched. */
export function currentNavigation(pathname: string, search = '', hash = '') {
  const id = navigationItemId(pathname, search, hash);
  for (const group of navigationGroups) {
    const item = group.items.find((entry) => entry.id === id);
    if (item) return { group, item };
  }
  return null;
}
