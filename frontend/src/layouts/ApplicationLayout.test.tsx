import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { ApplicationLayout } from './ApplicationLayout';

function CurrentHash() {
  return <output aria-label="Aktueller Bereich">{useLocation().hash}</output>;
}

function renderLayout(path = '/underlyings') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<ApplicationLayout />}>
          <Route
            path="*"
            element={
              <div>
                Seiteninhalt
                <CurrentHash />
              </div>
            }
          />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('ApplicationLayout', () => {
  it('offers five stable groups and only the current group subnavigation', () => {
    renderLayout();
    const navigation = screen.getByRole('navigation', { name: 'Hauptnavigation' });
    for (const name of ['Aktuelles', 'Depot', 'Marktanalyse', 'Lessons Learned', 'Basisdaten'])
      expect(within(navigation).getByRole('link', { name })).toBeInTheDocument();
    expect(within(navigation).getByRole('link', { name: 'Basisdaten' })).toHaveAttribute(
      'aria-current',
      'location',
    );
    const subnavigation = within(navigation).getByRole('navigation', {
      name: 'Basisdaten: Unterbereiche',
    });
    expect(within(subnavigation).getAllByRole('link')).toHaveLength(7);
    expect(within(subnavigation).getByRole('link', { name: 'Emittenten' })).toHaveAttribute(
      'href',
      '/issuers-admin',
    );
    expect(within(subnavigation).getByRole('link', { name: 'Basiswerte' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(
      screen.queryByRole('navigation', { name: 'Depot: Unterbereiche' }),
    ).not.toBeInTheDocument();
  });

  it('uses the current purchase owner for the location and preserves its exact direct link', () => {
    renderLayout('/product-selection?run_id=exact-run#purchase');
    expect(screen.getByRole('navigation', { name: 'Depot: Unterbereiche' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ausführungen' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(screen.getByRole('navigation', { name: 'Aktueller Ort' })).toHaveTextContent(
      'Depot/Ausführungen',
    );
    expect(document.title).toBe('Ausführungen · Trading Workspace');
  });

  it('opens the narrow navigation and closes it after selecting another group', async () => {
    const user = userEvent.setup();
    renderLayout();
    const button = screen.getByRole('button', { name: 'Navigation öffnen' });
    expect(button).toHaveAttribute('aria-expanded', 'false');
    await user.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');
    await user.click(
      within(screen.getByRole('navigation', { name: 'Hauptnavigation' })).getByRole('link', {
        name: 'Depot',
      }),
    );
    expect(button).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByRole('navigation', { name: 'Depot: Unterbereiche' })).toBeInTheDocument();
  });

  it('skips to content without replacing the active purchase hash or location', async () => {
    renderLayout('/product-selection?run_id=exact#purchase');
    await userEvent.click(screen.getByRole('link', { name: 'Zum Inhalt' }));
    expect(screen.getByRole('main')).toHaveFocus();
    expect(screen.getByLabelText('Aktueller Bereich')).toHaveTextContent('#purchase');
    expect(screen.getByRole('link', { name: 'Ausführungen' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });

  it('provides keyboard focus treatment, a skip link and an attention-first home', () => {
    renderLayout();
    expect(screen.getByRole('link', { name: 'Trading Workspace' })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: 'Zum Inhalt' })).toHaveAttribute(
      'href',
      '#page-content',
    );
    const links = within(screen.getByRole('navigation', { name: 'Hauptnavigation' })).getAllByRole(
      'link',
    );
    links.forEach((link) => expect(link).toHaveClass('focus-visible:ring-2'));
    expect(screen.getByRole('main')).toHaveAttribute('tabindex', '-1');
  });
});
