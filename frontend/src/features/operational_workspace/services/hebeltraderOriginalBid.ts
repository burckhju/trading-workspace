import { environment } from '../../../services/environment';
import { MarketApiError, requestJson } from '../../market/services/http';
import { originalBidCheckKeys, type HebeltraderOriginalBidReport } from '../hebeltraderOriginalBid';

const protocolError =
  'Die Antwort lässt sich dieser Position und dem Vertrag für Original-Geldkurse nicht sicher zuordnen.';
const text = (value: unknown): value is string =>
  typeof value === 'string' && value.trim().length > 0;
const nullableText = (value: unknown) => value === null || typeof value === 'string';
const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(text);
const oneOf = (value: unknown, allowed: readonly string[]) =>
  typeof value === 'string' && allowed.includes(value);
const decimal = (value: unknown) =>
  typeof value === 'string' && /^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(value);
const nullableDecimal = (value: unknown) => value === null || decimal(value);
const clock = (value: unknown): value is string =>
  typeof value === 'string' &&
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value) &&
  Number.isFinite(Date.parse(value));
const nullableClock = (value: unknown) => value === null || clock(value);
const day = (value: unknown): value is string =>
  typeof value === 'string' &&
  /^\d{4}-\d{2}-\d{2}$/.test(value) &&
  Number.isFinite(Date.parse(value)) &&
  new Date(value).toISOString().slice(0, 10) === value;
const nullableDay = (value: unknown) => value === null || day(value);
const currency = (value: unknown) => typeof value === 'string' && /^[A-Z]{3}$/.test(value);
const hash = (value: unknown) => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const originalStatusClock = (value: unknown): value is string =>
  clock(value) &&
  /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.test(
    value,
  ) &&
  !value.endsWith('-00:00') &&
  day(value.slice(0, 10));

function requireValue(condition: unknown): asserts condition {
  if (!condition) throw new Error(protocolError);
}

function object(value: unknown): Record<string, unknown> {
  requireValue(typeof value === 'object' && value !== null && !Array.isArray(value));
  return value as Record<string, unknown>;
}

function verifyPeriod(value: unknown) {
  const period = object(value);
  requireValue(
    oneOf(period.status, [
      'COMPLETE',
      'INCOMPLETE',
      'MISSING',
      'UNSUITABLE',
      'LIMIT_EXCEEDED',
      'NOT_REQUESTED',
    ]) &&
      nullableDay(period.start_date) &&
      nullableDay(period.end_date) &&
      nullableText(period.fingerprint) &&
      Array.isArray(period.missing_dates) &&
      period.missing_dates.every(day),
  );
}

function verifyCalendar(
  value: unknown,
  kind: 'UNDERLYING' | 'WARRANT',
  instrument: unknown,
  evaluatedAt: unknown,
  workspace?: unknown,
) {
  const calendar = object(value);
  requireValue(
    calendar.instrument_kind === kind &&
      calendar.instrument_id === instrument &&
      text(calendar.workspace_id) &&
      (workspace === undefined || calendar.workspace_id === workspace) &&
      oneOf(calendar.status, ['AVAILABLE', 'MISSING', 'UNSUITABLE']) &&
      calendar.verification === 'MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION' &&
      calendar.operation_status === 'READ_ONLY' &&
      nullableText(calendar.revision_id) &&
      nullableText(calendar.calendar_id) &&
      nullableText(calendar.calendar_version) &&
      nullableDay(calendar.coverage_start) &&
      nullableDay(calendar.coverage_end) &&
      nullableClock(calendar.recorded_at) &&
      calendar.known_at === evaluatedAt &&
      clock(calendar.read_at),
  );
  if (calendar.binding !== null) {
    const binding = object(calendar.binding);
    requireValue(
      binding.instrument_kind === kind &&
        binding.instrument_id === instrument &&
        ['listing_id', 'trading_venue_id', 'venue_mic', 'timezone', 'market_segment'].every((key) =>
          text(binding[key]),
        ) &&
        day(binding.valid_from) &&
        day(binding.valid_through),
    );
  }
  if (calendar.source !== null) {
    const source = object(calendar.source);
    requireValue(
      hash(source.document_sha256) &&
        hash(source.manifest_sha256) &&
        ['publisher', 'reference', 'document_filename', 'review_reference'].every((key) =>
          text(source[key]),
        ) &&
        clock(source.reviewed_at) &&
        nullableClock(source.retrieved_at) &&
        nullableClock(source.published_at) &&
        nullableDay(source.published_on),
    );
  }
  requireValue(
    calendar.status !== 'AVAILABLE' ||
      (calendar.binding !== null && calendar.source !== null && text(calendar.revision_id)),
  );
  return calendar;
}

function verifySide(value: unknown) {
  if (value === null) return;
  const side = object(value);
  requireValue(
    decimal(side.price) &&
      clock(side.observed_at) &&
      text(side.original_time_text) &&
      text(side.source_field) &&
      side.time_basis === 'SEPARATE_SIDE_TIMESTAMP',
  );
}

const originalStatusFields = [
  'version',
  'source_contract',
  'source_reference',
  'generated_at',
  'isin',
  'venue_mic',
  'status',
  'original_status_text',
  'source_status_field',
  'observed_at',
  'original_time_text',
  'source_time_field',
  'time_basis',
  'temporal_meaning',
] as const;

function verifyOriginalStatus(
  value: unknown,
  quote: Record<string, unknown>,
  route: Record<string, unknown>,
) {
  const original = object(value);
  requireValue(
    original.version === 'original-market-status-evidence-v1' &&
      [
        'source_contract',
        'source_reference',
        'original_status_text',
        'source_status_field',
        'source_time_field',
      ].every((key) => text(original[key])) &&
      clock(original.generated_at) &&
      clock(original.observed_at) &&
      originalStatusClock(original.original_time_text) &&
      original.isin === quote.provider_symbol &&
      (quote.isin === null || original.isin === quote.isin) &&
      original.venue_mic === route.venue_mic &&
      original.venue_mic === quote.venue_mic &&
      original.status === quote.trading_status &&
      original.original_status_text === original.status &&
      oneOf(original.status, ['OPEN', 'CLOSED', 'SUSPENDED', 'UNKNOWN']) &&
      original.time_basis === 'SEPARATE_STATUS_TIMESTAMP' &&
      original.temporal_meaning === 'OBSERVED_AT_INSTANT',
  );
  if (quote.original_evidence !== null) {
    const envelope = object(quote.original_evidence);
    requireValue(
      ['source_contract', 'source_reference', 'generated_at'].every(
        (key) => original[key] === envelope[key],
      ),
    );
  }
  return original;
}

function verifySaved(
  value: unknown,
  positionId: string,
  productId: unknown,
  workspace: unknown,
  evaluatedAt: unknown,
) {
  const saved = object(value);
  requireValue(
    text(saved.reason) &&
      nullableText(saved.provider) &&
      nullableText(saved.identity_key) &&
      nullableClock(saved.retrieved_at) &&
      text(saved.refresh_status),
  );
  let route: Record<string, unknown> | null = null;
  if (saved.route !== null) {
    route = object(saved.route);
    requireValue(
      route.position_id === positionId &&
        route.warrant_id === productId &&
        route.workspace_id === workspace &&
        [
          'warrant_listing_id',
          'trading_venue_id',
          'venue_mic',
          'identity_key',
          'selection_id',
        ].every((key) => text(route?.[key])) &&
        currency(route.currency) &&
        clock(route.selected_at),
    );
  }
  if (saved.provenance !== null) {
    const provenance = object(saved.provenance);
    requireValue(
      provenance.read_at === evaluatedAt &&
        hash(provenance.raw_payload_fingerprint) &&
        nullableClock(provenance.retrieved_at) &&
        nullableText(provenance.quality_status) &&
        nullableText(provenance.reason_code) &&
        strings(provenance.warnings) &&
        provenance.stored_at === null &&
        provenance.stored_at_status === 'NOT_RECORDED_BY_LAST_SUCCESS_STORE' &&
        provenance.storage_kind === 'LAST_SUCCESS' &&
        provenance.mutable === true &&
        provenance.historical_read === false,
    );
  }
  if (saved.quote === null) return saved;
  const quote = object(saved.quote);
  requireValue(
    route !== null &&
      saved.provenance !== null &&
      quote.warrant_listing_id === route.warrant_listing_id &&
      quote.currency === route.currency &&
      saved.identity_key === route.identity_key &&
      currency(quote.currency) &&
      nullableDecimal(quote.bid) &&
      nullableDecimal(quote.ask) &&
      nullableClock(quote.observed_at) &&
      [
        'isin',
        'wkn',
        'source_mode',
        'trading_status',
        'quote_time_text',
        'quote_time_basis',
        'venue_mic',
      ].every((key) => nullableText(quote[key])) &&
      text(quote.provider_symbol) &&
      typeof quote.retained === 'boolean',
  );
  if (quote.original_evidence !== null) {
    const original = object(quote.original_evidence);
    requireValue(
      original.version === 'original-quote-evidence-v1' &&
        original.currency === quote.currency &&
        original.isin === quote.provider_symbol &&
        (quote.isin === null || original.isin === quote.isin) &&
        original.venue_mic === route.venue_mic &&
        text(original.source_contract) &&
        text(original.source_reference) &&
        clock(original.generated_at),
    );
    verifySide(original.bid);
    verifySide(original.ask);
  }
  if (quote.original_market_status != null) {
    verifyOriginalStatus(quote.original_market_status, quote, route);
  }
  return saved;
}

function verifyStatusPoint(
  value: unknown,
  eventAt: unknown,
  applicable: boolean,
  hasOriginal: boolean,
) {
  const point = object(value);
  requireValue(point.event_at === eventAt && nullableClock(point.event_at));
  if (!applicable) {
    requireValue(point.status === 'NOT_APPLICABLE' && point.relation === 'NOT_APPLICABLE');
  } else {
    requireValue(point.status === 'NOT_ASSESSABLE');
    requireValue(
      eventAt === null
        ? point.relation === 'NO_EVENT_TIME'
        : !hasOriginal
          ? point.relation === 'NO_ORIGINAL_STATUS_TIME'
          : oneOf(point.relation, ['BEFORE_SOURCE_POINT', 'AT_SOURCE_POINT', 'AFTER_SOURCE_POINT']),
    );
  }
}

function verifyLiveMarketStatus(
  value: unknown,
  report: Record<string, unknown>,
  saved: Record<string, unknown>,
  bid: Record<string, unknown>,
) {
  const live = object(value);
  const quote = saved.quote === null ? null : object(saved.quote);
  const applicable = report.position_state === 'OPEN';
  requireValue(
    live.definition_version === 'hebeltrader-live-market-status-v1' &&
      oneOf(live.status, ['MISSING', 'UNSUITABLE', 'NOT_APPLICABLE']) &&
      strings(live.reasons) &&
      live.evaluated_at === report.evaluated_at &&
      live.reported_status === (quote?.trading_status ?? null) &&
      (live.reported_status === null || text(live.reported_status)) &&
      live.evidence_scope === 'SAVED_QUOTE_LAST_SUCCESS_ONLY' &&
      live.source_qualification === 'NOT_INDEPENDENTLY_VERIFIED' &&
      live.newer_status_observations === 'NOT_OBSERVED_BY_SAVED_QUOTE_READER' &&
      live.status_validity_interval === 'NOT_ESTABLISHED',
  );
  if (live.original_evidence === null) {
    requireValue(quote?.original_market_status == null);
  } else {
    requireValue(quote !== null);
    const route = object(saved.route);
    const original = verifyOriginalStatus(live.original_evidence, quote, route);
    const savedOriginal = object(quote.original_market_status);
    requireValue(originalStatusFields.every((key) => original[key] === savedOriginal[key]));
  }
  verifyStatusPoint(live.at_bid, bid.original_bid_at, applicable, live.original_evidence !== null);
  verifyStatusPoint(live.at_read, report.evaluated_at, applicable, live.original_evidence !== null);
  requireValue(
    applicable
      ? live.status !== 'NOT_APPLICABLE' &&
          (live.status !== 'UNSUITABLE' || report.coverage_status === 'UNSUITABLE')
      : live.status === 'NOT_APPLICABLE',
  );
  return live;
}

function verifyMatch(value: unknown, event: unknown) {
  const match = object(value);
  requireValue(
    oneOf(match.status, [
      'IN_DOCUMENTED_INTERVAL',
      'OUTSIDE_DOCUMENTED_INTERVAL',
      'NOT_ASSESSABLE',
    ]) &&
      match.event_at === event &&
      nullableClock(match.event_at) &&
      nullableDay(match.session_date) &&
      strings(match.reasons),
  );
  if (match.status === 'IN_DOCUMENTED_INTERVAL') {
    const interval = object(match.interval);
    requireValue(clock(interval.opens_at) && clock(interval.closes_at) && day(match.session_date));
  } else requireValue(match.interval === null);
}

function verifyScaleBinding(value: unknown, productId: unknown) {
  const binding = object(value);
  requireValue(
    binding.warrant_id === productId &&
      ['isin', 'issuer_id', 'underlying_id', 'current_terms_id'].every((key) => text(binding[key])),
  );
  return binding;
}

function verifyScaleCurrent(
  value: unknown,
  productId: unknown,
  workspace: unknown,
  evaluatedAt: unknown,
) {
  const current = object(value);
  requireValue(
    current.workspace_id === workspace &&
      current.warrant_id === productId &&
      current.known_at === evaluatedAt &&
      clock(current.read_at) &&
      nullableClock(current.recorded_at) &&
      nullableText(current.revision_id) &&
      nullableText(current.supersedes_revision_id) &&
      (current.revision_number === null ||
        (Number.isSafeInteger(current.revision_number) && Number(current.revision_number) >= 1)) &&
      oneOf(current.status, ['AVAILABLE', 'MISSING', 'UNSUITABLE']) &&
      strings(current.reasons) &&
      hash(current.fingerprint) &&
      current.verification === 'MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION' &&
      current.operation_status === 'READ_ONLY',
  );
  const binding = current.binding === null ? null : verifyScaleBinding(current.binding, productId);
  let manifest: Record<string, unknown> | null = null;
  if (current.manifest !== null) {
    manifest = object(current.manifest);
    const manifestBinding = verifyScaleBinding(manifest.binding, productId);
    requireValue(
      manifest.schema_version === 'product-price-scale-evidence-v1' &&
        manifest.axis === 'WARRANT' &&
        manifest.unit === 'CURRENCY_PER_WARRANT' &&
        currency(manifest.currency) &&
        clock(manifest.valid_from) &&
        clock(manifest.valid_until) &&
        oneOf(manifest.status, ['UNCHANGED_ORIGINAL', 'ADJUSTMENT_REQUIRED', 'WITHDRAWN']) &&
        ['scale_id', 'source_version', 'source_publisher', 'source_reference'].every((key) =>
          text(manifest?.[key]),
        ) &&
        hash(manifest.source_document_sha256) &&
        nullableClock(manifest.source_published_at) &&
        nullableDay(manifest.source_published_on),
    );
    if (current.status === 'AVAILABLE') {
      requireValue(
        binding !== null &&
          ['warrant_id', 'isin', 'issuer_id', 'underlying_id', 'current_terms_id'].every(
            (key) => binding[key] === manifestBinding[key],
          ),
      );
    }
  }
  if (current.source !== null) {
    const source = object(current.source);
    requireValue(
      hash(source.manifest_sha256) &&
        hash(source.document_sha256) &&
        [
          'document_filename',
          'document_media_type',
          'publisher',
          'reference',
          'review_reference',
          'recorded_by',
        ].every((key) => text(source[key])) &&
        clock(source.reviewed_at) &&
        nullableClock(source.retrieved_at) &&
        nullableClock(source.published_at) &&
        nullableDay(source.published_on) &&
        manifest !== null &&
        source.document_sha256 === manifest.source_document_sha256 &&
        source.publisher === manifest.source_publisher &&
        source.reference === manifest.source_reference &&
        source.published_at === manifest.source_published_at &&
        source.published_on === manifest.source_published_on,
    );
  }
  requireValue(
    current.status !== 'AVAILABLE' ||
      (binding !== null &&
        manifest !== null &&
        current.source !== null &&
        text(current.revision_id) &&
        clock(current.recorded_at)),
  );
  return current;
}

function verifyProductScale(
  value: unknown,
  report: Record<string, unknown>,
  economic: Record<string, unknown>,
  bid: Record<string, unknown>,
  workspace: unknown,
) {
  const scale = object(value);
  requireValue(
    scale.definition_version === 'hebeltrader-product-price-scale-v1' &&
      scale.adjustment_applied === false &&
      scale.execution_basis_id === economic.basis_id &&
      scale.bid_at === bid.original_bid_at &&
      oneOf(scale.status, ['DOCUMENTED', 'MISSING', 'UNSUITABLE', 'NOT_APPLICABLE']) &&
      oneOf(scale.bid_status, ['COVERED', 'MISSING', 'UNSUITABLE', 'NOT_APPLICABLE']) &&
      strings(scale.reasons) &&
      strings(scale.bid_reasons) &&
      Array.isArray(scale.purchases) &&
      Array.isArray(economic.buy_currency_evidence) &&
      strings(economic.effective_execution_ids),
  );
  const evidence = verifyScaleCurrent(
    scale.evidence,
    report.product_id,
    workspace,
    report.evaluated_at,
  );
  const effectiveExecutionIds = economic.effective_execution_ids;
  const buyEvidence = economic.buy_currency_evidence.map(object);
  requireValue(
    buyEvidence.every(
      (row) =>
        text(row.execution_id) &&
        effectiveExecutionIds.includes(row.execution_id) &&
        (row.currency_code === null || currency(row.currency_code)),
    ) && new Set(buyEvidence.map((row) => row.execution_id)).size === buyEvidence.length,
  );
  const ownerBuys = new Map(buyEvidence.map((row) => [row.execution_id, row.currency_code]));
  const purchases = scale.purchases.map(object);
  requireValue(
    new Set(purchases.map((row) => row.execution_id)).size === purchases.length &&
      purchases.length === ownerBuys.size &&
      purchases.every(
        (row) =>
          text(row.execution_id) &&
          ownerBuys.has(row.execution_id) &&
          nullableText(row.supersedes_execution_id) &&
          Number.isSafeInteger(row.original_quantity) &&
          Number(row.original_quantity) > 0 &&
          decimal(row.remaining_quantity) &&
          decimal(row.price_per_unit) &&
          clock(row.recorded_at) &&
          (row.currency_code === null || currency(row.currency_code)) &&
          nullableClock(row.possible_from) &&
          nullableClock(row.possible_until) &&
          (row.executed_on === null
            ? clock(row.executed_at) && row.execution_timezone === null
            : day(row.executed_on) && row.executed_at === null && text(row.execution_timezone)) &&
          oneOf(row.status, ['COVERED', 'MISSING', 'UNSUITABLE', 'NOT_APPLICABLE']) &&
          strings(row.reasons),
      ),
  );
  const manifest = evidence.manifest === null ? null : object(evidence.manifest);
  const binding = evidence.binding === null ? null : object(evidence.binding);
  requireValue(evidence.status !== 'AVAILABLE' || binding?.underlying_id === report.underlying_id);
  for (const purchase of purchases) {
    requireValue(
      purchase.status !== 'COVERED' ||
        (evidence.status === 'AVAILABLE' &&
          manifest?.status === 'UNCHANGED_ORIGINAL' &&
          purchase.currency_code === manifest.currency &&
          purchase.currency_code === ownerBuys.get(purchase.execution_id)),
    );
  }
  if (scale.bid_status === 'COVERED') {
    const quote = object(object(report.saved_quote).quote);
    const original = object(quote.original_evidence);
    requireValue(
      evidence.status === 'AVAILABLE' &&
        binding?.isin === original.isin &&
        manifest?.currency === bid.currency &&
        bid.status === 'AVAILABLE',
    );
  }
  if (scale.status === 'DOCUMENTED') {
    requireValue(
      report.position_state === 'OPEN' &&
        evidence.status === 'AVAILABLE' &&
        manifest?.status === 'UNCHANGED_ORIGINAL' &&
        scale.bid_status === 'COVERED' &&
        bid.status === 'AVAILABLE' &&
        manifest.currency === bid.currency &&
        purchases.some((row) => row.status === 'COVERED') &&
        purchases.every((row) => row.status === 'COVERED' || row.status === 'NOT_APPLICABLE'),
    );
  }
  requireValue(
    report.position_state === 'OPEN'
      ? scale.status !== 'NOT_APPLICABLE' && scale.bid_status !== 'NOT_APPLICABLE'
      : scale.status === 'NOT_APPLICABLE' &&
          scale.bid_status === 'NOT_APPLICABLE' &&
          purchases.every((row) => row.status === 'NOT_APPLICABLE'),
  );
  return scale;
}

/** Validate the displayed fields and their scopes, without repeating owner qualification rules. */
export function verifyHebeltraderOriginalBid(
  value: unknown,
  tradeId: string,
  positionId: string,
): HebeltraderOriginalBidReport {
  const report = object(value);
  requireValue(
    report.trade_id === tradeId &&
      report.position_id === positionId &&
      text(report.product_id) &&
      text(report.underlying_id) &&
      text(report.basis_id) &&
      oneOf(report.position_state, ['OPEN', 'CLOSED', 'CANCELLED']) &&
      clock(report.evaluated_at) &&
      clock(report.read_started_at) &&
      clock(report.read_completed_at) &&
      report.definition_version === 'hebeltrader-original-bid-v1' &&
      report.baseline_id === 'HEBELTRADER_CONFIRMED_BASELINE' &&
      report.baseline_version === '1.0.0' &&
      oneOf(report.implementation_status, [
        'F207_3_ORIGINAL_BID_EVIDENCE_ONLY',
        'F207_3_PRODUCT_PRICE_SCALE_EVIDENCE_ONLY',
        'F207_3_MARKET_STATUS_EVIDENCE_ONLY',
      ]) &&
      report.rule_evaluation_status === 'B04_B05_B06_B58_NOT_EVALUATED' &&
      report.operation_status === 'NOT_ACTIVATED' &&
      report.read_status === 'READ_ONLY' &&
      oneOf(report.coverage_status, ['PARTIAL', 'UNSUITABLE', 'NOT_APPLICABLE']) &&
      strings(report.notices),
  );
  const economic = object(report.economic_basis);
  const position = object(economic.position);
  requireValue(
    economic.definition_version === 'position-unrealized-gross-v1' &&
      text(economic.basis_id) &&
      position.id === positionId &&
      position.trade_id === tradeId &&
      position.product_id === report.product_id &&
      Number.isSafeInteger(position.open_quantity) &&
      decimal(position.average_entry_price) &&
      decimal(position.cost_basis) &&
      oneOf(economic.currency_status, ['KNOWN', 'UNKNOWN', 'MIXED']) &&
      (economic.cost_basis_currency === null || currency(economic.cost_basis_currency)) &&
      strings(economic.effective_execution_ids),
  );
  if (report.entry !== null) {
    const entry = object(report.entry);
    requireValue(
      text(entry.execution_id) &&
        oneOf(entry.time_precision, ['EXACT', 'DATE_ONLY']) &&
        nullableClock(entry.executed_at) &&
        nullableDay(entry.executed_on) &&
        nullableText(entry.execution_timezone),
    );
  }
  const underlying = object(report.underlying_sessions);
  const underlyingCalendar = verifyCalendar(
    underlying.calendar,
    'UNDERLYING',
    report.underlying_id,
    report.evaluated_at,
  );
  verifyPeriod(underlying.period);
  const saved = verifySaved(
    report.saved_quote,
    positionId,
    report.product_id,
    underlyingCalendar.workspace_id,
    report.evaluated_at,
  );
  const bid = object(report.bid);
  requireValue(
    oneOf(bid.status, ['AVAILABLE', 'MISSING', 'UNSUITABLE', 'NOT_APPLICABLE']) &&
      nullableDecimal(bid.price) &&
      nullableDecimal(bid.age_seconds) &&
      (bid.currency === null || currency(bid.currency)) &&
      nullableClock(bid.original_bid_at) &&
      bid.evaluated_at === report.evaluated_at &&
      bid.maximum_age_seconds === 900 &&
      bid.price_axis === 'WARRANT_BID' &&
      strings(bid.reasons),
  );
  if (saved.quote !== null) {
    const quote = object(saved.quote);
    const original = quote.original_evidence === null ? null : object(quote.original_evidence);
    const side = original?.bid == null ? null : object(original.bid);
    requireValue(
      bid.price === quote.bid &&
        bid.currency === quote.currency &&
        bid.original_bid_at === (side?.observed_at ?? null),
    );
  } else
    requireValue(bid.price === null && bid.original_bid_at === null && bid.status !== 'AVAILABLE');
  requireValue(
    bid.status !== 'AVAILABLE' ||
      (decimal(bid.price) && clock(bid.original_bid_at) && decimal(bid.age_seconds)),
  );
  const product = object(report.product_sessions);
  if (product.calendar !== null) {
    const calendar = verifyCalendar(
      product.calendar,
      'WARRANT',
      report.product_id,
      report.evaluated_at,
      underlyingCalendar.workspace_id,
    );
    if (calendar.status === 'AVAILABLE') {
      const route = object(saved.route);
      const binding = object(calendar.binding);
      requireValue(
        binding.listing_id === route.warrant_listing_id &&
          binding.trading_venue_id === route.trading_venue_id &&
          binding.venue_mic === route.venue_mic,
      );
    }
  }
  verifyPeriod(product.period);
  verifyMatch(product.at_bid, bid.original_bid_at);
  verifyMatch(product.at_read, report.evaluated_at);
  requireValue(
    oneOf(product.interval_relation, ['SAME_INTERVAL', 'DIFFERENT_INTERVALS', 'NOT_ASSESSABLE']),
  );
  if (underlying.count !== null) {
    const count = object(underlying.count);
    requireValue(
      bid.status === 'AVAILABLE' &&
        count.evaluated_at === bid.original_bid_at &&
        oneOf(count.status, ['AVAILABLE', 'NOT_ASSESSABLE', 'NOT_APPLICABLE']) &&
        nullableDay(count.anchor_date) &&
        nullableDay(count.twentieth_session_date) &&
        nullableClock(count.twentieth_closes_at) &&
        count.threshold_sessions === 20 &&
        strings(count.reasons),
    );
    requireValue(
      count.status === 'AVAILABLE'
        ? Number.isSafeInteger(count.completed_sessions) &&
            typeof count.threshold_reached === 'boolean'
        : count.completed_sessions === null && count.threshold_reached === null,
    );
  }
  requireValue(
    Array.isArray(report.checks) && report.checks.length === originalBidCheckKeys.length,
  );
  const checks = report.checks.map(object);
  requireValue(
    new Set(checks.map((check) => check.key)).size === originalBidCheckKeys.length &&
      checks.every(
        (check) =>
          oneOf(check.key, originalBidCheckKeys) &&
          text(check.label) &&
          text(check.detail) &&
          strings(check.reasons) &&
          oneOf(check.status, [
            'SATISFIED',
            'MISSING',
            'UNSUITABLE',
            'NOT_REACHED',
            'NOT_APPLICABLE',
          ]) &&
          Array.isArray(check.affected_rules) &&
          check.affected_rules.every((rule) => oneOf(rule, ['B04', 'B58'])),
      ),
  );
  const scale =
    report.product_price_scale == null
      ? null
      : verifyProductScale(
          report.product_price_scale,
          report,
          economic,
          bid,
          underlyingCalendar.workspace_id,
        );
  requireValue(
    !['F207_3_PRODUCT_PRICE_SCALE_EVIDENCE_ONLY', 'F207_3_MARKET_STATUS_EVIDENCE_ONLY'].includes(
      String(report.implementation_status),
    ) || scale !== null,
  );
  const scaleCheck = checks.find((check) => check.key === 'PRICE_SCALE');
  requireValue(
    scale === null
      ? scaleCheck?.status === (report.position_state === 'OPEN' ? 'MISSING' : 'NOT_APPLICABLE')
      : scaleCheck?.status === (scale.status === 'DOCUMENTED' ? 'SATISFIED' : scale.status),
  );
  requireValue(
    report.implementation_status !== 'F207_3_MARKET_STATUS_EVIDENCE_ONLY' ||
      report.live_market_status != null,
  );
  const live =
    report.live_market_status == null
      ? null
      : verifyLiveMarketStatus(report.live_market_status, report, saved, bid);
  const liveCheck = checks.find((check) => check.key === 'VERIFIED_LIVE_MARKET_STATUS');
  requireValue(live === null || liveCheck?.status === live.status);
  requireValue(
    report.position_state === 'OPEN'
      ? report.coverage_status !== 'NOT_APPLICABLE' &&
          (report.implementation_status === 'F207_3_MARKET_STATUS_EVIDENCE_ONLY'
            ? live !== null && oneOf(liveCheck?.status, ['MISSING', 'UNSUITABLE'])
            : liveCheck?.status === 'MISSING')
      : report.coverage_status === 'NOT_APPLICABLE' &&
          checks.every((check) => check.status === 'NOT_APPLICABLE'),
  );
  return value as HebeltraderOriginalBidReport;
}

export async function readHebeltraderOriginalBid(
  tradeId: string,
  positionId: string,
  signal?: AbortSignal,
): Promise<HebeltraderOriginalBidReport> {
  let value: unknown;
  try {
    value = await requestJson<unknown>(
      `${environment.apiBaseUrl}/api/v1/position-monitoring/trades/${encodeURIComponent(tradeId)}/hebeltrader-original-bid?position_id=${encodeURIComponent(positionId)}`,
      { signal },
    );
  } catch (error) {
    throw new Error(
      error instanceof MarketApiError && error.status === 403
        ? 'Keine Berechtigung für den Original-Geldkursbeleg dieser Position.'
        : 'Der Original-Geldkursbeleg konnte nicht gelesen werden. Fehlende oder ungeeignete Kursbelege sind damit nicht festgestellt.',
    );
  }
  return verifyHebeltraderOriginalBid(value, tradeId, positionId);
}
