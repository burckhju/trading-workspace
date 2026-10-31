import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { createMemoryRouter, MemoryRouter, RouterProvider, useLocation } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { PendingNavigationGuard } from '../../../components/PendingNavigationGuard';
import { parseClosedContext } from '../../performance/services/closedReportContext';
import type { TradeWorkspaceView } from '../services/workspaceNavigation';
import { TradeWorkspaceNavigation } from './TradeWorkspaceNavigation';

const tradeId = '10000000-0000-4000-8000-000000000001';
const reviewId = '20000000-0000-4000-8000-000000000001';
const journalId = '30000000-0000-4000-8000-000000000001';
// Deliberately noncanonical ordering/encoding: changing the search string on a
// same-owner section switch would trip the existing unsaved-input guard.
const search = `journal_version_id=${journalId}&report_timezone=Europe%2fVienna&trade_id=${tradeId}&review_version_id=${reviewId}&report_context=closed-trades&from_date=2026-10-01&to_date=2026-10-31&report_currency=EUR&report_view=qualified&report_page=3&report_basis=${'a'.repeat(64)}`;
const route = (hash = '') => `/trade-management?${search}${hash}`;

function NavigationFixture({
  view = 'management',
  cancelled = false,
  showBackLinks = true,
}: {
  view?: TradeWorkspaceView;
  cancelled?: boolean;
  showBackLinks?: boolean;
}) {
  const location = useLocation();
  const [note, setNote] = useState('');
  return (
    <>
      <PendingNavigationGuard shouldBlock={() => note.length > 0} />
      <TradeWorkspaceNavigation
        tradeId={tradeId}
        view={view}
        cancelled={cancelled}
        showBackLinks={showBackLinks}
      />
      <input
        aria-label="Ungespeicherte Notiz"
        value={note}
        onChange={(event) => setNote(event.target.value)}
      />
      <section id="trade-overview" tabIndex={-1}>
        Überblicksziel
      </section>
      <section id="position-price-history" tabIndex={-1}>
        Kursverlaufsziel
      </section>
      <section id="execution-dates" tabIndex={-1}>
        Buchungsziel
      </section>
      <section id="trade-risk" tabIndex={-1}>
        Risikoziel
      </section>
      <section id="trade-plan-sources" tabIndex={-1}>
        Planziel
      </section>
      <section id="trade-journal" tabIndex={-1}>
        Journalziel
      </section>
      <section id="unexpected-target" tabIndex={-1}>
        Fremdes Ziel
      </section>
      <output aria-label="Aktuelle Route">
        {location.pathname}
        {location.search}
        {location.hash}
      </output>
    </>
  );
}

function mount(
  initialEntry = route(),
  options: { view?: TradeWorkspaceView; cancelled?: boolean; showBackLinks?: boolean } = {},
) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <NavigationFixture {...options} />
    </MemoryRouter>,
  );
}

describe('Trade workspace navigation', () => {
  it('identifies the selected trade and exposes ordinary keyboard-accessible section links', () => {
    mount();
    const navigation = screen.getByRole('navigation', { name: 'Trade-Arbeitsbereiche' });
    expect(within(navigation).getByText('TR-10000000')).toBeVisible();
    for (const name of [
      'Überblick',
      'Kursverlauf',
      'Buchungen',
      'Risiko und Management',
      'Plan und Quellen',
      'Journal und Lessons',
    ]) {
      const link = within(navigation).getByRole('link', { name });
      expect(link.tagName).toBe('A');
      expect(link).toHaveAttribute('href');
      expect(link).not.toHaveAttribute('tabindex', '-1');
    }
    expect(within(navigation).getAllByRole('link', { current: 'location' })).toHaveLength(1);
    expect(screen.getByRole('link', { name: 'Überblick' })).toHaveAttribute(
      'aria-current',
      'location',
    );
    expect(screen.queryByRole('tab')).not.toBeInTheDocument();
  });

  it('changes same-owner sections by keyboard without changing the query or losing an input', async () => {
    const user = userEvent.setup();
    const router = createMemoryRouter([{ path: '*', element: <NavigationFixture /> }], {
      initialEntries: [route()],
    });
    render(<RouterProvider router={router} />);
    fireEvent.change(screen.getByRole('textbox', { name: 'Ungespeicherte Notiz' }), {
      target: { value: 'Noch nicht gespeicherte Reflexion' },
    });
    const history = screen.getByRole('link', { name: 'Kursverlauf' });
    expect(history).toHaveAttribute('href', route('#position-price-history'));
    await user.tab();
    expect(screen.getByRole('link', { name: 'Überblick' })).toHaveFocus();
    await user.tab();
    expect(history).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(screen.getByLabelText('Aktuelle Route')).toHaveTextContent(
      route('#position-price-history'),
    );
    expect(history).toHaveAttribute('aria-current', 'location');
    expect(screen.getByText('Kursverlaufsziel')).toHaveFocus();
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Ungespeicherte Notiz' })).toHaveValue(
      'Noch nicht gespeicherte Reflexion',
    );
  });

  it('uses the existing pending-input guard on cross-owner links and permits staying in context', async () => {
    const user = userEvent.setup();
    const router = createMemoryRouter([{ path: '*', element: <NavigationFixture /> }], {
      initialEntries: [route('#execution-dates')],
    });
    render(<RouterProvider router={router} />);
    await user.type(screen.getByRole('textbox', { name: 'Ungespeicherte Notiz' }), 'Offene Notiz');
    await user.click(screen.getByRole('link', { name: 'Journal und Lessons' }));
    expect(screen.getByRole('alertdialog')).toHaveTextContent('Ungespeicherte Änderungen');
    expect(screen.getByRole('button', { name: 'Hier bleiben' })).toHaveFocus();
    expect(screen.getByLabelText('Aktuelle Route')).toHaveTextContent(route('#execution-dates'));
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Ungespeicherte Notiz' })).toHaveValue(
      'Offene Notiz',
    );
    expect(screen.getByLabelText('Aktuelle Route')).toHaveTextContent(route('#execution-dates'));

    const unload = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(unload);
    expect(unload.defaultPrevented).toBe(true);
  });

  it('keeps historical pins and the closed-report selection when moving to another owner', () => {
    mount();
    for (const [name, pathname, hash] of [
      ['Plan und Quellen', '/trade-management', '#trade-plan-sources'],
      ['Journal und Lessons', '/post-trade', '#trade-journal'],
    ]) {
      const href = screen.getByRole('link', { name }).getAttribute('href');
      const target = new URL(href!, 'http://workspace.test');
      expect(target.pathname).toBe(pathname);
      expect(target.hash).toBe(hash);
      expect(target.searchParams.get('trade_id')).toBe(tradeId);
      expect(target.searchParams.get('review_version_id')).toBe(reviewId);
      expect(target.searchParams.get('journal_version_id')).toBe(journalId);
      expect(parseClosedContext(target.searchParams).context).toEqual(
        parseClosedContext(new URLSearchParams(search)).context,
      );
    }
    const back = screen.getByRole('link', { name: 'Zur ursprünglichen Abschlussauswahl' });
    const target = new URL(back.getAttribute('href')!, 'http://workspace.test');
    expect(target.pathname).toBe('/performance/closed-trades');
    expect(target.searchParams.get('report_page')).toBe('3');
    expect(target.searchParams.get('report_view')).toBe('qualified');
    expect(target.searchParams.get('report_basis')).toBe('a'.repeat(64));
    expect(screen.getByRole('link', { name: 'Zur Positionsübersicht' })).toHaveAttribute(
      'href',
      '/workspace',
    );
  });

  it('drops arbitrary destinations and monetary values from same-owner as well as cross-owner links', () => {
    mount(`${route()}&returnTo=https%3A%2F%2Felsewhere.invalid&amount=999999&workspace_id=foreign`);
    for (const link of within(screen.getByRole('navigation')).getAllByRole('link')) {
      const destination = new URL(link.getAttribute('href')!, 'http://workspace.test');
      expect(destination.origin).toBe('http://workspace.test');
      expect(destination.searchParams.has('returnTo')).toBe(false);
      expect(destination.searchParams.has('amount')).toBe(false);
      expect(destination.searchParams.has('workspace_id')).toBe(false);
    }
  });

  it.each([
    ['#execution-dates', 'Buchungen'],
    ['#sale-capture', 'Buchungen'],
    ['#trade-management-state', 'Risiko und Management'],
  ])('recognizes direct and legacy anchor %s as the %s area', (hash, name) => {
    mount(route(hash));
    expect(screen.getByRole('link', { name })).toHaveAttribute('aria-current', 'location');
    expect(
      within(screen.getByRole('navigation')).getAllByRole('link', { current: 'location' }),
    ).toHaveLength(1);
  });

  it.each([
    [
      'sources',
      '/trade-management',
      'view=sources&',
      '#trade-plan-sources',
      'Plan und Quellen',
      'Planziel',
    ],
    ['journal', '/post-trade', '', '#trade-journal', 'Journal und Lessons', 'Journalziel'],
  ] as const)(
    'restores the %s owner and focuses its section on a direct URL or reload',
    (view, pathname, extraQuery, hash, label, target) => {
      const url = `${pathname}?${extraQuery}${search}${hash}`;
      const first = mount(url, { view });
      expect(screen.getByRole('link', { name: label })).toHaveAttribute('href', url);
      expect(screen.getByRole('link', { name: label })).toHaveAttribute('aria-current', 'location');
      expect(screen.getByText(target)).toHaveFocus();
      first.unmount();
      mount(url, { view });
      expect(screen.getByRole('link', { name: label })).toHaveAttribute('href', url);
      expect(screen.getByText(target)).toHaveFocus();
    },
  );

  it('does not manufacture a report return link for incomplete or ambiguous report context', () => {
    mount(`${route()}&report_page=5`);
    expect(screen.queryByRole('link', { name: 'Zur ursprünglichen Abschlussauswahl' })).toBeNull();
    const target = new URL(
      screen.getByRole('link', { name: 'Journal und Lessons' }).getAttribute('href')!,
      'http://workspace.test',
    );
    expect(target.searchParams.getAll('report_page')).toEqual(['3', '5']);
    expect(parseClosedContext(target.searchParams).error).not.toBeNull();
  });

  it('retains historical areas for a cancelled trade without offering active-position areas', () => {
    mount(route(), { cancelled: true });
    expect(screen.queryByRole('link', { name: 'Kursverlauf' })).toBeNull();
    expect(screen.queryByRole('link', { name: 'Risiko und Management' })).toBeNull();
    for (const name of ['Überblick', 'Buchungen', 'Plan und Quellen', 'Journal und Lessons']) {
      expect(screen.getByRole('link', { name })).toBeVisible();
    }
  });

  it('can omit duplicate list-return links while retaining all section navigation', () => {
    mount(route(), { showBackLinks: false });
    expect(within(screen.getByRole('navigation')).getAllByRole('link')).toHaveLength(6);
    expect(screen.queryByRole('link', { name: 'Zur Positionsübersicht' })).toBeNull();
    expect(screen.queryByRole('link', { name: 'Zur ursprünglichen Abschlussauswahl' })).toBeNull();
  });

  it('does not focus an arbitrary hash target or fetch data when rendering navigation', () => {
    const fetch = vi.fn();
    vi.stubGlobal('fetch', fetch);
    mount(route('#unexpected-target'));
    expect(screen.getByText('Fremdes Ziel')).not.toHaveFocus();
    expect(fetch).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
