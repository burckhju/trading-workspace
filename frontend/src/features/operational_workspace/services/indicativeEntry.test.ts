import { MarketApiError, requestJson } from '../../market/services/http';
import {
  indicativeAssessment,
  indicativeEpisode,
  indicativeReport,
} from '../test/indicativeEntryFixture';
import { readIndicativeEntry, verifyIndicativeEntry } from './indicativeEntry';

vi.mock('../../market/services/http', async (original) => ({
  ...(await original<typeof import('../../market/services/http')>()),
  requestJson: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(requestJson).mockReset();
});

it('uses only the existing position-scoped GET and propagates cancellation', async () => {
  const report = indicativeReport({
    trade_id: 'synthetic/trade',
    position_id: 'synthetic/position',
  });
  vi.mocked(requestJson).mockResolvedValue(report);
  const signal = new AbortController().signal;
  expect(await readIndicativeEntry(report.trade_id, report.position_id, signal)).toBe(report);
  expect(requestJson).toHaveBeenCalledExactlyOnceWith(
    expect.stringMatching(
      /trades\/synthetic%2Ftrade\/indicative-entry\?position_id=synthetic%2Fposition$/,
    ),
    { signal },
  );
});

it('preserves a V1 loss alongside a V2 data problem without deriving recovery', () => {
  const active = [
    indicativeEpisode(),
    indicativeEpisode({
      id: 'synthetic-data',
      kind: 'DATA_UNAVAILABLE',
      rule_version: 'indicative-entry-review-v2',
    }),
  ];
  const report = indicativeReport({
    latest_assessment: indicativeAssessment(),
    assessment_count: 2,
    active_episodes: active,
    recent_episodes: active,
    episode_count: 2,
  });
  expect(verifyIndicativeEntry(report, report.trade_id, report.position_id)).toBe(report);
  expect(report.latest_assessment?.outcome).toBe('UNAVAILABLE');
  expect(report.active_episodes[0].closed_at).toBeNull();
});

it('accepts legacy V1 reports without claiming newer quality metadata', () => {
  const latest = indicativeAssessment({
    rule_version: undefined,
    source_quote_at: undefined,
    source_time_basis: undefined,
    source_freshness: undefined,
    product_scale_quality: undefined,
    history_continuity_assumed: undefined,
    evaluation_mode: 'INDICATIVE_ISSUER',
  });
  const report = indicativeReport({
    scope: 'INDICATIVE_ENTRY_V1',
    definition_version: 'indicative-entry-review-v1',
    latest_assessment: latest,
    assessment_count: 1,
  });
  expect(verifyIndicativeEntry(report, report.trade_id, report.position_id)).toBe(report);
  expect(report.latest_assessment?.source_time_basis).toBeUndefined();
});

it('rejects foreign positions, mismatched versions, invented qualification and malformed clocks', () => {
  const report = indicativeReport();
  const active = indicativeEpisode();
  const invalid: unknown[] = [
    null,
    { ...report, position_id: 'foreign' },
    { ...report, trade_id: 'foreign' },
    { ...report, definition_version: 'indicative-entry-review-v1' },
    { ...report, qualified_b04: true },
    { ...report, full_baseline_activated: true },
    { ...report, read_status: 'WRITE' },
    { ...report, read_at: '2026-11-18' },
    { ...report, read_at: '2026-02-30T15:00:00Z' },
    { ...report, read_at: '2026-11-18T15:00:00-00:00' },
    { ...report, assessment_count: 1 },
    { ...report, latest_assessment: indicativeAssessment() },
    { ...report, assessment_count: 1, latest_assessment: indicativeAssessment({ bid: 'NaN' }) },
    {
      ...report,
      assessment_count: 1,
      latest_assessment: { ...indicativeAssessment(), source_freshness: 'LIVE_CONFIRMED' },
    },
    { ...report, episode_count: 2, active_episodes: [active, { ...active, id: 'duplicate-kind' }] },
    {
      ...report,
      episode_count: 1,
      active_episodes: [
        {
          ...active,
          closed_at: '2026-11-18T15:00:00Z',
          close_reason: 'CLOSED',
          closing_assessment_id: 'synthetic-closing',
        },
      ],
    },
  ];
  for (const value of invalid) {
    expect(() => verifyIndicativeEntry(value, report.trade_id, report.position_id)).toThrow(
      /Prüfstand/,
    );
  }
});

it('does not convert a read error into missing evidence or a cleared episode', async () => {
  vi.mocked(requestJson).mockRejectedValueOnce(new Error('synthetic transport failure'));
  await expect(readIndicativeEntry('synthetic-trade', 'synthetic-position')).rejects.toThrow(
    /Offene Hinweise und Datenlage sind damit nicht geklärt/,
  );
  vi.mocked(requestJson).mockRejectedValueOnce(
    new MarketApiError(403, {
      code: 'DENIED',
      message: 'Synthetic',
      details: [],
      timestamp: '2026-11-18T15:00:00Z',
    }),
  );
  await expect(readIndicativeEntry('synthetic-trade', 'synthetic-position')).rejects.toThrow(
    /Keine Berechtigung/,
  );
  const abort = new DOMException('Aborted', 'AbortError');
  vi.mocked(requestJson).mockRejectedValueOnce(abort);
  await expect(readIndicativeEntry('synthetic-trade', 'synthetic-position')).rejects.toBe(abort);
});

it('keeps current document acquisition diagnostics separate from the recorded assessment', () => {
  const latest = indicativeAssessment();
  const report = indicativeReport({
    latest_assessment: latest,
    assessment_count: 1,
    document_readiness: {
      outcome: 'PRODUCT_DOCUMENT_ACQUISITION_FAILED',
      attempted_at: '2026-11-18T15:31:00Z',
      next_attempt_at: '2026-11-18T15:46:00Z',
    },
  });
  expect(verifyIndicativeEntry(report, report.trade_id, report.position_id).latest_assessment).toBe(
    latest,
  );
  expect(() =>
    verifyIndicativeEntry(
      {
        ...report,
        document_readiness: { ...report.document_readiness, attempted_at: '2026-11-18' },
      },
      report.trade_id,
      report.position_id,
    ),
  ).toThrow(/Prüfstand/);
});
