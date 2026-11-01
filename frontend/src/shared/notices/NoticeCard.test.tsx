import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, MemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { NoticeCard, NoticeDetails } from './NoticeCard';
import type {
  AuthorityRef,
  NoticeAction,
  NoticeDestination,
  NoticePresentation,
  NoticeView,
} from './types';

const proof: AuthorityRef = {
  owner: 'performance',
  contract: 'realized-gross-sell-v2',
  snapshotToken: 'basis-1',
  references: ['item:execution-1', 'source:buy-1', 'currency_resolution.reasons'],
};

const destination: NoticeDestination = {
  availability: 'verified-existing',
  href: '/trade/trade-1?report=realized-gross&basis=basis-1#execution-dates',
  builder: 'realizedTradeLink',
  subject: {
    identity: 'known-object',
    kind: 'trade',
    id: 'trade-1',
    label: 'Beispielprodukt',
    versionId: null,
  },
  granularity: 'section',
  relationshipProof: proof,
};

const noticeContent = {
  id: 'currency:execution-1',
  catalogRule: 'F1',
  title: 'Währungsherkunft dieses Verkaufs',
  cause: {
    known: true,
    explanation: 'Eine Kaufquelle enthält widersprüchliche Währungsangaben.',
    proof,
  },
  impact: 'Dieser Verkaufsbeitrag ist nicht berechenbar.',
  automatic: {
    kind: 'none-evidenced',
    explanation: 'Die gelesene Antwort enthält keine automatische Korrektur.',
  },
  userNeed: {
    kind: 'optional-inspection',
    explanation: 'Die betroffenen Buchungen können geprüft werden.',
  },
  time: {
    observedAt: null,
    checkedAt: null,
    validFrom: null,
    validTo: null,
    explanation: '',
  },
  details: [{ label: 'Kaufquelle', value: 'Brokerabrechnung vom 30.10.2026', proof }],
  actions: [{ kind: 'read', label: 'Buchungen ansehen', destination }],
} as const;

function makeNotice(
  presentation: NoticePresentation = { kind: 'warning', priority: 'relevant-problem' },
): NoticeView {
  if (presentation.kind === 'information' || presentation.kind === 'success') {
    return { ...noticeContent, presentation };
  }
  return { ...noticeContent, presentation };
}

function renderCard(notice = makeNotice(), headingLevel: 2 | 3 | 4 = 3) {
  return render(
    <MemoryRouter>
      <NoticeCard notice={notice} headingLevel={headingLevel} detailsId="notice-details" />
    </MemoryRouter>,
  );
}

function expectNoLiveAnnouncement(container: HTMLElement) {
  expect(container.querySelector('[role="alert"], [role="status"], [aria-live]')).toBeNull();
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('NoticeCard', () => {
  it.each<{ label: string; presentation: NoticePresentation }>([
    { label: 'Hinweis', presentation: { kind: 'information', priority: 'normal' } },
    { label: 'Warnung', presentation: { kind: 'warning', priority: 'relevant-problem' } },
    {
      label: 'Blockierung',
      presentation: {
        kind: 'blocker',
        priority: 'blocked-operation',
        blockedOperation: 'Verkaufsbeitrag berechnen',
        proof,
      },
    },
    {
      label: 'Fehler',
      presentation: {
        kind: 'error',
        priority: 'relevant-problem',
        failedOperation: 'Bericht lesen',
        proof,
      },
    },
    {
      label: 'Bestätigt',
      presentation: {
        kind: 'success',
        priority: 'normal',
        completedOperation: 'Buchung bestätigt',
        proof,
      },
    },
  ])('labels $label visibly without a live announcement', ({ label, presentation }) => {
    const { container } = renderCard(makeNotice(presentation));
    const region = screen.getByRole('region', { name: noticeContent.title });
    expect(within(region).getByText(label)).toBeVisible();
    expect(within(region).getByText(noticeContent.cause.explanation)).toBeVisible();
    expect(within(region).getByText(noticeContent.impact)).toBeVisible();
    expectNoLiveAnnouncement(container);
  });

  it.each([2, 3, 4] as const)('uses the requested native heading level %s', (headingLevel) => {
    renderCard(makeNotice(), headingLevel);
    expect(
      screen.getByRole('heading', { name: noticeContent.title, level: headingLevel }),
    ).toBeVisible();
  });

  it('uses native details without a read or write when opened', async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    const { container } = renderCard();
    const summary = screen.getByText('Ursache und Quellen');
    const details = summary.closest('details');
    expect(summary.tagName).toBe('SUMMARY');
    expect(details).not.toHaveAttribute('open');
    expect(screen.getByText(noticeContent.details[0].value)).not.toBeVisible();

    // Native summary keyboard/focus behavior is checked in the browser pilot;
    // jsdom/user-event does not model its tab stop.
    await user.click(summary);

    expect(details).toHaveAttribute('open');
    expect(screen.getByText(noticeContent.details[0].value)).toBeVisible();
    expect(fetchSpy).not.toHaveBeenCalled();
    expectNoLiveAnnouncement(container);
  });

  it('shows only supplied timestamps with their exact semantic labels', async () => {
    const user = userEvent.setup();
    const notice = {
      ...makeNotice(),
      time: {
        observedAt: '2026-10-30T12:30:00Z',
        checkedAt: '2026-11-01T08:00:00Z',
        validFrom: null,
        validTo: null,
        explanation: 'Die Prüfzeit stammt aus dem fachlichen Nachweis.',
      },
    };
    const { container } = renderCard(notice);
    await user.click(screen.getByText('Ursache und Quellen'));
    expect(screen.getByText('Fachlicher Zeitpunkt')).toBeVisible();
    expect(screen.getByText('Prüfzeit')).toBeVisible();
    expect(screen.queryByText('Gültig ab')).not.toBeInTheDocument();
    expect(screen.queryByText('Gültig bis ausschließlich')).not.toBeInTheDocument();
    expect([...container.querySelectorAll('time')].map((node) => node.dateTime)).toEqual([
      notice.time.observedAt,
      notice.time.checkedAt,
    ]);
  });

  it('does not invent timestamps or an empty details control', () => {
    const { container } = render(
      <NoticeDetails id="empty-details" rows={[]} time={noticeContent.time} />,
    );
    expect(container.querySelector('details')).toBeNull();
    expect(container.querySelector('time')).toBeNull();
  });

  it('labels the supplied validity end as exclusive', async () => {
    const user = userEvent.setup();
    renderCard({
      ...makeNotice(),
      time: {
        ...noticeContent.time,
        validFrom: '2026-10-01T00:00:00Z',
        validTo: '2026-11-01T00:00:00Z',
      },
    });
    await user.click(screen.getByText('Ursache und Quellen'));
    expect(screen.getByText('Gültig ab')).toBeVisible();
    expect(screen.getByText('Gültig bis ausschließlich')).toBeVisible();
    expect(screen.queryByText('Prüfzeit')).not.toBeInTheDocument();
  });

  it.each([
    '//example.org/trade',
    '/\\example.org/trade',
    '/\n/example.org/trade',
    'https://example.org/trade',
    'javascript:alert(1)',
    'data:text/html,unexpected',
    'file:///tmp/unexpected',
    'trade/trade-1',
  ])('does not activate an unsupported destination: %j', (href) => {
    renderCard({
      ...makeNotice(),
      actions: [
        { kind: 'read', label: 'Buchungen ansehen', destination: { ...destination, href } },
      ],
    });
    expect(screen.getByText('Buchungen ansehen')).toBeVisible();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it.each<NoticeAction>([
    { kind: 'read', label: 'Buchungen ansehen', destination },
    {
      kind: 'open-decision',
      label: 'Bestätigung prüfen',
      destination,
      decision: 'confirm',
      confirmation: 'explicit-in-owner',
    },
  ])('keeps $kind a navigation link without a read or write callback', async (action) => {
    const user = userEvent.setup();
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    const router = createMemoryRouter([
      {
        path: '/',
        element: (
          <NoticeCard
            notice={{ ...makeNotice(), actions: [action] }}
            headingLevel={3}
            detailsId="navigation-details"
          />
        ),
      },
      { path: '/trade/:tradeId', element: <h1>Buchungen</h1> },
    ]);
    render(<RouterProvider router={router} />);
    const link = screen.getByRole('link', { name: action.label });
    expect(link).toHaveAttribute('href', destination.href);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();

    await user.click(link);

    expect(screen.getByRole('heading', { name: 'Buchungen' })).toBeVisible();
    expect(router.state.location.pathname).toBe('/trade/trade-1');
    expect(router.state.location.search).toBe('?report=realized-gross&basis=basis-1');
    expect(router.state.location.hash).toBe('#execution-dates');
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('replaces facts and destinations without announcing a recovery or retaining stale values', async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    const initial = makeNotice();
    const { container, rerender } = renderCard(initial);
    await user.click(screen.getByText('Ursache und Quellen'));
    const primaryLink = screen.getByRole('link', { name: 'Buchungen ansehen' });
    primaryLink.focus();
    expect(primaryLink).toHaveFocus();
    const nextProof = { ...proof, snapshotToken: 'basis-2', references: ['source:buy-2'] };
    const next: NoticeView = {
      ...initial,
      title: 'Geprüfte Währungsherkunft dieses Verkaufs',
      cause: {
        known: true,
        explanation: 'Eine andere Kaufquelle ist betroffen.',
        proof: nextProof,
      },
      details: [
        { label: 'Aktuelle Kaufquelle', value: 'Korrigierte Brokerabrechnung', proof: nextProof },
      ],
      actions: [
        {
          kind: 'read',
          label: 'Aktuelle Buchungen ansehen',
          destination: {
            ...destination,
            href: '/trade/trade-1?report=realized-gross&basis=basis-2#execution-dates',
            relationshipProof: nextProof,
          },
        },
      ],
    };
    rerender(
      <MemoryRouter>
        <NoticeCard notice={next} headingLevel={3} detailsId="notice-details" />
      </MemoryRouter>,
    );

    expect(screen.queryByText(initial.title)).not.toBeInTheDocument();
    expect(screen.queryByText(initial.cause.explanation)).not.toBeInTheDocument();
    expect(screen.queryByText(initial.details[0].value)).not.toBeInTheDocument();
    expect(screen.getByText('Korrigierte Brokerabrechnung')).toBeVisible();
    expect(screen.getByRole('region', { name: next.title })).toHaveAttribute(
      'data-notice-id',
      initial.id,
    );
    expect(screen.getByRole('link', { name: 'Aktuelle Buchungen ansehen' })).toHaveAttribute(
      'href',
      next.actions[0].destination.href,
    );
    expect(screen.getByRole('link', { name: 'Aktuelle Buchungen ansehen' })).toHaveFocus();
    expectNoLiveAnnouncement(container);

    rerender(
      <MemoryRouter>
        <NoticeCard key="basis-2" notice={next} headingLevel={3} detailsId="notice-details" />
      </MemoryRouter>,
    );
    expect(screen.getByText('Ursache und Quellen').closest('details')).not.toHaveAttribute('open');
    expect(screen.queryByText('Bestätigt')).not.toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
    expectNoLiveAnnouncement(container);
  });

  it('preserves long labels and source values as text in their supplied detail context', async () => {
    const user = userEvent.setup();
    const longTitle = `Währungsherkunft ${'einer ausführlich benannten Buchung '.repeat(10)}`;
    const originalReference = `broker-reference:${'a'.repeat(500)}<script>untrusted()</script>`;
    const { container } = renderCard({
      ...makeNotice(),
      title: longTitle,
      details: [{ label: 'Originalreferenz', value: originalReference, proof }],
    });
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent(longTitle.trim());
    expect(screen.getByText(originalReference)).not.toBeVisible();
    await user.click(screen.getByText('Ursache und Quellen'));
    expect(screen.getByText(originalReference)).toBeVisible();
    expect(container.querySelector('script')).toBeNull();
    expect(container.querySelector('[title]')).toBeNull();
  });

  it('keeps additional navigation in details and distinct cards independently labelled', async () => {
    const user = userEvent.setup();
    const secondAction: NoticeAction = {
      kind: 'read',
      label: 'Produkt ansehen',
      destination: {
        ...destination,
        href: '/product/product-1',
        subject: {
          identity: 'known-object',
          kind: 'product',
          id: 'product-1',
          label: 'Beispielprodukt',
          versionId: null,
        },
      },
    };
    render(
      <MemoryRouter>
        <NoticeCard
          notice={{ ...makeNotice(), actions: [...noticeContent.actions, secondAction] }}
          headingLevel={3}
          detailsId="first-details"
        />
        <NoticeCard
          notice={{ ...makeNotice(), id: 'currency:execution-2', title: 'Zweite Buchung' }}
          headingLevel={3}
          detailsId="second-details"
        />
      </MemoryRouter>,
    );
    const first = screen.getByRole('region', { name: noticeContent.title });
    const second = screen.getByRole('region', { name: 'Zweite Buchung' });
    expect(within(first).getByRole('link', { name: 'Produkt ansehen' })).not.toBeVisible();
    await user.click(within(first).getByText('Ursache und Quellen'));
    expect(within(first).getByRole('link', { name: 'Produkt ansehen' })).toBeVisible();
    expect(within(second).getByText('Ursache und Quellen').closest('details')).not.toHaveAttribute(
      'open',
    );
  });
});
