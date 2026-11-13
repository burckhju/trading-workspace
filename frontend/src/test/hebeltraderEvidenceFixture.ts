import type {
  HebeltraderEvidenceReport,
  HebeltraderSource,
} from '../features/operational_workspace/hebeltraderEvidence';

export function hebeltraderSource(overrides: Partial<HebeltraderSource> = {}): HebeltraderSource {
  const marks = {
    reference_price: '100',
    target_1: '110',
    target_2: '120',
    stop_1: '90',
    stop_2: '95',
    scale: 'SOURCE_ORIGINAL' as const,
  };
  return {
    source_version_id: 'source-version-1',
    observation_id: 'observation-1',
    version: 1,
    supersedes_version_id: null,
    currentness: 'CURRENT_SOURCE',
    product_id: 'product-1',
    underlying_id: 'underlying-1',
    underlying: {
      ...marks,
      binding: { basis: 'UNDERLYING', instrument_id: 'underlying-1', currency: 'USD' },
    },
    product: {
      ...marks,
      binding: { basis: 'WARRANT', instrument_id: 'product-1', currency: 'EUR' },
    },
    issue_date: '2026-08-03',
    time_precision: 'DATE_ONLY',
    observed_at: '2026-08-03T00:00:00Z',
    recorded_at: '2026-11-14T09:00:00Z',
    imported_at: '2026-11-14T09:00:00Z',
    source_name: 'HEBELTRADER',
    external_reference: '123/2026',
    import_row_id: 'import-row-1',
    batch_id: 'batch-1',
    file_id: 'file-1',
    filename: 'synthetic.pdf',
    content_hash: 'a'.repeat(64),
    accepted_at: '2026-11-14T09:05:00Z',
    accepted_by: 'actor-1',
    ...overrides,
  };
}

export function hebeltraderEvidence(
  overrides: Partial<HebeltraderEvidenceReport> = {},
): HebeltraderEvidenceReport {
  return {
    definition_version: 'hebeltrader-evidence-v1',
    trade_id: 'trade-1',
    position_id: 'position-1',
    product_id: 'product-1',
    underlying_id: 'underlying-1',
    basis_id: 'basis-1',
    read_started_at: '2026-11-14T10:00:00Z',
    read_completed_at: '2026-11-14T10:00:01Z',
    evidence_revision_id: null,
    evidence_recorded_at: null,
    coverage_status: 'INCOMPLETE',
    items: [
      {
        key: 'executions',
        label: 'Ausführungen',
        status: 'PRESENT',
        detail: 'Vorhandene Ausführungen und Restmenge.',
        affected_rules: ['B10', 'B53'],
        clarification: null,
        references: ['execution:buy-1'],
      },
      {
        key: 'entry_group',
        label: 'Einstiegsgruppe',
        status: 'MISSING',
        detail: 'Auftragszugehörigkeit fehlt.',
        affected_rules: ['B01', 'B55'],
        clarification: 'Ursprünglichen Auftrag mit den belegten Teilausführungen zuordnen.',
        references: [],
      },
    ],
    original_z1_quantity: null,
    assigned_z1_sold_quantity: null,
    personal_underlying_entry: null,
    underlying_currency: null,
    source: null,
    implementation_status: 'F207_4_EVIDENCE_ONLY',
    operation_status: 'NOT_ASSESSED',
    baseline_id: 'HEBELTRADER_CONFIRMED_BASELINE',
    baseline_version: '1.0.0',
    ...overrides,
  };
}
