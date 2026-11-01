import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, MemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { NoticeCard } from './NoticeCard';
import type { NoticeView } from './types';

const notice: NoticeView = {
  id: 'currency:execution-1',
  title: 'Währungsherkunft dieses Verkaufs',
  presentation: 'warning',
  cause: 'Eine Kaufquelle enthält widersprüchliche Währungsangaben.',
  impact: 'Dieser Verkaufsbeitrag ist nicht berechenbar.',
  automatic: 'Die gelesene Antwort enthält keine automatische Klärung.',
  userNeed: 'Die betroffenen Buchungen können bei Bedarf geprüft werden.',
  details: [{ label: 'Kaufquelle', value: 'Brokerabrechnung vom 30.10.2026' }],
  action: {
    label: 'Buchungen ansehen',
    href: '/trade-management?trade_id=trade-1&report_context=realized-gross&report_basis=basis-1#execution-dates',
  },
};

function renderCard(value = notice, headingLevel: 2 | 3 | 4 = 3) {
  return render(
    <MemoryRouter>
      <NoticeCard notice={value} headingLevel={headingLevel} detailsId="notice-details" />
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
  it.each([
    { label: 'Hinweis', presentation: 'information' as const },
    { label: 'Warnung', presentation: 'warning' as const },
  ])('labels $label visibly without a live announcement', ({ label, presentation }) => {
    const { container } = renderCard({ ...notice, presentation });
    const region = screen.getByRole('region', { name: notice.title });
    expect(within(region).getByText(label)).toBeVisible();
    expect(within(region).getByText(notice.cause)).toBeVisible();
    expect(within(region).getByText(notice.impact)).toBeVisible();
    expect(within(region).getByText(notice.automatic)).toBeVisible();
    expect(within(region).getByText(notice.userNeed)).toBeVisible();
    expect(within(region).getByRole('link', { name: notice.action.label })).toBeVisible();
    expectNoLiveAnnouncement(container);
  });

  it.each([2, 3, 4] as const)('uses the requested native heading level %s', (headingLevel) => {
    renderCard(notice, headingLevel);
    expect(screen.getByRole('heading', { name: notice.title, level: headingLevel })).toBeVisible();
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
    expect(screen.getByText(notice.details[0].value)).not.toBeVisible();

    // Native summary keyboard/focus behavior is checked in the browser pilot;
    // jsdom/user-event does not model its tab stop.
    await user.click(summary);

    expect(details).toHaveAttribute('open');
    expect(screen.getByText(notice.details[0].value)).toBeVisible();
    expect(fetchSpy).not.toHaveBeenCalled();
    expectNoLiveAnnouncement(container);
  });

  it('does not invent detail content or an empty details control', () => {
    const { container } = renderCard({ ...notice, details: [] });
    expect(container.querySelector('details')).toBeNull();
    expect(screen.getByText(notice.impact)).toBeVisible();
    expect(screen.getByRole('link', { name: notice.action.label })).toBeVisible();
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
    renderCard({ ...notice, action: { ...notice.action, href } });
    expect(screen.getByText(notice.action.label)).toBeVisible();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('keeps the supplied action a navigation link without a read or write callback', async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    const router = createMemoryRouter([
      {
        path: '/',
        element: <NoticeCard notice={notice} headingLevel={3} detailsId="navigation-details" />,
      },
      { path: '/trade-management', element: <h1>Buchungen</h1> },
    ]);
    render(<RouterProvider router={router} />);
    const link = screen.getByRole('link', { name: notice.action.label });
    expect(link).toHaveAttribute('href', notice.action.href);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();

    await user.click(link);

    expect(screen.getByRole('heading', { name: 'Buchungen' })).toBeVisible();
    expect(router.state.location.pathname).toBe('/trade-management');
    expect(router.state.location.search).toBe(
      '?trade_id=trade-1&report_context=realized-gross&report_basis=basis-1',
    );
    expect(router.state.location.hash).toBe('#execution-dates');
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('replaces text and destination together while retaining focus and quiet rereads', async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    const { container, rerender } = renderCard();
    await user.click(screen.getByText('Ursache und Quellen'));
    const primaryLink = screen.getByRole('link', { name: notice.action.label });
    primaryLink.focus();
    expect(primaryLink).toHaveFocus();
    const next: NoticeView = {
      ...notice,
      presentation: 'information',
      title: 'Währungsherkunft eines anderen Verkaufs',
      cause: 'Die gelieferte Kaufquelle weist EUR aus.',
      impact: 'Der Bericht weist diesen Beitrag als verwendbar aus.',
      automatic: 'Die gespeicherte historische Quelle wird bereits verwendet.',
      userNeed: 'Eine erneute Bestätigung ist für diese Zuordnung nicht erforderlich.',
      details: [{ label: 'Aktuelle Kaufquelle', value: 'Korrigierte Brokerabrechnung' }],
      action: {
        label: 'Aktuelle Buchungen ansehen',
        href: '/trade-management?trade_id=trade-2&report_context=realized-gross&report_basis=basis-2#execution-dates',
      },
    };
    const content = (
      <MemoryRouter>
        <NoticeCard notice={next} headingLevel={3} detailsId="notice-details" />
      </MemoryRouter>
    );
    rerender(content);

    for (const oldText of [
      notice.title,
      notice.cause,
      notice.impact,
      notice.automatic,
      notice.userNeed,
      notice.details[0].value,
    ]) {
      expect(screen.queryByText(oldText)).not.toBeInTheDocument();
    }
    expect(screen.getByText('Korrigierte Brokerabrechnung')).toBeVisible();
    expect(screen.getByRole('region', { name: next.title })).toHaveAttribute(
      'data-notice-id',
      notice.id,
    );
    expect(screen.getByRole('link', { name: next.action.label })).toHaveAttribute(
      'href',
      next.action.href,
    );
    expect(screen.getByRole('link', { name: next.action.label })).toHaveFocus();
    expectNoLiveAnnouncement(container);

    rerender(content);
    expect(screen.getByRole('link', { name: next.action.label })).toHaveFocus();
    expectNoLiveAnnouncement(container);
    rerender(
      <MemoryRouter>
        <NoticeCard key="remount" notice={next} headingLevel={3} detailsId="notice-details" />
      </MemoryRouter>,
    );
    expect(screen.getByText('Ursache und Quellen').closest('details')).not.toHaveAttribute('open');
    expect(screen.queryByText('Bestätigt')).not.toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
    expectNoLiveAnnouncement(container);
  });

  it('preserves long source references as text without creating links', async () => {
    const user = userEvent.setup();
    const longTitle = `Währungsherkunft ${'einer ausführlich benannten Buchung '.repeat(10)}`;
    const originalReference = `https://archive.example/${'a'.repeat(500)}<script>untrusted()</script>`;
    const { container } = renderCard({
      ...notice,
      title: longTitle,
      details: [{ label: 'Originalreferenz', value: originalReference }],
    });
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent(longTitle.trim());
    expect(screen.getByText(originalReference)).not.toBeVisible();
    await user.click(screen.getByText('Ursache und Quellen'));
    expect(screen.getByText(originalReference)).toBeVisible();
    expect(screen.getAllByRole('link')).toHaveLength(1);
    expect(screen.getByRole('link')).toHaveAttribute('href', notice.action.href);
    expect(container.querySelector('script')).toBeNull();
    expect(container.querySelector('[title]')).toBeNull();
  });

  it('keeps distinct cards independently labelled and expandable', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <NoticeCard notice={notice} headingLevel={3} detailsId="first-details" />
        <NoticeCard
          notice={{ ...notice, id: 'currency:execution-2', title: 'Zweite Buchung' }}
          headingLevel={3}
          detailsId="second-details"
        />
      </MemoryRouter>,
    );
    const first = screen.getByRole('region', { name: notice.title });
    const second = screen.getByRole('region', { name: 'Zweite Buchung' });
    await user.click(within(first).getByText('Ursache und Quellen'));
    expect(within(first).getByText(notice.details[0].value)).toBeVisible();
    expect(within(second).getByText('Ursache und Quellen').closest('details')).not.toHaveAttribute(
      'open',
    );
    expect(within(second).getByText(notice.details[0].value)).not.toBeVisible();
  });
});
