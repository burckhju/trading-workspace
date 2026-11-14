import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { position } from '../../../test/positionFixture';
import type { HebeltraderTargetsReport } from '../hebeltraderTargets';
import { assessHebeltraderTargets, readHebeltraderTargets } from '../services/hebeltraderTargets';
import { targetAssessment, targetReport } from '../test/hebeltraderTargetsFixture';
import { HebeltraderTargetHistory } from './HebeltraderTargetHistory';
import { PositionDetails } from './PositionDetails';

vi.mock('../services/hebeltraderTargets', () => ({
  readHebeltraderTargets: vi.fn(),
  assessHebeltraderTargets: vi.fn(),
}));
vi.mock('./PositionPriceHistory', () => ({ PositionPriceHistory: () => null }));
vi.mock('./HebeltraderEvidenceCoverage', () => ({ HebeltraderEvidenceCoverage: () => null }));
vi.mock('../../alert/components/PositionRiskPanel', () => ({ PositionRiskPanel: () => null }));

beforeEach(() => {
  vi.mocked(readHebeltraderTargets)
    .mockReset()
    .mockImplementation((tradeId, positionId) =>
      Promise.resolve(targetReport({ trade_id: tradeId, position_id: positionId })),
    );
  vi.mocked(assessHebeltraderTargets).mockReset().mockResolvedValue(targetReport());
});

function deferred() {
  let resolve!: (value: HebeltraderTargetsReport) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<HebeltraderTargetsReport>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

const button = () => screen.getByRole('button', { name: 'Gespeicherte Belege prüfen' });

it('renders durable day-only evidence and original quantities without declaring an active baseline or stop', async () => {
  render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  expect(button()).toBeDisabled();
  await screen.findByText('Z1: Treffer belegt');
  expect(screen.getByText('Z2: Kein Treffer in verfügbaren Belegen')).toBeInTheDocument();
  expect(screen.getByText('Ein fehlender Trefferbeleg ist keine Entwarnung.')).toBeInTheDocument();
  expect(screen.getByText(/Basiswertmarke: 110.123456789 USD/)).toBeInTheDocument();
  expect(screen.getByText(/Nur tagesgenau belegt; Trefferuhrzeit/)).toBeInTheDocument();
  expect(screen.getByText(/Ursprüngliche Bezugsmenge: 7.*Z1-Verkäufe: 2/)).toBeInTheDocument();
  expect(
    screen.getByText(/50 % der ursprünglichen Einstiegsmenge sind eine Orientierung/),
  ).toBeInTheDocument();
  expect(screen.queryByText(/3[,.]5/)).not.toBeInTheDocument();
  expect(
    screen.getByText(/Persönlicher Basiswert-Einstieg: 100.987654321 USD/),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/kein bekanntgegebener oder überwachter Schutzvorschlag/),
  ).toBeInTheDocument();
  expect(screen.getByText(/nicht als laufende Überwachung aktiviert/)).toBeInTheDocument();
  expect(screen.getByText(/Quellenbasis dieses Prüflaufs: source-version-1/)).toBeInTheDocument();
  expect(readHebeltraderTargets).toHaveBeenCalledOnce();
  expect(assessHebeltraderTargets).not.toHaveBeenCalled();
});

it('keeps an absent assessment and missing comparison qualification distinct from a clear result', async () => {
  vi.mocked(readHebeltraderTargets).mockResolvedValue(
    targetReport({
      latest_assessment: null,
      assessment_count: 0,
      currentness: 'NO_ASSESSMENT',
      inputs: {
        ...targetReport().inputs,
        qualification_reusable: false,
        issues: ['PRICE_QUALIFICATION_MISSING'],
      },
    }),
  );
  render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('Noch keine gespeicherte Prüfung');
  expect(screen.getByText(/Vergleichsqualifikation.*fehlt oder passt nicht/)).toBeInTheDocument();
  expect(screen.getByText('PRICE_QUALIFICATION_MISSING')).toBeInTheDocument();
  expect(screen.queryByRole('list', { name: 'Gespeicherte Zielbefunde' })).not.toBeInTheDocument();
  expect(assessHebeltraderTargets).not.toHaveBeenCalled();
});

it('keeps the original A proof source and scale after a B-source review assessment', async () => {
  const assessment = targetAssessment();
  vi.mocked(readHebeltraderTargets).mockResolvedValue(
    targetReport({
      currentness: 'CHANGED_INPUTS',
      current_basis_id: 'basis-2',
      inputs: { ...targetReport().inputs, source_version_id: 'source-version-2' },
      latest_assessment: targetAssessment({
        source_version_id: 'source-version-2',
        targets: [
          {
            ...assessment.targets[0],
            status: 'REVIEW_REQUIRED',
            detail: 'Korrektur des ursprünglichen Belegs prüfen.',
            reasons: ['CORRECTION'],
          },
          {
            ...assessment.targets[1],
            status: 'NOT_ASSESSABLE',
            detail: 'Maßstabsnachweis fehlt.',
            reasons: ['SCALE_UNKNOWN'],
          },
        ],
      }),
    }),
  );
  render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('Eingaben seit der Prüfung geändert');
  expect(screen.getByText(/Die angezeigte Prüfung ist historisch/)).toBeInTheDocument();
  expect(screen.getByText('Z1: Erneute Prüfung erforderlich')).toBeInTheDocument();
  expect(screen.getByText('Z2: Nicht beurteilbar')).toBeInTheDocument();
  expect(screen.getByText('Korrektur des ursprünglichen Belegs prüfen.')).toBeInTheDocument();
  expect(screen.getByText('Maßstabsnachweis fehlt.')).toBeInTheDocument();
  expect(screen.getByText(/Ereignis: event-z1/)).toBeInTheDocument();
  expect(screen.getByText(/Basiswertmarke: 110.123456789 USD/)).toBeInTheDocument();
  expect(screen.getByText(/Ursprüngliche Zielquelle: source-version-1/)).toHaveTextContent(
    'Maßstabsreferenz des Zielbelegs: source-original-1',
  );
  expect(screen.queryByText(/Ursprüngliche Zielquelle: source-version-2/)).not.toBeInTheDocument();
  expect(screen.getByText(/Quellenbasis dieses Prüflaufs: source-version-2/)).toBeInTheDocument();
  expect(assessHebeltraderTargets).not.toHaveBeenCalled();
});

it.each([null, 'assessment-1'])(
  'assesses only after the explicit click with frozen basis, previous assessment %s and one UUID',
  async (previousAssessmentId) => {
    const user = userEvent.setup();
    const pending = deferred();
    if (previousAssessmentId === null) {
      vi.mocked(readHebeltraderTargets).mockResolvedValueOnce(
        targetReport({
          latest_assessment: null,
          assessment_count: 0,
          currentness: 'NO_ASSESSMENT',
        }),
      );
    }
    vi.mocked(assessHebeltraderTargets).mockReturnValueOnce(pending.promise);
    render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
    await screen.findByText(
      previousAssessmentId === null ? 'Noch keine gespeicherte Prüfung' : 'Z1: Treffer belegt',
    );
    await user.dblClick(button());
    expect(assessHebeltraderTargets).toHaveBeenCalledOnce();
    const [tradeId, payload, signal] = vi.mocked(assessHebeltraderTargets).mock.calls[0];
    const { request_id: requestId, ...body } = payload;
    expect(tradeId).toBe('trade-1');
    expect(requestId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    );
    expect(body).toEqual({
      position_id: 'position-1',
      expected_basis_id: 'basis-1',
      expected_assessment_id: previousAssessmentId,
      confirmation: 'ASSESS_SAVED_HEBELTRADER_EVIDENCE',
    });
    expect(signal).toBeInstanceOf(AbortSignal);
    expect(button()).toBeDisabled();
    await act(async () => {
      pending.resolve(
        targetReport({
          assessment_count: previousAssessmentId === null ? 1 : 2,
          latest_assessment: targetAssessment({
            id: 'assessment-2',
            previous_assessment_id: previousAssessmentId,
          }),
        }),
      );
      await pending.promise;
    });
    expect(screen.getByText(/Prüfung assessment-2/)).toBeInTheDocument();
    expect(button()).toBeEnabled();
    expect(readHebeltraderTargets).toHaveBeenCalledOnce();
  },
);

it('preserves draft input and requires deliberate readback after an uncertain write, without retrying it', async () => {
  const user = userEvent.setup();
  vi.mocked(assessHebeltraderTargets).mockRejectedValueOnce(new Error('Ausgang nicht bestätigt.'));
  render(
    <>
      <label>
        Verkaufsmenge
        <input defaultValue="7" />
      </label>
      <HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />
    </>,
  );
  await screen.findByText('Z1: Treffer belegt');
  await user.clear(screen.getByLabelText('Verkaufsmenge'));
  await user.type(screen.getByLabelText('Verkaufsmenge'), '3');
  await user.click(button());
  expect(await screen.findByRole('alert')).toHaveTextContent('Ausgang nicht bestätigt.');
  expect(button()).toBeDisabled();
  expect(
    screen.getByText(/angezeigte Stand ist nach dem Schreibversuch noch nicht bestätigt/),
  ).toBeInTheDocument();
  expect(readHebeltraderTargets).toHaveBeenCalledOnce();
  await user.click(screen.getByRole('button', { name: 'Gespeicherten Prüfstand erneut lesen' }));
  await screen.findByText('Z1: Treffer belegt');
  expect(screen.getByLabelText('Verkaufsmenge')).toHaveValue('3');
  expect(button()).toBeEnabled();
  expect(readHebeltraderTargets).toHaveBeenCalledTimes(2);
  expect(assessHebeltraderTargets).toHaveBeenCalledOnce();
});

it.each(['CLOSED', 'CANCELLED'] as const)(
  'keeps %s historical evidence readable with the command disabled',
  async (positionState) => {
    vi.mocked(readHebeltraderTargets).mockResolvedValue(
      targetReport({ position_state: positionState }),
    );
    const user = userEvent.setup();
    render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
    await screen.findByText('Z1: Treffer belegt');
    expect(
      screen.getByText(/gespeicherte Historie bleibt lesbar; keine neue Prüfung/),
    ).toBeInTheDocument();
    await user.click(button());
    expect(button()).toBeDisabled();
    expect(assessHebeltraderTargets).not.toHaveBeenCalled();
  },
);

it.each(['resolve', 'reject'] as const)(
  'ignores a late GET %s across A → B → A',
  async (outcome) => {
    const pending = deferred();
    vi.mocked(readHebeltraderTargets).mockReturnValueOnce(pending.promise);
    const view = render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
    view.rerender(<HebeltraderTargetHistory tradeId="trade-2" positionId="position-2" />);
    await screen.findByText('Z1: Treffer belegt');
    view.rerender(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
    await screen.findByText('Z1: Treffer belegt');
    await act(async () => {
      if (outcome === 'resolve') pending.resolve(targetReport({ currentness: 'CHANGED_INPUTS' }));
      else pending.reject(new Error('Alter Lesefehler'));
      await pending.promise.catch(() => undefined);
    });
    expect(screen.queryByText('Eingaben seit der Prüfung geändert')).not.toBeInTheDocument();
    expect(screen.queryByText('Alter Lesefehler')).not.toBeInTheDocument();
    expect(vi.mocked(readHebeltraderTargets).mock.calls[0][2]?.aborted).toBe(true);
    expect(assessHebeltraderTargets).not.toHaveBeenCalled();
  },
);

it.each(['resolve', 'reject'] as const)(
  'ignores a late POST %s after A → B → A without reissuing the command',
  async (outcome) => {
    const user = userEvent.setup();
    const pending = deferred();
    vi.mocked(assessHebeltraderTargets).mockReturnValueOnce(pending.promise);
    const view = render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
    await screen.findByText('Z1: Treffer belegt');
    await user.click(button());
    view.rerender(<HebeltraderTargetHistory tradeId="trade-2" positionId="position-2" />);
    await screen.findByText('Z1: Treffer belegt');
    view.rerender(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
    await screen.findByText('Z1: Treffer belegt');
    await act(async () => {
      if (outcome === 'resolve')
        pending.resolve(
          targetReport({ latest_assessment: targetAssessment({ id: 'obsolete-assessment' }) }),
        );
      else pending.reject(new Error('Alter Schreibfehler'));
      await pending.promise.catch(() => undefined);
    });
    expect(screen.queryByText(/obsolete-assessment|Alter Schreibfehler/)).not.toBeInTheDocument();
    expect(button()).toBeEnabled();
    expect(assessHebeltraderTargets).toHaveBeenCalledOnce();
    expect(vi.mocked(assessHebeltraderTargets).mock.calls[0][2]?.aborted).toBe(true);
  },
);

it('aborts reads and pending commands on a changed position, reload token and unmount', async () => {
  const user = userEvent.setup();
  const pending = deferred();
  vi.mocked(assessHebeltraderTargets).mockReturnValue(pending.promise);
  const view = render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  await screen.findByText('Z1: Treffer belegt');
  await user.click(button());
  view.rerender(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-2" />);
  await screen.findByText('Z1: Treffer belegt');
  view.rerender(
    <HebeltraderTargetHistory tradeId="trade-1" positionId="position-2" reloadToken="basis-2" />,
  );
  await screen.findByText('Z1: Treffer belegt');
  view.unmount();
  expect(readHebeltraderTargets).toHaveBeenCalledTimes(3);
  expect(vi.mocked(readHebeltraderTargets).mock.calls.every((call) => call[2]?.aborted)).toBe(true);
  expect(vi.mocked(assessHebeltraderTargets).mock.calls[0][2]?.aborted).toBe(true);
  await act(async () => {
    pending.resolve(targetReport());
    await pending.promise;
  });
});

it('retries an initial failed read explicitly without calling the assessment endpoint', async () => {
  vi.mocked(readHebeltraderTargets).mockRejectedValueOnce(
    new Error('Zielhistorie nicht verfügbar.'),
  );
  const user = userEvent.setup();
  render(<HebeltraderTargetHistory tradeId="trade-1" positionId="position-1" />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Zielhistorie nicht verfügbar.');
  expect(screen.queryByText('Noch keine gespeicherte Prüfung')).not.toBeInTheDocument();
  expect(button()).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Gespeicherten Prüfstand erneut lesen' }));
  await screen.findByText('Z1: Treffer belegt');
  expect(readHebeltraderTargets).toHaveBeenCalledTimes(2);
  expect(assessHebeltraderTargets).not.toHaveBeenCalled();
});

it('uses the existing details host and invalidates after its economic basis changes', async () => {
  const p = position({ trade_id: 'trade-1', position_id: 'position-1', position_basis: undefined });
  const view = render(
    <MemoryRouter>
      <PositionDetails position={p} />
    </MemoryRouter>,
  );
  await screen.findByText('Z1: Treffer belegt');
  expect(
    screen.getByRole('link', { name: 'Kauf-/Verkaufsdaten und Historie öffnen' }),
  ).toHaveAttribute('href', `${p.target}#execution-dates`);
  view.rerender(
    <MemoryRouter>
      <PositionDetails position={{ ...p, open_quantity: p.open_quantity + 1 }} />
    </MemoryRouter>,
  );
  await screen.findByText('Z1: Treffer belegt');
  expect(readHebeltraderTargets).toHaveBeenCalledTimes(2);
  expect(vi.mocked(readHebeltraderTargets).mock.calls[0][2]?.aborted).toBe(true);
  expect(assessHebeltraderTargets).not.toHaveBeenCalled();
});
