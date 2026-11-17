import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { position } from '../../../test/positionFixture';
import type { HebeltraderTargetsReport } from '../hebeltraderTargets';
import { operationalWorkspaceApiClient } from '../services/client';
import { readQualificationPreview, readTargetRequest } from '../services/hebeltraderQualification';
import { assessHebeltraderTargets, readHebeltraderTargets } from '../services/hebeltraderTargets';
import { qualificationPreview } from '../test/hebeltraderQualificationFixture';
import { targetAssessment, targetReport } from '../test/hebeltraderTargetsFixture';
import type { OperationalPositionsResponse } from '../types';
import { OpenPositionsPanel } from './OpenPositionsPanel';
import { OperationalWorkspacePage } from './OperationalWorkspacePage';

vi.mock('../services/client', () => ({
  operationalWorkspaceApiClient: {
    getActions: vi.fn(),
    getPositions: vi.fn(),
    getPositionAlertProjection: vi.fn(),
  },
}));
vi.mock('../services/hebeltraderTargets', async (original) => ({
  ...(await original<typeof import('../services/hebeltraderTargets')>()),
  readHebeltraderTargets: vi.fn(),
  assessHebeltraderTargets: vi.fn(),
}));
vi.mock('../services/hebeltraderQualification', () => ({
  readQualificationPreview: vi.fn(),
  readTargetRequest: vi.fn(),
}));
vi.mock('../components/PositionPriceHistory', () => ({ PositionPriceHistory: () => null }));
vi.mock('../components/HebeltraderEvidenceCoverage', () => ({
  HebeltraderEvidenceCoverage: () => null,
}));
vi.mock('../../alert/components/PositionRiskPanel', () => ({ PositionRiskPanel: () => null }));
vi.mock('./MarketDataRefreshPanel', () => ({ MarketDataRefreshPanel: () => null }));

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

beforeEach(() => {
  sessionStorage.clear();
  vi.mocked(operationalWorkspaceApiClient.getActions)
    .mockReset()
    .mockResolvedValue({ generated_at: '2026-11-14T10:00:00Z', actions: [] });
  vi.mocked(operationalWorkspaceApiClient.getPositions)
    .mockReset()
    .mockResolvedValue({ generated_at: '2026-11-14T10:00:00Z', positions: [position()] });
  vi.mocked(operationalWorkspaceApiClient.getPositionAlertProjection)
    .mockReset()
    .mockImplementation((tradeId) =>
      Promise.resolve({
        ...position().position_signal!,
        trade_id: tradeId,
        position_id: tradeId.replace('trade-', 'position-'),
      }),
    );
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

async function openDetails(user: ReturnType<typeof userEvent.setup>, index = 0) {
  await user.click((await screen.findAllByRole('button', { name: 'Details' }))[index]);
  const open = await screen.findByRole('button', {
    name: /Historische Vergleichsbelege ansehen|Vergleichsbelege schließen/,
  });
  if (open.textContent === 'Historische Vergleichsbelege ansehen') await user.click(open);
  await screen.findByRole('textbox');
}

it('preserves separate A/B drafts through detail closing, filters and page navigation without changing search input', async () => {
  const user = userEvent.setup();
  const positions = Array.from({ length: 26 }, (_, i) =>
    position({
      trade_id: `trade-${i}`,
      position_id: `position-${i}`,
      product_name: `Warrant ${String(i).padStart(2, '0')}`,
    }),
  );
  render(
    <MemoryRouter>
      <OpenPositionsPanel positions={positions} />
    </MemoryRouter>,
  );
  await user.selectOptions(screen.getByLabelText('Sortierung'), 'product');
  await openDetails(user);
  await user.click(reference());
  await user.paste('A: eigener Originalbeleg');
  await user.click(screen.getByRole('button', { name: 'Details schließen' }));
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  await openDetails(user);
  expect(reference()).toHaveValue('A: eigener Originalbeleg');
  await user.click(screen.getByRole('button', { name: 'Datenprobleme' }));
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Alle offenen Positionen' }));
  await screen.findByRole('textbox');
  expect(reference()).toHaveValue('A: eigener Originalbeleg');
  await user.click(screen.getByRole('button', { name: 'Nächste Seite' }));
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Vorherige Seite' }));
  await screen.findByRole('textbox');
  expect(reference()).toHaveValue('A: eigener Originalbeleg');
  // A is expanded, so the first remaining closed Details button belongs to B.
  await openDetails(user);
  expect(reference()).toHaveValue('');
  await user.click(reference());
  await user.paste('B: andere historische Quelle');
  const rowA = screen
    .getByRole('region', { name: 'Positionstabelle, horizontal und vertikal scrollbar' })
    .querySelector('tr[data-position-id="position-0"]')!;
  await user.click(within(rowA as HTMLElement).getByRole('button', { name: 'Details' }));
  await screen.findByRole('textbox');
  expect(reference()).toHaveValue('A: eigener Originalbeleg');
  await user.click(screen.getByRole('searchbox'));
  await user.paste('Warrant 00');
  expect(screen.getByRole('searchbox')).toHaveValue('Warrant 00');
  expect(reference()).toHaveValue('A: eigener Originalbeleg');
  expect(assessHebeltraderTargets).not.toHaveBeenCalled();
  expect(JSON.stringify(sessionStorage)).not.toContain('Originalbeleg');
});

it('keeps the draft through the existing details reloadToken without affecting adjacent position input', async () => {
  const user = userEvent.setup();
  const p = position();
  const view = render(
    <MemoryRouter>
      <OpenPositionsPanel positions={[p]} />
    </MemoryRouter>,
  );
  await user.click(screen.getByRole('searchbox'));
  await user.paste('Test');
  await openDetails(user);
  await user.click(reference());
  await user.paste('Unveränderter Referenzentwurf');
  view.rerender(
    <MemoryRouter>
      <OpenPositionsPanel positions={[{ ...p, open_quantity: p.open_quantity + 1 }]} />
    </MemoryRouter>,
  );
  await screen.findByRole('textbox');
  expect(reference()).toHaveValue('Unveränderter Referenzentwurf');
  expect(screen.getByRole('searchbox')).toHaveValue('Test');
  expect(readQualificationPreview).toHaveBeenCalledTimes(2);
  expect(vi.mocked(readQualificationPreview).mock.calls[0][2]?.aborted).toBe(true);
  expect(assessHebeltraderTargets).not.toHaveBeenCalled();
});

it.each(['PENDING', 'UNKNOWN'] as const)(
  'retains a %s frozen command across global refresh, including a failed reload',
  async (phase) => {
    const user = userEvent.setup();
    const write = deferred<HebeltraderTargetsReport>();
    const refresh = deferred<OperationalPositionsResponse>();
    if (phase === 'PENDING') vi.mocked(assessHebeltraderTargets).mockReturnValueOnce(write.promise);
    else
      vi.mocked(assessHebeltraderTargets).mockRejectedValueOnce(
        new Error('Unbestätigter Schreibausgang'),
      );
    render(
      <MemoryRouter>
        <OperationalWorkspacePage />
      </MemoryRouter>,
    );
    await openDetails(user);
    await user.click(reference());
    await user.paste('Erhaltener Beleg bei Aktualisierung');
    await user.click(confirm());
    if (phase === 'UNKNOWN') await screen.findByText('Unbestätigter Schreibausgang');
    const original = vi.mocked(assessHebeltraderTargets).mock.calls[0][1];
    vi.mocked(operationalWorkspaceApiClient.getPositions).mockReturnValueOnce(refresh.promise);
    await user.click(screen.getByRole('button', { name: 'Aktualisieren' }));
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    if (phase === 'UNKNOWN') {
      await act(async () => {
        refresh.reject(new Error('Positionslesen fehlgeschlagen'));
        await refresh.promise.catch(() => undefined);
      });
      await screen.findByText('Positionslesen fehlgeschlagen');
      await user.click(screen.getByRole('button', { name: 'Erneut versuchen' }));
    } else
      await act(async () => {
        refresh.resolve({
          generated_at: '2026-11-14T11:00:00Z',
          positions: [position({ open_quantity: 11 })],
        });
        await refresh.promise;
      });
    await openDetails(user);
    expect(reference()).toHaveValue('Erhaltener Beleg bei Aktualisierung');
    expect(confirm()).toBeDisabled();
    expect(screen.getByRole('region', { name: 'Unbestätigter Prüfauftrag' })).toBeInTheDocument();
    expect(screen.getByText(new RegExp(original.request_id))).toBeInTheDocument();
    expect(screen.getByText(/Eingefrorene Belegreferenz: Erhaltener Beleg/)).toBeInTheDocument();
    if (phase === 'PENDING') {
      expect(vi.mocked(assessHebeltraderTargets).mock.calls[0][2]?.aborted).toBe(true);
      await act(async () => {
        write.resolve(
          targetReport({ latest_assessment: targetAssessment({ id: 'late-obsolete-assessment' }) }),
        );
        await write.promise;
      });
      expect(screen.queryByText(/late-obsolete-assessment/)).not.toBeInTheDocument();
      expect(confirm()).toBeDisabled();
    }
    expect(assessHebeltraderTargets).toHaveBeenCalledOnce();
    expect(readTargetRequest).not.toHaveBeenCalled();
  },
);

it('states and respects the Workspace route lifetime instead of storing private drafts in browser storage', async () => {
  const user = userEvent.setup();
  const view = render(
    <MemoryRouter>
      <OperationalWorkspacePage />
    </MemoryRouter>,
  );
  await openDetails(user);
  await user.click(reference());
  await user.paste('Synthetischer privater Nachweis');
  expect(
    screen.getByText(/Beim Verlassen der Workspace-Seite oder Neuladen im Browser/),
  ).toBeInTheDocument();
  view.unmount();
  render(
    <MemoryRouter>
      <OperationalWorkspacePage />
    </MemoryRouter>,
  );
  await openDetails(user);
  expect(reference()).toHaveValue('');
  expect(JSON.stringify(sessionStorage)).not.toContain('privater Nachweis');
  expect(JSON.stringify(localStorage)).not.toContain('privater Nachweis');
});
