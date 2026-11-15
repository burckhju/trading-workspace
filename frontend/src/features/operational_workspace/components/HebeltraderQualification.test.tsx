import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { TargetQualificationPreview } from '../hebeltraderQualification';
import type { HebeltraderTargetsReport } from '../hebeltraderTargets';
import { readQualificationPreview, readTargetRequest } from '../services/hebeltraderQualification';
import {
  assessHebeltraderTargets,
  HebeltraderCommandError,
  readHebeltraderTargets,
} from '../services/hebeltraderTargets';
import {
  comparisonQualification,
  historicalPrice,
  qualificationPreview,
  targetRequest,
} from '../test/hebeltraderQualificationFixture';
import { targetAssessment, targetReport } from '../test/hebeltraderTargetsFixture';
import { HebeltraderTargetHistory } from './HebeltraderTargetHistory';

vi.mock('../services/hebeltraderTargets', async (original) => ({
  ...(await original<typeof import('../services/hebeltraderTargets')>()),
  readHebeltraderTargets: vi.fn(),
  assessHebeltraderTargets: vi.fn(),
}));
vi.mock('../services/hebeltraderQualification', () => ({
  readQualificationPreview: vi.fn(),
  readTargetRequest: vi.fn(),
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
const reference = () =>
  screen.getByRole('textbox', {
    name: 'Konkreter Nachweis für historische Listingzuordnung und gemeinsamen Originalmaßstab',
  });
const confirm = () =>
  screen.getByRole('button', {
    name: 'Historische Zuordnung und Originalmaßstab bestätigen und prüfen',
  });
const assess = () => screen.getByRole('button', { name: 'Gespeicherte Belege prüfen' });
const receiptButton = () =>
  screen.getByRole('button', { name: 'Beleg genau dieser Anfrage lesen' });

beforeEach(() => {
  vi.mocked(readHebeltraderTargets)
    .mockReset()
    .mockImplementation((tradeId, positionId) =>
      Promise.resolve({
        ...qualificationPreview().report,
        trade_id: tradeId,
        position_id: positionId,
      }),
    );
  vi.mocked(readQualificationPreview)
    .mockReset()
    .mockImplementation((tradeId, positionId) => {
      const preview = qualificationPreview();
      preview.report = { ...preview.report, trade_id: tradeId, position_id: positionId };
      return Promise.resolve(preview);
    });
  vi.mocked(assessHebeltraderTargets).mockReset().mockResolvedValue(targetReport());
  vi.mocked(readTargetRequest).mockReset();
});

async function open(user: ReturnType<typeof userEvent.setup>) {
  await user.click(
    await screen.findByRole('button', { name: 'Historische Vergleichsbelege ansehen' }),
  );
  await screen.findByRole('table', { name: 'Gespeicherte Basiswert-Tageskurse' });
}
async function fill(
  user: ReturnType<typeof userEvent.setup>,
  value = comparisonQualification().evidence_reference,
) {
  await user.click(reference());
  await user.paste(value);
}

it('reads the preview only when requested and distinguishes original times, axes, metadata and activation', async () => {
  const user = userEvent.setup();
  render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('Noch keine gespeicherte Prüfung');
  expect(readQualificationPreview).not.toHaveBeenCalled();
  await open(user);
  expect(readQualificationPreview).toHaveBeenCalledExactlyOnceWith(
    'trade-1',
    'position-1',
    expect.any(AbortSignal),
  );
  expect(screen.getByText(/Basiswertmarken in USD/)).toHaveTextContent('Z1 110, Z2 120');
  expect(screen.getByText(/Einstieg: 2026-09-01/)).toHaveTextContent(
    'nur Datum, keine bekannte Uhrzeit',
  );
  expect(screen.getByText(/keine belegte Publikationsuhrzeit/)).toHaveTextContent('2026-08-03');
  expect(screen.getByText(/Aktuelle Listingreferenz/)).toHaveTextContent(
    'kann aus dem Listing stammen',
  );
  expect(screen.getByText(/Aktuelle Listingreferenz/)).toHaveTextContent(
    'technische Qualität allein',
  );
  expect(screen.getByText(/Kalendertag-Intervall: 2026-09-09T04:00:00Z/)).toHaveTextContent(
    'Nur tagesgenau',
  );
  expect(screen.getAllByText(/Quelle aktualisiert 2026-11-11T10:00:00Z/)[0]).toHaveTextContent(
    'Abgerufen 2026-11-12T10:00:00Z',
  );
  expect(screen.getByText('111.1234567891 USD')).toBeInTheDocument();
  expect(
    screen.getByText(/Eine Nutzererklärung ist keine unabhängige Verifikation/),
  ).toBeInTheDocument();
  expect(screen.getByText(/nicht als laufende Überwachung aktiviert/)).toBeInTheDocument();
  expect(screen.getByText(/B04\/B05\/B06\/B58/)).toBeInTheDocument();
  expect(assessHebeltraderTargets).not.toHaveBeenCalled();
  expect(readTargetRequest).not.toHaveBeenCalled();
});

it('submits one precise declaration with only the atomic preview tokens and a new UUID on explicit action', async () => {
  const user = userEvent.setup();
  const pending = deferred<HebeltraderTargetsReport>();
  vi.mocked(readHebeltraderTargets).mockResolvedValueOnce(
    targetReport({ current_basis_id: 'older-report-basis' }),
  );
  vi.mocked(assessHebeltraderTargets).mockReturnValueOnce(pending.promise);
  render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  await open(user);
  await fill(user, `  ${comparisonQualification().evidence_reference}  `);
  expect(assessHebeltraderTargets).not.toHaveBeenCalled();
  await user.dblClick(confirm());
  expect(assessHebeltraderTargets).toHaveBeenCalledOnce();
  const [trade, payload, signal] = vi.mocked(assessHebeltraderTargets).mock.calls[0];
  expect(trade).toBe('trade-1');
  expect(signal).toBeInstanceOf(AbortSignal);
  expect(payload.request_id).toMatch(/^[0-9a-f-]{36}$/);
  expect(payload).toEqual({
    position_id: 'position-1',
    request_id: payload.request_id,
    expected_basis_id: 'basis-1',
    expected_assessment_id: null,
    confirmation: 'ASSESS_SAVED_HEBELTRADER_EVIDENCE',
    qualification: {
      ...comparisonQualification(),
      confirmation: 'CONFIRM_HISTORICAL_LISTING_AND_UNCHANGED_ORIGINAL_SCALE',
    },
  });
  expect(confirm()).toBeDisabled();
  expect(reference()).toBeDisabled();
  expect(assess()).toBeDisabled();
  await act(async () => {
    pending.resolve(targetReport());
    await pending.promise;
  });
  expect(await screen.findByText(/Die ausdrückliche Prüfung wurde bestätigt/)).toBeInTheDocument();
  expect(reference()).toHaveValue(`  ${comparisonQualification().evidence_reference}  `);
  expect(confirm()).toBeDisabled();
  expect(screen.getByText(/Der gelesene Vergleichsstand ist überholt/)).toBeInTheDocument();
  expect(readQualificationPreview).toHaveBeenCalledOnce();
});

it.each(['', '   ', 'ab', 'x'.repeat(1001)])(
  'never sends an invalid reference (%s)',
  async (value) => {
    const user = userEvent.setup();
    render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
    await open(user);
    fireEvent.change(reference(), { target: { value } });
    expect(confirm()).toBeDisabled();
    await user.click(confirm());
    expect(assessHebeltraderTargets).not.toHaveBeenCalled();
  },
);

it('reuses an existing bound declaration without another reference input or a fictitious original confirmer', async () => {
  const preview = qualificationPreview({ report: targetReport() });
  preview.qualification = {
    ...preview.qualification,
    status: 'REUSABLE',
    value: comparisonQualification(),
    contained_in_assessment_id: 'assessment-7',
    contained_in_recorded_at: '2026-11-14T10:00:00Z',
  };
  vi.mocked(readQualificationPreview).mockResolvedValue(preview);
  const user = userEvent.setup();
  render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  await open(user);
  expect(screen.getByText(/Keine erneute Eingabe erforderlich/)).toBeInTheDocument();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(screen.getByText(/Enthalten in Prüfstand assessment-7/)).toHaveTextContent(
    'nicht den ursprünglichen Bestätiger',
  );
  await user.click(assess());
  expect(vi.mocked(assessHebeltraderTargets).mock.calls[0][1]).not.toHaveProperty('qualification');
});

it('keeps a stale declaration historical and copies it only as an explicit draft', async () => {
  const preview = qualificationPreview();
  preview.qualification = {
    ...preview.qualification,
    status: 'STALE',
    value: comparisonQualification({ source_version_id: 'old-source' }),
    contained_in_assessment_id: 'old-assessment',
    contained_in_recorded_at: '2026-11-01T10:00:00Z',
  };
  vi.mocked(readQualificationPreview).mockResolvedValue(preview);
  const user = userEvent.setup();
  render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  await open(user);
  expect(reference()).toHaveValue('');
  expect(confirm()).toBeDisabled();
  expect(screen.getByText(/hier nicht wiederverwendbar/)).toBeInTheDocument();
  await user.click(
    screen.getByRole('button', { name: 'Bisherige Belegreferenz als Entwurf übernehmen' }),
  );
  expect(reference()).toHaveValue(comparisonQualification().evidence_reference);
  expect(confirm()).toBeEnabled();
  expect(assessHebeltraderTargets).not.toHaveBeenCalled();
});

it.each(['BLOCKED', 'NOT_APPLICABLE'] as const)(
  'shows %s raw history and concrete global reasons without a checkbox override',
  async (status) => {
    const preview = qualificationPreview();
    preview.source_scale.source_scale_reference = null;
    preview.report.inputs.source_scale_reference = null;
    preview.qualification_binding = null;
    preview.readiness = {
      status,
      usable_row_count: 0,
      rows: [],
      issues: [
        {
          code: 'SOURCE_SCALE_UNVERIFIED',
          detail: 'Historischer Originalmaßstab ist nicht belegt.',
        },
      ],
    };
    if (status === 'NOT_APPLICABLE') preview.report.position_state = 'CLOSED';
    vi.mocked(readQualificationPreview).mockResolvedValue(preview);
    const user = userEvent.setup();
    render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
    await open(user);
    await fill(user);
    expect(screen.getByText(/Historischer Originalmaßstab ist nicht belegt/)).toBeInTheDocument();
    expect(
      screen.getAllByText('Wegen übergeordneter Sperre nicht zeilenweise geprüft'),
    ).toHaveLength(2);
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(confirm()).toBeDisabled();
    expect(
      within(
        screen.getByRole('region', { name: 'Historische Quelle für den Vergleich' }),
      ).getByText(/Maßstabsreferenz: Nicht belegt/),
    ).toBeInTheDocument();
    expect(assessHebeltraderTargets).not.toHaveBeenCalled();
  },
);

it('keeps the complete comparison scope visible while paging original rows locally without more reads', async () => {
  const preview = qualificationPreview();
  preview.history.rows = Array.from({ length: 26 }, (_, i) =>
    historicalPrice({
      source_row_id: `price-${i}`,
      fingerprint: `fingerprint-${i}`,
      high: String(100 + i),
    }),
  );
  preview.history.rows_observed = 26;
  preview.report.inputs.available_price_rows = 26;
  preview.readiness.rows = preview.history.rows.map((row) => ({
    source_row_id: row.source_row_id,
    fingerprint: row.fingerprint,
    status: 'SUITABLE_AFTER_CONFIRMATION',
    issues: [],
  }));
  preview.readiness.usable_row_count = 26;
  vi.mocked(readQualificationPreview).mockResolvedValue(preview);
  const user = userEvent.setup();
  render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  await open(user);
  const table = screen.getByRole('table', { name: 'Gespeicherte Basiswert-Tageskurse' });
  expect(within(table).getAllByRole('row')).toHaveLength(26);
  expect(screen.getByText(/gesamten benannten Bereich, nicht nur/)).toHaveTextContent(
    '26 angezeigbare Kursbelege',
  );
  await user.click(screen.getByRole('button', { name: 'Nächste Kursseite' }));
  expect(within(table).getAllByRole('row')).toHaveLength(2);
  expect(within(table).getByText('125 USD')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Vorherige Kursseite' }));
  expect(within(table).getAllByRole('row')).toHaveLength(26);
  expect(readQualificationPreview).toHaveBeenCalledOnce();
});

it('preserves the reference on a failed preview and invalidates its binding after an explicit changed-basis read', async () => {
  const user = userEvent.setup();
  render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  await open(user);
  await fill(user, 'Privater Beleg vom 10. September, Seite 7');
  vi.mocked(readQualificationPreview).mockRejectedValueOnce(new Error('Lesen fehlgeschlagen.'));
  await user.click(screen.getByRole('button', { name: 'Vergleichsbelege erneut lesen' }));
  await screen.findByText('Lesen fehlgeschlagen.');
  const next = qualificationPreview();
  next.report.current_basis_id = 'basis-2';
  vi.mocked(readQualificationPreview).mockResolvedValueOnce(next);
  await user.click(screen.getByRole('button', { name: 'Vergleichsbelege erneut lesen' }));
  await screen.findByRole('textbox');
  expect(reference()).toHaveValue('Privater Beleg vom 10. September, Seite 7');
  expect(confirm()).toBeDisabled();
  expect(screen.getByText(/nicht automatisch auf die neue Basis übertragen/)).toBeInTheDocument();
  await user.click(
    screen.getByRole('button', { name: 'Entwurf nach Prüfung auf diesen Belegstand beziehen' }),
  );
  expect(confirm()).toBeEnabled();
  expect(assessHebeltraderTargets).not.toHaveBeenCalled();
});

it.each(['resolve', 'reject'] as const)(
  'ignores a late preview %s across A → B → A without losing the A draft',
  async (outcome) => {
    const user = userEvent.setup();
    const late = deferred<TargetQualificationPreview>();
    const view = render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
    await open(user);
    await fill(user, 'A Beleg bleibt');
    vi.mocked(readQualificationPreview).mockReturnValueOnce(late.promise);
    await user.click(screen.getByRole('button', { name: 'Vergleichsbelege erneut lesen' }));
    view.rerender(<HebeltraderTargetHistory tradeId="trade-2" positionId="position-2" />);
    await screen.findByText('Noch keine gespeicherte Prüfung');
    view.rerender(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
    await screen.findByRole('textbox');
    expect(reference()).toHaveValue('A Beleg bleibt');
    await act(async () => {
      if (outcome === 'resolve') {
        const old = qualificationPreview();
        old.source!.filename = 'OLD.pdf';
        late.resolve(old);
      } else late.reject(new Error('Alter Lesefehler'));
      await late.promise.catch(() => undefined);
    });
    expect(screen.queryByText(/OLD.pdf|Alter Lesefehler/)).not.toBeInTheDocument();
    expect(reference()).toHaveValue('A Beleg bleibt');
    expect(vi.mocked(readQualificationPreview).mock.calls[1][2]?.aborted).toBe(true);
  },
);

it('does not replace a confirmed same-ID retry with a preview begun while that request was UNKNOWN', async () => {
  const user = userEvent.setup();
  const latePreview = deferred<TargetQualificationPreview>();
  vi.mocked(assessHebeltraderTargets).mockRejectedValueOnce(new Error('Transportabbruch'));
  const view = render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  await open(user);
  await fill(user);
  await user.click(confirm());
  await screen.findByText('Transportabbruch');
  const payload = vi.mocked(assessHebeltraderTargets).mock.calls[0][1];
  view.rerender(<HebeltraderTargetHistory tradeId="trade-2" positionId="position-2" />);
  await screen.findByText('Noch keine gespeicherte Prüfung');
  vi.mocked(readQualificationPreview).mockReturnValueOnce(latePreview.promise);
  view.rerender(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('Gespeicherte Vergleichsbelege werden gelesen …');
  const confirmed = targetReport({
    latest_assessment: targetAssessment({ id: 'retry-confirmed-assessment' }),
  });
  vi.mocked(assessHebeltraderTargets).mockResolvedValueOnce(confirmed);
  await user.click(
    screen.getByRole('button', { name: 'Denselben eingefrorenen Prüfauftrag erneut senden' }),
  );
  await screen.findByText(/Prüfung retry-confirmed-assessment/);
  await act(async () => {
    latePreview.resolve(qualificationPreview());
    await latePreview.promise;
  });
  expect(screen.getByText(/Prüfung retry-confirmed-assessment/)).toBeInTheDocument();
  expect(screen.queryByText('Noch keine gespeicherte Prüfung')).not.toBeInTheDocument();
  expect(screen.getByText(/Der gelesene Vergleichsstand ist überholt/)).toBeInTheDocument();
  expect(confirm()).toBeDisabled();
  expect(vi.mocked(assessHebeltraderTargets).mock.calls[1][1]).toBe(payload);
});

it('retains UNKNOWN for the first attempt when a same-ID retry is concretely rejected', async () => {
  const user = userEvent.setup();
  vi.mocked(assessHebeltraderTargets)
    .mockRejectedValueOnce(new Error('Transportabbruch'))
    .mockRejectedValueOnce(
      new HebeltraderCommandError('Berechtigung geändert.', 'REJECTED', 'FORBIDDEN'),
    );
  render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  await open(user);
  await fill(user);
  await user.click(confirm());
  await screen.findByText('Transportabbruch');
  const original = vi.mocked(assessHebeltraderTargets).mock.calls[0][1];
  await user.click(
    screen.getByRole('button', { name: 'Denselben eingefrorenen Prüfauftrag erneut senden' }),
  );
  expect(await screen.findByText(/Die Wiederholung wurde abgelehnt/)).toHaveTextContent(
    'Ausgang der ursprünglichen Anfrage bleibt unbestätigt',
  );
  expect(screen.getByRole('region', { name: 'Unbestätigter Prüfauftrag' })).toBeInTheDocument();
  expect(confirm()).toBeDisabled();
  expect(assess()).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Gespeicherten Prüfstand erneut lesen' }));
  await screen.findByRole('textbox');
  expect(confirm()).toBeDisabled();
  expect(reference()).toHaveValue(comparisonQualification().evidence_reference);
  expect(vi.mocked(assessHebeltraderTargets).mock.calls[1][1]).toBe(original);
  expect(screen.queryByText(/Die Anfrage wurde konkret abgelehnt/)).not.toBeInTheDocument();
  expect(readTargetRequest).not.toHaveBeenCalled();
});

it('preserves a concretely rejected draft, requires a fresh stand and does not label the write unknown', async () => {
  vi.mocked(assessHebeltraderTargets).mockRejectedValueOnce(
    new HebeltraderCommandError('Maßstab geändert.', 'REJECTED', 'SCALE_CHANGED'),
  );
  const user = userEvent.setup();
  render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  await open(user);
  await fill(user);
  await user.click(confirm());
  expect(await screen.findByText('Maßstab geändert.')).toBeInTheDocument();
  expect(reference()).toHaveValue(comparisonQualification().evidence_reference);
  expect(confirm()).toBeDisabled();
  expect(
    screen.queryByRole('region', { name: 'Unbestätigter Prüfauftrag' }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Vergleichsbelege erneut lesen' }));
  await screen.findByRole('textbox');
  expect(confirm()).toBeEnabled();
  expect(assessHebeltraderTargets).toHaveBeenCalledOnce();
});

it('retains an unknown frozen request through generic reads, UNKNOWN receipt and technical receipt failure until exact recovery', async () => {
  vi.mocked(assessHebeltraderTargets).mockRejectedValueOnce(
    new HebeltraderCommandError('Ausgang unbestätigt.', 'UNKNOWN'),
  );
  const user = userEvent.setup();
  render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  await open(user);
  await fill(user);
  await user.click(confirm());
  await screen.findByText('Ausgang unbestätigt.');
  const payload = vi.mocked(assessHebeltraderTargets).mock.calls[0][1];
  await user.click(screen.getByRole('button', { name: 'Gespeicherten Prüfstand erneut lesen' }));
  await screen.findByRole('textbox');
  expect(reference()).toHaveValue(comparisonQualification().evidence_reference);
  expect(confirm()).toBeDisabled();
  vi.mocked(readTargetRequest).mockResolvedValueOnce(
    targetRequest({
      request_id: payload.request_id,
      status: 'UNKNOWN',
      recorded_at: null,
      assessment: null,
      qualification: null,
    }),
  );
  await user.click(receiptButton());
  expect(await screen.findByText(/Dies beweist weder ein Scheitern/)).toBeInTheDocument();
  expect(confirm()).toBeDisabled();
  vi.mocked(readTargetRequest).mockRejectedValueOnce(
    new Error('Vorgangslesen technisch gescheitert.'),
  );
  await user.click(receiptButton());
  await screen.findByText('Vorgangslesen technisch gescheitert.');
  expect(confirm()).toBeDisabled();
  vi.mocked(readTargetRequest).mockResolvedValueOnce(
    targetRequest({
      request_id: payload.request_id,
      assessment: targetAssessment({ id: 'exact-request-assessment' }),
    }),
  );
  await user.click(receiptButton());
  expect(
    await screen.findByText(/Damals enthaltener Prüfstand: exact-request-assessment/),
  ).toBeInTheDocument();
  expect(screen.getByText(/Vorgang gespeichert: 2026-11-14T10:00:01Z/)).toBeInTheDocument();
  expect(screen.getByText(/Dieser Beleg bestätigt die konkrete Anfrage/)).toBeInTheDocument();
  expect(
    screen.queryByRole('region', { name: 'Unbestätigter Prüfauftrag' }),
  ).not.toBeInTheDocument();
  expect(assessHebeltraderTargets).toHaveBeenCalledOnce();
  for (const call of vi.mocked(readTargetRequest).mock.calls)
    expect(call).toEqual(['trade-1', 'position-1', payload.request_id, expect.any(AbortSignal)]);
});

it.each(['basis', 'qualification'] as const)(
  'keeps a mismatched %s receipt unknown and retries only the same explicit frozen command',
  async (mismatch) => {
    vi.mocked(assessHebeltraderTargets).mockRejectedValueOnce(new Error('Transportabbruch'));
    const user = userEvent.setup();
    render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
    await open(user);
    await fill(user);
    await user.click(confirm());
    await screen.findByText('Transportabbruch');
    const original = vi.mocked(assessHebeltraderTargets).mock.calls[0][1];
    const receipt = targetRequest({ request_id: original.request_id });
    if (mismatch === 'basis') receipt.assessment!.basis_id = 'other';
    else receipt.qualification!.evidence_reference = 'other';
    vi.mocked(readTargetRequest).mockResolvedValueOnce(receipt);
    await user.click(receiptButton());
    expect(
      await screen.findByText(/passt nicht zum eingefrorenen Prüfauftrag/),
    ).toBeInTheDocument();
    expect(confirm()).toBeDisabled();
    expect(assessHebeltraderTargets).toHaveBeenCalledOnce();
    await user.click(
      screen.getByRole('button', { name: 'Denselben eingefrorenen Prüfauftrag erneut senden' }),
    );
    await screen.findByText(/Die ausdrückliche Prüfung wurde bestätigt/);
    expect(assessHebeltraderTargets).toHaveBeenCalledTimes(2);
    expect(vi.mocked(assessHebeltraderTargets).mock.calls[1][1]).toBe(original);
  },
);

it.each(['resolve', 'reject'] as const)(
  'keeps a pending command frozen and ignores its late %s across A → B → A',
  async (outcome) => {
    const user = userEvent.setup();
    const late = deferred<HebeltraderTargetsReport>();
    vi.mocked(assessHebeltraderTargets).mockReturnValueOnce(late.promise);
    const view = render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
    await open(user);
    await fill(user, 'A Originalbeleg');
    await user.click(confirm());
    const original = vi.mocked(assessHebeltraderTargets).mock.calls[0][1];
    view.rerender(<HebeltraderTargetHistory tradeId="trade-2" positionId="position-2" />);
    await screen.findByText('Noch keine gespeicherte Prüfung');
    expect(screen.queryByText(/Eingefrorene Belegreferenz/)).not.toBeInTheDocument();
    view.rerender(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
    await screen.findByRole('textbox');
    await act(async () => {
      if (outcome === 'resolve')
        late.resolve(
          targetReport({ latest_assessment: targetAssessment({ id: 'obsolete-assessment' }) }),
        );
      else late.reject(new Error('Alter Schreibfehler'));
      await late.promise.catch(() => undefined);
    });
    expect(screen.queryByText(/obsolete-assessment|Alter Schreibfehler/)).not.toBeInTheDocument();
    expect(reference()).toHaveValue('A Originalbeleg');
    expect(confirm()).toBeDisabled();
    expect(
      screen.getByText(`Eingefrorene Belegreferenz: ${original.qualification!.evidence_reference}`),
    ).toBeInTheDocument();
    expect(screen.getByText(new RegExp(original.request_id))).toBeInTheDocument();
    expect(assessHebeltraderTargets).toHaveBeenCalledOnce();
    expect(vi.mocked(assessHebeltraderTargets).mock.calls[0][2]?.aborted).toBe(true);
  },
);
