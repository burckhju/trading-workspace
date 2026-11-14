import { MarketApiError, requestJson } from '../../market/services/http';
import type { HebeltraderTargetAssessmentRequest } from '../hebeltraderTargets';
import { targetAssessment, targetReport } from '../test/hebeltraderTargetsFixture';
import { assessHebeltraderTargets, readHebeltraderTargets } from './hebeltraderTargets';

vi.mock('../../market/services/http', async (original) => ({
  ...(await original<typeof import('../../market/services/http')>()),
  requestJson: vi.fn(),
}));

beforeEach(() => vi.mocked(requestJson).mockReset());

const payload: HebeltraderTargetAssessmentRequest = {
  position_id: 'position/b',
  request_id: '00000000-0000-4000-8000-000000000123',
  expected_basis_id: 'basis-1',
  expected_assessment_id: 'assessment-1',
  confirmation: 'ASSESS_SAVED_HEBELTRADER_EVIDENCE',
};

it('reads only the exact owner route and position with cancellation', async () => {
  const report = targetReport({ trade_id: 'trade/a', position_id: 'position/b' });
  vi.mocked(requestJson).mockResolvedValue(report);
  const signal = new AbortController().signal;
  expect(await readHebeltraderTargets('trade/a', 'position/b', signal)).toBe(report);
  expect(requestJson).toHaveBeenCalledExactlyOnceWith(
    expect.stringMatching(
      /position-monitoring\/trades\/trade%2Fa\/hebeltrader-targets\?position_id=position%2Fb$/,
    ),
    { signal },
  );
});

it('posts the frozen explicit assessment contract once and validates its returned identity', async () => {
  const report = targetReport({ trade_id: 'trade/a', position_id: 'position/b' });
  const signal = new AbortController().signal;
  vi.mocked(requestJson).mockResolvedValueOnce(report);
  expect(await assessHebeltraderTargets('trade/a', payload, signal)).toBe(report);
  expect(requestJson).toHaveBeenCalledExactlyOnceWith(
    expect.stringMatching(/trades\/trade%2Fa\/hebeltrader-targets\/assessments$/),
    { method: 'POST', body: payload, signal },
  );
  vi.mocked(requestJson).mockResolvedValueOnce(targetReport({ position_id: 'other' }));
  await expect(assessHebeltraderTargets('trade/a', payload)).rejects.toThrow(
    'nicht sicher zuordnen',
  );
});

it('fails closed for mixed identity, activation, malformed target evidence and contradictory history', async () => {
  const target = targetAssessment().targets[0];
  const invalid = [
    null,
    [],
    targetReport({ trade_id: 'other' }),
    targetReport({ position_id: 'other' }),
    { ...targetReport(), definition_version: 'future' },
    { ...targetReport(), baseline_version: '2.0.0' },
    { ...targetReport(), implementation_status: 'BASELINE_COMPLETE' },
    { ...targetReport(), operation_status: 'ACTIVATED' },
    { ...targetReport(), currentness: 'HEALTHY' },
    { ...targetReport(), position_state: 'HEALTHY' },
    targetReport({ latest_assessment: null }),
    targetReport({ currentness: 'NO_ASSESSMENT' }),
    targetReport({ assessment_count: 0 }),
    targetReport({ inputs: { ...targetReport().inputs, available_price_rows: -1 } }),
    { ...targetReport(), inputs: { ...targetReport().inputs, qualification_reusable: 'true' } },
    targetReport({ latest_assessment: targetAssessment({ targets: [target, target] }) }),
    ...[
      { status: 'HEALTHY' },
      { threshold: 'NaN' },
      { currency: 'usd' },
      { event_id: null },
      { proof_source_version_id: null },
      { proof_scale_reference: null },
      { evidence: null },
      { reasons: null },
      { evidence: { ...target.evidence, time_precision: 'TIMESTAMP' } },
      { evidence: { ...target.evidence, source_row_id: undefined } },
    ].map((change) => ({
      ...targetReport(),
      latest_assessment: {
        ...targetAssessment(),
        targets: [{ ...target, ...change }, targetAssessment().targets[1]],
      },
    })),
  ];
  for (const report of invalid) {
    vi.mocked(requestJson).mockResolvedValueOnce(report);
    await expect(readHebeltraderTargets('trade-1', 'position-1')).rejects.toThrow(
      'nicht sicher zuordnen',
    );
  }
});

it('preserves no-assessment, changed-input and closed historical reports without inferring health', async () => {
  for (const report of [
    targetReport({ currentness: 'NO_ASSESSMENT', latest_assessment: null, assessment_count: 0 }),
    targetReport({ currentness: 'CHANGED_INPUTS', current_basis_id: 'basis-2' }),
    targetReport({ position_state: 'CLOSED' }),
    targetReport({ position_state: 'CANCELLED' }),
  ]) {
    vi.mocked(requestJson).mockResolvedValueOnce(report);
    expect(await readHebeltraderTargets('trade-1', 'position-1')).toBe(report);
  }
});

it('keeps read permission and unknown command outcome explicit without retries or automatic readback', async () => {
  vi.mocked(requestJson).mockRejectedValueOnce(
    new MarketApiError(403, {
      code: 'FORBIDDEN',
      message: 'Denied',
      details: [],
      timestamp: '2026-11-14T10:00:00Z',
    }),
  );
  await expect(readHebeltraderTargets('trade/a', 'position/b')).rejects.toThrow(
    'Keine Berechtigung',
  );
  vi.mocked(requestJson).mockRejectedValueOnce(new Error('network unavailable'));
  await expect(assessHebeltraderTargets('trade/a', payload)).rejects.toThrow(
    'Ausgang der Prüfung konnte nicht bestätigt',
  );
  expect(requestJson).toHaveBeenCalledTimes(2);
  vi.mocked(requestJson).mockRejectedValueOnce(
    new MarketApiError(409, {
      code: 'CHANGED',
      message: 'Changed',
      details: [],
      timestamp: '2026-11-14T10:00:00Z',
    }),
  );
  await expect(assessHebeltraderTargets('trade/a', payload)).rejects.toThrow(
    'Beleggrundlage hat sich geändert',
  );
  expect(requestJson).toHaveBeenCalledTimes(3);
});
