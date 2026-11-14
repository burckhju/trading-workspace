import type { HebeltraderTargetAssessment, HebeltraderTargetsReport } from '../hebeltraderTargets';

export function targetAssessment(
  overrides: Partial<HebeltraderTargetAssessment> = {},
): HebeltraderTargetAssessment {
  return {
    id: 'assessment-1',
    recorded_at: '2026-11-14T10:00:00Z',
    basis_id: 'basis-1',
    source_version_id: 'source-version-1',
    previous_assessment_id: null,
    targets: [
      {
        target: 'Z1',
        status: 'PROVEN',
        threshold: '110.123456789',
        currency: 'USD',
        event_id: 'event-z1',
        proof_source_version_id: 'source-version-1',
        proof_scale_reference: 'source-original-1',
        detail: 'Z1 durch den gespeicherten Basiswertbeleg erreicht.',
        reasons: [],
        evidence: {
          trading_date: '2026-09-09',
          interval_start: '2026-09-09T00:00:00Z',
          interval_end: '2026-09-10T00:00:00Z',
          high: '111.123456789',
          source_row_id: 'price-row-1',
          source_fingerprint: 'price-fingerprint-1',
          provider: 'SYNTHETIC',
          provider_symbol: 'TEST.US',
          listing_id: 'listing-1',
          time_precision: 'DATE_ONLY',
          detected_at: '2026-11-14T10:00:00Z',
        },
      },
      {
        target: 'Z2',
        status: 'NOT_PROVEN',
        threshold: '120',
        currency: 'USD',
        event_id: null,
        proof_source_version_id: null,
        proof_scale_reference: null,
        detail: 'Die verfügbaren Belege weisen keinen Z2-Treffer nach.',
        reasons: [],
        evidence: null,
      },
    ],
    orientation: {
      status: 'AVAILABLE',
      original_quantity: 7,
      assigned_sold_quantity: 2,
      proportion: '0.5',
      detail: 'Die ursprüngliche Bezugsmenge bleibt trotz Nachkauf erhalten.',
    },
    protection_basis: {
      status: 'AVAILABLE',
      personal_underlying_entry: '100.987654321',
      currency: 'USD',
      detail: 'Persönlicher Basiswerteinstieg aus den vorhandenen Kaufbelegen.',
    },
    ...overrides,
  };
}

export function targetReport(
  overrides: Partial<HebeltraderTargetsReport> = {},
): HebeltraderTargetsReport {
  return {
    definition_version: 'hebeltrader-targets-v1',
    baseline_id: 'HEBELTRADER_CONFIRMED_BASELINE',
    baseline_version: '1.0.0',
    implementation_status: 'F207_2_TARGET_HISTORY_ONLY',
    operation_status: 'NOT_ACTIVATED',
    trade_id: 'trade-1',
    position_id: 'position-1',
    current_basis_id: 'basis-1',
    currentness: 'CURRENT',
    position_state: 'OPEN',
    read_started_at: '2026-11-14T10:00:00Z',
    read_completed_at: '2026-11-14T10:00:01Z',
    assessment_count: 1,
    inputs: {
      source_version_id: 'source-version-1',
      source_scale_reference: 'source-original-1',
      price_history_fingerprint: 'history-1',
      listing_binding_fingerprint: 'listing-binding-1',
      qualification_reusable: true,
      available_price_rows: 2,
      issues: [],
    },
    latest_assessment: targetAssessment(),
    ...overrides,
  };
}
