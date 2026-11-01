import type { DetailRow, NoticeView } from '../../../shared/notices';
import type { RealizedGrossItem, RealizedGrossReport, RealizedGrossSource } from '../types/api';
import {
  parseRealizedContext,
  realizedContextQuery,
  realizedTradeLink,
  verifyRealizedReport,
  type RealizedReportContext,
} from './performanceReportContext';
import { executionTimeText, filterKey } from './presentation';

type CurrencyResolution = NonNullable<RealizedGrossSource['currency_resolution']>;

const currencyReasons = new Set(['CURRENCY_UNKNOWN', 'CURRENCY_CONFLICT', 'CURRENCY_MIXED']);
const reusedSources = new Set<CurrencyResolution['source']>([
  'PRIOR_BUYS',
  'REPLACED_EXECUTION',
  'EXECUTION_DOCUMENT',
  'HISTORICAL_LISTING',
  'HISTORICAL_LISTINGS',
]);

/** Provenance only: a known SELL currency does not qualify its BUY cost basis. */
export function currencyResolutionLabel(resolution: CurrencyResolution): string {
  if (resolution.source === 'MIXED') return 'keine eindeutige Währungszuordnung';
  if (resolution.source === 'CONFLICT') return 'widersprüchliche Währungsbelege';
  if (resolution.source === 'UNKNOWN' || resolution.currency_code === null) return 'unbekannt';
  const origins: Partial<Record<CurrencyResolution['source'], string>> = {
    USER_CONFIRMED: 'ausdrücklich bestätigt',
    PRIOR_BUYS: 'aus vorherigen Käufen übernommen',
    REPLACED_EXECUTION: 'aus ursprünglicher Buchung übernommen',
    EXECUTION_DOCUMENT: 'automatisch aus Ausführungsbeleg abgeleitet',
    HISTORICAL_LISTING: 'automatisch aus historischer Notierung abgeleitet',
    HISTORICAL_LISTINGS: 'automatisch aus historischen Notierungen abgeleitet',
  };
  return `${resolution.currency_code} · ${origins[resolution.source] ?? 'Herkunft nicht näher erläutert'}`;
}

const reasonExplanations: Readonly<Record<string, string>> = {
  NO_HISTORICAL_EVIDENCE:
    'Für diese Buchung liegt im gelesenen Quellenstand kein passender historischer Währungsbeleg vor.',
  EXECUTION_TIME_UNKNOWN:
    'Ausführungsdatum oder Zeitzone reichen nicht aus, passende historische Notierungen zuzuordnen.',
  LISTING_HISTORY_INCOMPLETE:
    'Die historischen Notierungsbelege reichen für eine eindeutige Währungszuordnung nicht aus.',
  DOCUMENT_CONFLICT: 'Die Ausführungsbelege widersprechen sich bei Währung oder Handelsplatz.',
  LISTING_CONFLICT:
    'Historische Notierungsbelege nennen für denselben Handelsplatz unterschiedliche Währungen.',
  MULTIPLE_LISTING_CURRENCIES:
    'Die historischen Handelsplätze weisen unterschiedliche Währungen aus; daraus ergibt sich keine eindeutige Ausführungswährung.',
  CORRECTION_SOURCE_REVIEW_REQUIRED:
    'Die früheren Quellen gehören zur ersetzten Buchung; für die Korrektur ist die Währungsherkunft nicht ausreichend belegt.',
  EVIDENCE_HISTORY_INVALID: 'Die Historie der Währungsbelege ist widersprüchlich.',
};

interface SourceEntry {
  executionId: string;
  label: string;
  source: RealizedGrossSource | null;
  problem: string | null;
  /** Local join rule, not a replacement domain status or a translated text key. */
  problemRule: string | null;
}

/** Join owner-provided identities, without inferring a new financial qualification. */
function requiredSources(item: RealizedGrossItem, report: RealizedGrossReport): SourceEntry[] {
  const byId = new Map<string, RealizedGrossSource[]>();
  for (const source of report.sources) {
    const existing = byId.get(source.execution_id) ?? [];
    existing.push(source);
    byId.set(source.execution_id, existing);
  }
  const entries: SourceEntry[] = [];
  let buyNumber = 0;
  const ids = [...new Set([...item.cost_basis_execution_ids, item.execution_id])];
  for (const [index, executionId] of ids.entries()) {
    const selectedSale = executionId === item.execution_id;
    const label = selectedSale ? 'Verkauf' : `Buchung im Kostenbasispräfix ${index + 1}`;
    const matches = byId.get(executionId) ?? [];
    let problem: string | null = null;
    let problemRule: string | null = null;
    const source = matches.length === 1 ? matches[0] : null;
    if (!matches.length) {
      problemRule = 'missing-source';
      problem =
        'Diese Buchungsquelle fehlt in der Berichtsantwort; ihre Währungsherkunft ist hier nicht zuordenbar.';
    } else if (!source) {
      problemRule = 'nonunique-source';
      problem =
        'Diese Buchungsquelle ist in der Berichtsantwort nicht eindeutig; ihre Währungsherkunft wird nicht zugeordnet.';
    } else if (source.trade_id !== item.trade_id || source.product_id !== item.product_id) {
      problemRule = 'source-scope-mismatch';
      problem = 'Die gelieferte Buchungsquelle gehört nicht zum Trade und Produkt dieses Beitrags.';
    } else if (!source.is_effective || source.superseded_by_execution_id !== null) {
      problemRule = 'source-not-effective';
      problem =
        'Die gelieferte Buchungsquelle ist historisch ersetzt; sie belegt keine zusätzliche wirksame Kaufkostenbasis.';
    } else if (selectedSale && source.side !== 'SELL') {
      problemRule = 'selected-source-not-sell';
      problem =
        'Die gelieferte Buchungsquelle ist kein Verkauf; sie wird diesem Verkaufsbeitrag nicht als Währungsbeleg zugeordnet.';
    } else if (!selectedSale && source.side === 'SELL') {
      // Earlier SELLs explain the position history, not the currencies of BUY costs.
      continue;
    } else if (!selectedSale && source.side !== 'BUY') {
      problemRule = 'prefix-source-not-buy';
      problem =
        'Die Buchungsseite ist nicht als Kauf belegt; sie wird der Kaufkostenbasis nicht zugeordnet.';
    }
    entries.push({
      executionId,
      label: problem || selectedSale ? label : `Kauf ${++buyNumber}`,
      source: problem ? null : source,
      problem,
      problemRule,
    });
  }
  return entries;
}

function unresolved(entry: SourceEntry): boolean {
  const resolution = entry.source?.currency_resolution;
  return (
    !resolution ||
    resolution.currency_code === null ||
    (!reusedSources.has(resolution.source) && resolution.source !== 'USER_CONFIRMED')
  );
}

function sourceIdentity(entry: SourceEntry): unknown {
  const resolution = entry.source?.currency_resolution;
  if (!resolution) return [entry.executionId, entry.problemRule ?? 'resolution-not-supplied'];
  // An unresolved inherited prefix can list known confirmations as context.
  // Those links alone do not identify the missing BUY cause; the actual
  // unresolved BUY entries remain separate identities in this item's card.
  const unresolvedPrefix =
    resolution.source === 'UNKNOWN' &&
    !resolution.reason &&
    !resolution.evidence_ids?.length &&
    !resolution.evidence?.length;
  return [
    entry.executionId,
    resolution.source,
    resolution.currency_code,
    resolution.reason ?? null,
    resolution.resolver_version ?? null,
    unresolvedPrefix ? [] : [...resolution.source_execution_ids].sort(),
    unresolvedPrefix ? [] : [...resolution.confirmation_ids].sort(),
    [...(resolution.evidence_ids ?? [])].sort(),
    [...(resolution.evidence ?? [])]
      .map((evidence) => [
        evidence.id,
        evidence.source_fingerprint ?? null,
        evidence.valid_from ?? null,
        evidence.valid_to ?? null,
        evidence.supersedes_evidence_id ?? null,
      ])
      .sort((left, right) => String(left[0]).localeCompare(String(right[0]))),
  ];
}

function sourceDetails(entry: SourceEntry, report: RealizedGrossReport): DetailRow[] {
  if (!entry.source) {
    return [
      { label: `${entry.label} · Quellenzuordnung`, value: entry.problem! },
      { label: `${entry.label} · Originalbezug`, value: entry.executionId },
    ];
  }
  const source = entry.source;
  const resolution = source.currency_resolution;
  const rows: DetailRow[] = [
    {
      label: `${entry.label} · Ausführung`,
      value: executionTimeText(source, report.filters.report_timezone),
    },
    {
      label: `${entry.label} · Währungsherkunft`,
      value: resolution
        ? currencyResolutionLabel(resolution)
        : 'Die Berichtsantwort enthält keine Währungsauflösung für diese Buchung. Eine vorhandene Bestätigung wird hier nicht zu einer Auflösung ergänzt.',
    },
    {
      label: `${entry.label} · Originalbezug`,
      value: `Buchung ${source.execution_id} · Trade ${source.trade_id} · Produkt ${source.product_id} · ${source.side} · wirksam`,
    },
  ];
  if (!resolution) return rows;
  if (resolution.reason) {
    rows.push({
      label: `${entry.label} · Ursache`,
      value:
        reasonExplanations[resolution.reason] ??
        'Der zuständige Fachbereich liefert einen hier noch nicht näher erläuterten Grund. Aus diesem Code wird keine zusätzliche Ursache abgeleitet.',
    });
  }
  rows.push({
    label: `${entry.label} · Originalauflösung`,
    value: [resolution.source, resolution.reason, resolution.resolver_version]
      .filter(Boolean)
      .join(' · '),
  });
  for (const [label, ids] of [
    ['Verwendete Buchungen', resolution.source_execution_ids],
    ['Verwendete Bestätigungen', resolution.confirmation_ids],
    ['Verwendete Belegversionen', resolution.evidence_ids ?? []],
  ] as const) {
    if (ids.length) rows.push({ label: `${entry.label} · ${label}`, value: ids.join(', ') });
  }
  for (const evidence of resolution.evidence ?? []) {
    rows.push({
      label: `${entry.label} · Belegquelle`,
      value: `${evidence.source_reference} · Belegversion ${evidence.id}${evidence.source_fingerprint ? ` · Fingerprint ${evidence.source_fingerprint}` : ''}`,
    });
    if (evidence.valid_from || evidence.valid_to) {
      rows.push({
        label: `${entry.label} · Beleggültigkeit`,
        value: `${evidence.valid_from ?? 'Beginn nicht angegeben'} bis ausschließlich ${evidence.valid_to ?? 'Ende nicht angegeben'}`,
      });
    }
  }
  return rows;
}

/** Only the owner's summary qualifies the selected sum, never a source reason. */
const summaryImpact: Readonly<Record<RealizedGrossReport['summary']['status'], string>> = {
  EMPTY: 'Der Bericht enthält keine passenden Verkaufsbeiträge.',
  COMPLETE: 'Der Bericht weist die gewählte Summe als vollständig berechenbar aus.',
  PARTIAL:
    'Der Bericht ist teilweise berechenbar. Die ausgewiesene Teilsumme ist keine vollständige Summe.',
  NOT_COMPUTABLE: 'Der Bericht weist die gewählte Summe als nicht berechenbar aus.',
};

/**
 * Read-only explanation of one item from one already accepted report response.
 * The host owns request generations. This adapter neither resolves currencies nor
 * recalculates amounts, promotes confirmations, or tracks recovery across reads.
 */
export function buildRealizedCurrencyNotice(
  item: RealizedGrossItem,
  report: RealizedGrossReport,
  context: RealizedReportContext,
): NoticeView | null {
  if (
    !report.items.includes(item) ||
    report.items.filter((candidate) => candidate.execution_id === item.execution_id).length !== 1 ||
    !item.execution_id ||
    !item.trade_id ||
    !item.product_id ||
    context.basis !== report.basis.id
  )
    return null;
  try {
    verifyRealizedReport(report, context.filters);
    if (!parseRealizedContext(realizedContextQuery(context)).context) return null;
  } catch {
    return null;
  }

  const entries = requiredSources(item, report);
  const reasons = [...new Set(item.reasons.filter((reason) => currencyReasons.has(reason)))];
  const currencyPreventsContribution = item.status === 'NOT_COMPUTABLE' && reasons.length > 0;
  const unavailable = entries.some(unresolved);
  const explanations: Record<string, string> = {
    CURRENCY_UNKNOWN:
      'Für den Verkauf oder seine benötigten Käufe ist die Ausführungswährung nicht vollständig belegt.',
    CURRENCY_CONFLICT:
      'Währungsbelege des Verkaufs oder seiner benötigten Käufe widersprechen sich.',
    CURRENCY_MIXED:
      'Der Bericht weist für Verkauf und Kaufkostenbasis keine einheitliche Währungszuordnung aus.',
  };
  const subject = `${item.product_name?.trim() || 'Produktname nicht verfügbar'} · Verkauf ${executionTimeText(item, report.filters.report_timezone)}.`;
  const cause = reasons.length
    ? `${subject} ${reasons.map((reason) => explanations[reason]).join(' ')}`
    : unavailable
      ? `${subject} Die Berichtsantwort liefert nicht für alle benötigten Buchungen eine eindeutig zuordenbare Währungsherkunft. Der ausgewiesene Beitragsstatus bleibt maßgeblich.`
      : `${subject} Die Währungsherkunft des Verkaufs und seiner benötigten Käufe ist in dieser Berichtsantwort belegt.`;

  let impact: string;
  if (item.status === 'EXCLUDED') {
    const exclusion = [
      item.reasons.includes('OUTSIDE_PERIOD') ? 'Er liegt außerhalb des gewählten Zeitraums.' : '',
      item.reasons.includes('OTHER_CURRENCY')
        ? 'Seine belegte Verkaufswährung liegt außerhalb der Währungsauswahl.'
        : '',
    ]
      .filter(Boolean)
      .join(' ');
    impact = `Dieser Verkauf ist von der gewählten Berichtssumme ausgeschlossen.${exclusion ? ` ${exclusion}` : ''} Ein zusätzlicher Währungsbefund blockiert die gewählte Summe nicht.`;
  } else if (currencyPreventsContribution) {
    impact =
      'Der Bericht kann den Bruttobeitrag dieses Verkaufs derzeit nicht berechnen. Andere Beiträge behalten ihre eigene ausgewiesene Qualifikation.';
  } else if (item.status === 'NOT_COMPUTABLE') {
    impact =
      'Der Bericht weist diesen Beitrag als nicht berechenbar aus. Eine nähere Währungsursache kann diese Ansicht aus den gelieferten Gründen nicht erläutern.';
  } else {
    impact =
      'Der Bericht weist diesen Bruttobeitrag als verwendbar aus. Der angezeigte Betrag wird unverändert übernommen.';
  }

  const hasAutomaticOrigin = entries.some((entry) => {
    const resolution = entry.source?.currency_resolution;
    return resolution && resolution.currency_code !== null && reusedSources.has(resolution.source);
  });
  // Preserve independent sources; this is one card, not a merged root cause.
  const causalEntries =
    reasons.includes('CURRENCY_MIXED') || !reasons.length ? entries : entries.filter(unresolved);
  const identityEntries = causalEntries.length ? causalEntries : entries;
  const details: DetailRow[] = [
    { label: 'Originalbefund des Beitrags', value: [item.status, ...item.reasons].join(' · ') },
    { label: 'Originalqualifikation der Summe', value: report.summary.status },
    {
      label: 'Berichtsauswahl',
      value: `${report.filters.from_date} bis ${report.filters.to_date} · ${report.filters.report_currency} · ${report.filters.report_timezone}`,
    },
    { label: 'Berichtsstand', value: report.basis.id },
    {
      label: 'Bericht gelesen',
      value: `${report.basis.read_started_at} bis ${report.basis.read_completed_at}`,
    },
    { label: 'Bericht berechnet', value: report.basis.calculated_at },
    {
      label: 'Zeitbezug',
      value:
        'Lese- und Berechnungszeiten sind keine Ausführungs- oder Quellenprüfzeiten und belegen keine Behebung eines früheren Befunds.',
    },
    {
      label: 'Herkunftsbezug',
      value:
        'Die wirksamen Käufe im gelieferten Kostenbasispräfix und dieser Verkauf werden einzeln zugeordnet. Frühere Verkäufe belegen die Bestandsentwicklung; spätere und historisch ersetzte Buchungen bleiben Kontext. Diese gemeinsame Darstellung belegt keine gemeinsame Ursache.',
    },
    ...entries.flatMap((entry) => sourceDetails(entry, report)),
  ];
  return {
    id: `realized-currency:${JSON.stringify([
      report.definition_version,
      filterKey(report.filters),
      item.trade_id,
      item.product_id,
      item.execution_id,
      [...reasons].sort(),
      identityEntries
        .map(sourceIdentity)
        .sort((left, right) => JSON.stringify(left).localeCompare(JSON.stringify(right))),
    ])}`,
    title: currencyPreventsContribution
      ? 'Währungsherkunft dieses Beitrags ungeklärt'
      : 'Währungsherkunft dieses Beitrags',
    presentation: currencyPreventsContribution ? 'warning' : 'information',
    cause,
    impact: `${impact} ${summaryImpact[report.summary.status]}`,
    automatic: hasAutomaticOrigin
      ? 'Bereits belegte Währungszuordnungen werden aus vorhandenen Quellen übernommen. Für diese Zuordnungen ist keine erneute Bestätigung nötig.'
      : currencyPreventsContribution
        ? 'Die gelesene Antwort belegt keine automatische Klärung dieser Währungslücke.'
        : '',
    userNeed: 'Buchungen und Belege bei Bedarf im Trade prüfen.',
    details,
    action: {
      label: 'Buchungen und Währungsbestätigungen im Trade prüfen',
      href: realizedTradeLink(item.trade_id, context),
    },
  };
}
