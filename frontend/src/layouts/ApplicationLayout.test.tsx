import { render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { ApplicationLayout } from './ApplicationLayout';

function renderLayout() {
  return render(
    <MemoryRouter initialEntries={['/underlyings']}>
      <Routes>
        <Route path="/" element={<ApplicationLayout />}>
          <Route path="underlyings" element={<div>Basiswerte</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('ApplicationLayout', () => {
  it('exposes issuer administration in the main navigation', () => {
    renderLayout();

    expect(screen.getByRole('link', { name: 'Stammdaten · Emittenten' })).toHaveAttribute(
      'href',
      '/issuers-admin',
    );
  });

  it('provides explicit keyboard focus treatment for branding and every main navigation link', () => {
    renderLayout();

    expect(screen.getByRole('link', { name: 'Trading Workspace' })).toHaveClass(
      'focus-visible:ring-2',
    );

    const navigation = screen.getByRole('navigation', { name: 'Hauptnavigation' });
    const links = within(navigation).getAllByRole('link');
    expect(links).toHaveLength(10);
    links.forEach((link) => expect(link).toHaveClass('focus-visible:ring-2'));
  });
});
