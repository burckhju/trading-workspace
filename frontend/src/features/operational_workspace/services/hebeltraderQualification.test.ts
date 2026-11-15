import { MarketApiError, requestJson } from '../../market/services/http';
import type { TargetQualificationPreview } from '../hebeltraderQualification';
import {
  comparisonQualification,
  qualificationPreview,
  targetRequest,
} from '../test/hebeltraderQualificationFixture';
import { targetAssessment, targetReport } from '../test/hebeltraderTargetsFixture';
import {
  readQualificationPreview,
  readTargetRequest,
  verifyQualificationPreview,
} from './hebeltraderQualification';
import { assessHebeltraderTargets, HebeltraderCommandError } from './hebeltraderTargets';

vi.mock('../../market/services/http', async (original) => ({
  ...(await original<typeof import('../../market/services/http')>()),
  requestJson: vi.fn(),
}));
beforeEach(() => vi.mocked(requestJson).mockReset());

it('uses the exact scoped read routes, preserves original decimals and never writes or refreshes a provider', async () => {
  const preview = qualificationPreview({
    report: targetReport({
      trade_id: 'trade/a',
      position_id: 'position/b',
      inputs: qualificationPreview().report.inputs,
    }),
  });
  const signal = new AbortController().signal;
  vi.mocked(requestJson).mockResolvedValueOnce(preview);
  expect(await readQualificationPreview('trade/a', 'position/b', signal)).toBe(preview);
  expect(preview.history.rows[0].high).toBe('111.1234567891');
  const receipt = targetRequest({
    trade_id: 'trade/a',
    position_id: 'position/b',
    request_id: 'request/c',
  });
  vi.mocked(requestJson).mockResolvedValueOnce(receipt);
  expect(await readTargetRequest('trade/a', 'position/b', 'request/c', signal)).toBe(receipt);
  expect(vi.mocked(requestJson).mock.calls).toEqual([
    [
      expect.stringMatching(
        /trades\/trade%2Fa\/hebeltrader-targets\/qualification-preview\?position_id=position%2Fb$/,
      ),
      { signal },
    ],
    [
      expect.stringMatching(
        /trades\/trade%2Fa\/hebeltrader-targets\/requests\/request%2Fc\?position_id=position%2Fb$/,
      ),
      { signal },
    ],
  ]);
});

it.each(['scale', 'PUT', 'closed'] as const)(
  'retains complete raw history when global %s prevents a row review',
  (blocker) => {
    const preview = qualificationPreview();
    preview.readiness = {
      status: blocker === 'closed' ? 'NOT_APPLICABLE' : 'BLOCKED',
      issues: [{ code: 'GLOBAL_BLOCKER', detail: 'Konkreter globaler Sperrgrund.' }],
      usable_row_count: 0,
      rows: [],
    };
    preview.qualification_binding = null;
    if (blocker === 'scale') {
      preview.source_scale.source_scale_reference = null;
      preview.report.inputs.source_scale_reference = null;
    } else if (blocker === 'PUT') preview.entry.option_direction = 'PUT';
    else preview.report.position_state = 'CLOSED';
    expect(verifyQualificationPreview(preview, 'trade-1', 'position-1')).toBe(preview);
    expect(preview.history.rows).toHaveLength(2);
  },
);

it('preserves individually unsuitable original values and adjustment indications without promoting them to evidence', () => {
  const preview = qualificationPreview();
  preview.history.rows[1] = {
    ...preview.history.rows[1],
    currency: '',
    provider_symbol: '',
    high: 'NaN',
    adjusted_close: '55',
    scale_status: 'ADJUSTMENT_INDICATION_PRESENT',
    issues: ['CURRENCY_INVALID', 'ADJUSTMENT_INDICATION'],
  };
  preview.readiness.rows[1] = {
    ...preview.readiness.rows[1],
    status: 'UNSUITABLE',
    issues: [{ code: 'ADJUSTMENT_INDICATION', detail: 'Ungeeigneter Originalbeleg.' }],
  };
  preview.readiness.usable_row_count = 1;
  expect(verifyQualificationPreview(preview, 'trade-1', 'position-1')).toBe(preview);
});

it.each(['REUSABLE', 'STALE'] as const)(
  'keeps the stored %s declaration distinct from independent historical verification',
  (status) => {
    const preview = qualificationPreview();
    preview.report.inputs.qualification_reusable = status === 'REUSABLE';
    preview.qualification = {
      status,
      value: comparisonQualification({
        history_fingerprint: status === 'REUSABLE' ? 'history-1' : 'old-history',
      }),
      contained_in_assessment_id: 'assessment-7',
      contained_in_recorded_at: '2026-11-14T10:00:00Z',
      origin: 'USER_DECLARATION_NOT_INDEPENDENT_VERIFICATION',
    };
    expect(verifyQualificationPreview(preview, 'trade-1', 'position-1')).toBe(preview);
  },
);

const corruptions: [string, (value: TargetQualificationPreview) => void][] = [
  [
    'foreign position',
    (p) => {
      p.report.position_id = 'other';
    },
  ],
  [
    'foreign trade',
    (p) => {
      p.report.trade_id = 'other';
    },
  ],
  [
    'foreign source identity',
    (p) => {
      p.source!.product_id = 'other';
    },
  ],
  [
    'foreign source axis',
    (p) => {
      p.source!.underlying.binding.basis = 'WARRANT' as 'UNDERLYING';
    },
  ],
  [
    'foreign source version',
    (p) => {
      p.source!.source_version_id = 'other';
    },
  ],
  [
    'foreign workspace row',
    (p) => {
      p.history.rows[0].workspace_id = 'other';
    },
  ],
  [
    'foreign listing row',
    (p) => {
      p.history.rows[0].listing_id = 'other';
    },
  ],
  [
    'foreign listing underlying',
    (p) => {
      p.history.binding!.underlying_id = 'other';
    },
  ],
  [
    'mismatched history fingerprint',
    (p) => {
      p.report.inputs.price_history_fingerprint = 'other';
    },
  ],
  [
    'mismatched listing fingerprint',
    (p) => {
      p.report.inputs.listing_binding_fingerprint = 'other';
    },
  ],
  [
    'mismatched source scale',
    (p) => {
      p.qualification_binding!.source_scale_reference = 'other';
    },
  ],
  [
    'invented source scale',
    (p) => {
      p.source_scale.source_scale_reference = null;
    },
  ],
  [
    'unscoped binding',
    (p) => {
      p.qualification_binding!.source_version_id = 'other';
    },
  ],
  [
    'unreviewed row in reviewable preview',
    (p) => {
      p.readiness.rows.pop();
    },
  ],
  [
    'repeated row review',
    (p) => {
      p.readiness.rows[1] = p.readiness.rows[0];
    },
  ],
  [
    'wrong reviewed original',
    (p) => {
      p.readiness.rows[0].fingerprint = 'other';
    },
  ],
  [
    'duplicate original row',
    (p) => {
      p.history.rows[1] = p.history.rows[0];
    },
  ],
  [
    'wrong usable row count',
    (p) => {
      p.readiness.usable_row_count = 9;
    },
  ],
  [
    'reviewable empty row review',
    (p) => {
      p.readiness.rows = [];
      p.readiness.usable_row_count = 0;
    },
  ],
  [
    'unbound reviewable preview',
    (p) => {
      p.qualification_binding = null;
    },
  ],
  [
    'invented independent verification',
    (p) => {
      p.qualification.origin = 'VERIFIED' as typeof p.qualification.origin;
    },
  ],
  [
    'unannounced extra rows',
    (p) => {
      p.report.inputs.available_price_rows = 1;
    },
  ],
  [
    'row limit overflow',
    (p) => {
      p.history.row_limit = 1;
    },
  ],
  [
    'missing offset',
    (p) => {
      p.history.rows[0].retrieved_at = '2026-11-12T10:00:00';
    },
  ],
  [
    'invented session precision',
    (p) => {
      p.history.rows[0].interval_basis = 'SESSION' as (typeof p.history.rows)[0]['interval_basis'];
    },
  ],
  [
    'wrong price axis',
    (p) => {
      p.history.rows[0].price_basis = 'WARRANT' as 'UNDERLYING';
    },
  ],
  [
    'unbound reused qualification',
    (p) => {
      p.report.inputs.qualification_reusable = true;
      p.qualification = {
        ...p.qualification,
        status: 'REUSABLE',
        value: comparisonQualification({ history_fingerprint: 'old' }),
        contained_in_assessment_id: 'old-assessment',
        contained_in_recorded_at: '2026-11-14T10:00:00Z',
      };
    },
  ],
];
it.each(corruptions)('rejects %s without manufacturing a reviewable result', (_label, corrupt) => {
  const preview = qualificationPreview();
  corrupt(preview);
  expect(() => verifyQualificationPreview(preview, 'trade-1', 'position-1')).toThrow(
    /nicht sicher zuordnen/,
  );
});

it('represents absent sources, missing listing and empty history as explicit blocked evidence', () => {
  const preview = qualificationPreview();
  preview.source = null;
  preview.attempted_source_version_id = null;
  preview.source_issues = [{ code: 'NOT_FOUND', detail: 'Quelle fehlt.' }];
  preview.history = {
    ...preview.history,
    binding: null,
    rows: [],
    status: 'MISSING',
    rows_observed: 0,
    stored_range_complete: false,
    intervals_complete: false,
  };
  preview.report.inputs = {
    ...preview.report.inputs,
    source_version_id: null,
    listing_binding_fingerprint: null,
    available_price_rows: 0,
  };
  preview.readiness = {
    status: 'BLOCKED',
    issues: [{ code: 'SOURCE_MISSING', detail: 'Quelle fehlt.' }],
    usable_row_count: 0,
    rows: [],
  };
  preview.qualification_binding = null;
  expect(verifyQualificationPreview(preview, 'trade-1', 'position-1')).toBe(preview);
});

it('never turns technical read failures into MISSING or UNKNOWN and keeps permission errors explicit', async () => {
  vi.mocked(requestJson).mockRejectedValueOnce(
    new MarketApiError(403, {
      code: 'FORBIDDEN',
      message: 'Denied',
      details: [],
      timestamp: '2026-11-14T10:00:00Z',
    }),
  );
  await expect(readQualificationPreview('trade-1', 'position-1')).rejects.toThrow(
    'Keine Berechtigung',
  );
  vi.mocked(requestJson).mockRejectedValueOnce(new Error('network unavailable'));
  await expect(readTargetRequest('trade-1', 'position-1', 'request-1')).rejects.toThrow(
    'bleiben erhalten',
  );
});

it('accepts UNKNOWN only with no purported assessment, qualification or recorded time', async () => {
  const unknown = targetRequest({
    status: 'UNKNOWN',
    recorded_at: null,
    assessment: null,
    qualification: null,
  });
  vi.mocked(requestJson).mockResolvedValueOnce(unknown);
  expect(await readTargetRequest('trade-1', 'position-1', unknown.request_id)).toBe(unknown);
  for (const invalid of [
    { ...unknown, recorded_at: '2026-11-14T10:00:00Z' },
    { ...unknown, assessment: targetAssessment() },
    { ...unknown, qualification: comparisonQualification() },
    { ...unknown, status: 'FAILED' },
    { ...targetRequest(), request_id: 'other' },
    { ...targetRequest(), position_id: 'other' },
    { ...targetRequest(), trade_id: 'other' },
    { ...targetRequest(), assessment: null },
    { ...targetRequest(), recorded_at: null },
    { ...targetRequest(), read_completed_at: '2026-11-14T10:00:00' },
    { ...targetRequest(), operation_status: 'ACTIVATED' },
  ]) {
    vi.mocked(requestJson).mockResolvedValueOnce(invalid);
    await expect(readTargetRequest('trade-1', 'position-1', unknown.request_id)).rejects.toThrow(
      'Schreibausgang bleibt unbestätigt',
    );
  }
});

it.each([400, 403, 409, 422, 429, 500, 503])(
  'classifies HTTP %s without silently retrying a command',
  async (status) => {
    vi.mocked(requestJson).mockRejectedValueOnce(
      new MarketApiError(status, {
        code: 'EXPLICIT_REASON',
        message: 'Konkreter Ablehnungsgrund.',
        details: [],
        timestamp: '2026-11-14T10:00:00Z',
      }),
    );
    const payload = {
      position_id: 'position-1',
      request_id: targetRequest().request_id,
      expected_basis_id: 'basis-1',
      expected_assessment_id: null,
      confirmation: 'ASSESS_SAVED_HEBELTRADER_EVIDENCE' as const,
    };
    const error = await assessHebeltraderTargets('trade-1', payload).catch(
      (reason: unknown) => reason,
    );
    expect(error).toBeInstanceOf(HebeltraderCommandError);
    expect(error).toMatchObject({
      outcome: status < 500 ? 'REJECTED' : 'UNKNOWN',
      code: 'EXPLICIT_REASON',
    });
    expect(requestJson).toHaveBeenCalledOnce();
  },
);

it('treats a malformed success response as an unknown write, never a retryable concrete rejection', async () => {
  vi.mocked(requestJson).mockResolvedValueOnce({ status: 'OK' });
  await expect(
    assessHebeltraderTargets('trade-1', {
      position_id: 'position-1',
      request_id: targetRequest().request_id,
      expected_basis_id: 'basis-1',
      expected_assessment_id: null,
      confirmation: 'ASSESS_SAVED_HEBELTRADER_EVIDENCE',
    }),
  ).rejects.toMatchObject({ outcome: 'UNKNOWN' });
  expect(requestJson).toHaveBeenCalledOnce();
});
