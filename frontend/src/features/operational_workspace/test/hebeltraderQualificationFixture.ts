import { hebeltraderSource } from '../../../test/hebeltraderEvidenceFixture';
import type {
  HistoricalDailyEvidence,
  TargetQualificationPreview,
  TargetRequestStatus,
} from '../hebeltraderQualification';
import type { TargetComparisonQualification } from '../hebeltraderTargets';
import { targetAssessment, targetReport } from './hebeltraderTargetsFixture';

export function historicalPrice(
  overrides: Partial<HistoricalDailyEvidence> = {},
): HistoricalDailyEvidence {
  return {
    source_row_id: 'price-row-1',
    workspace_id: 'workspace-1',
    listing_id: 'listing-1',
    market_data_instrument_id: 'instrument-1',
    fingerprint: 'price-fingerprint-1',
    trading_date: '2026-09-09',
    open: '100',
    high: '111.1234567891',
    low: '99',
    close: '110',
    adjusted_close: null,
    volume: '1234',
    currency: 'USD',
    provider: 'SYNTHETIC',
    provider_symbol: 'TEST.US',
    price_type: 'EOD',
    quality_status: 'VALID',
    warnings: [],
    interval_start: '2026-09-09T04:00:00Z',
    interval_end: '2026-09-10T04:00:00Z',
    retrieved_at: '2026-11-12T10:00:00Z',
    source_updated_at: '2026-11-11T10:00:00Z',
    recorded_at: '2026-11-12T10:00:01Z',
    last_updated_at: '2026-11-13T10:00:00Z',
    issues: [],
    scale_status: 'REQUIRES_EXPLICIT_COMPARISON_QUALIFICATION',
    time_precision: 'DATE_ONLY',
    interval_basis: 'LOCAL_CALENDAR_DAY_NOT_VERIFIED_SESSION',
    price_basis: 'UNDERLYING',
    ...overrides,
  };
}

export function comparisonQualification(
  overrides: Partial<TargetComparisonQualification> = {},
): TargetComparisonQualification {
  return {
    history_fingerprint: 'history-1',
    listing_fingerprint: 'listing-binding-1',
    source_version_id: 'source-version-1',
    source_scale_reference: 'source-original-1',
    evidence_reference:
      'Synthetisches Listingarchiv 2026, Seite 7; Originalmaßstab im Zeitraum geprüft.',
    ...overrides,
  };
}

export function qualificationPreview(
  overrides: Partial<TargetQualificationPreview> = {},
): TargetQualificationPreview {
  const rows = [
    historicalPrice(),
    historicalPrice({
      source_row_id: 'price-row-2',
      fingerprint: 'price-fingerprint-2',
      trading_date: '2026-09-10',
      high: '112.987654321',
      interval_start: '2026-09-10T04:00:00Z',
      interval_end: '2026-09-11T04:00:00Z',
    }),
  ];
  const qualification = comparisonQualification();
  const binding = {
    history_fingerprint: qualification.history_fingerprint,
    listing_fingerprint: qualification.listing_fingerprint,
    source_version_id: qualification.source_version_id,
    source_scale_reference: qualification.source_scale_reference,
  };
  return {
    definition_version: 'hebeltrader-qualification-preview-v1',
    operation_status: 'READ_ONLY',
    report: targetReport({
      latest_assessment: null,
      assessment_count: 0,
      currentness: 'NO_ASSESSMENT',
      inputs: {
        ...targetReport().inputs,
        qualification_reusable: false,
        issues: ['Vergleichsbestätigung fehlt.'],
      },
    }),
    entry: {
      product_id: 'product-1',
      underlying_id: 'underlying-1',
      option_direction: 'CALL',
      opened_at: null,
      opened_on: '2026-09-01',
      opening_timezone: 'America/New_York',
      evidence_revision_id: 'revision-1',
    },
    source: hebeltraderSource(),
    attempted_source_version_id: 'source-version-1',
    source_issues: [],
    source_scale: {
      review_status: 'UNCHANGED_VERIFIED',
      source_scale_reference: 'source-original-1',
      review_reference: 'Synthetischer Quellen- und Kaufbeleg, Seite 2.',
      scope: 'SOURCE_AND_PURCHASE_EVIDENCE_ONLY',
      market_observations_verified: false,
    },
    history: {
      workspace_id: 'workspace-1',
      underlying_id: 'underlying-1',
      binding: {
        workspace_id: 'workspace-1',
        underlying_id: 'underlying-1',
        listing_id: 'listing-1',
        trading_venue_id: 'venue-1',
        venue_mic: 'XNAS',
        timezone: 'America/New_York',
        currency: 'USD',
        listing_version: 2,
        venue_version: 3,
        venue_reference_version: 'synthetic-reference-v1',
        listing_recorded_at: '2026-01-01T10:00:00Z',
        listing_updated_at: '2026-11-01T10:00:00Z',
        venue_recorded_at: '2026-01-01T10:00:00Z',
        venue_updated_at: '2026-11-01T10:00:00Z',
        fingerprint: 'listing-binding-1',
        provenance: 'CURRENT_REFERENCE_NOT_HISTORICALLY_VERIFIED',
      },
      rows,
      status: 'AVAILABLE',
      reasons: [],
      fingerprint: 'history-1',
      start_date: '2026-09-01',
      end_date: '2026-11-14',
      known_at: '2026-11-14T10:00:00Z',
      read_at: '2026-11-14T10:00:00Z',
      stored_range_complete: true,
      intervals_complete: true,
      rows_observed: rows.length,
      row_limit: 5000,
      calendar_coverage: 'NOT_ASSESSED',
      qualification_required: 'HISTORICAL_BINDING_AND_COMPARISON_SCALE',
    },
    readiness: {
      status: 'REVIEWABLE',
      issues: [],
      usable_row_count: rows.length,
      rows: rows.map((row) => ({
        source_row_id: row.source_row_id,
        fingerprint: row.fingerprint,
        status: 'SUITABLE_AFTER_CONFIRMATION',
        issues: [],
      })),
    },
    qualification: {
      status: 'MISSING',
      value: null,
      contained_in_assessment_id: null,
      contained_in_recorded_at: null,
      origin: 'USER_DECLARATION_NOT_INDEPENDENT_VERIFICATION',
    },
    qualification_binding: binding,
    notices: ['Synthetische Kursreihe; keine Providerabfrage und keine Regelfreigabe.'],
    ...overrides,
  };
}

export function targetRequest(overrides: Partial<TargetRequestStatus> = {}): TargetRequestStatus {
  return {
    definition_version: 'hebeltrader-request-status-v1',
    operation_status: 'READ_ONLY',
    trade_id: 'trade-1',
    position_id: 'position-1',
    request_id: '00000000-0000-4000-8000-000000000123',
    status: 'RECORDED',
    read_started_at: '2026-11-14T11:00:00Z',
    read_completed_at: '2026-11-14T11:00:01Z',
    recorded_at: '2026-11-14T10:00:01Z',
    assessment: targetAssessment(),
    qualification: comparisonQualification(),
    ...overrides,
  };
}
