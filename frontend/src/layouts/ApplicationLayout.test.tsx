import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { ApplicationLayout } from './ApplicationLayout';

describe('ApplicationLayout', () => {
  it('exposes issuer administration in the main navigation', () => {
    render(
      <MemoryRouter initialEntries={['/underlyings']}>
        <Routes>
          <Route path="/" element={<ApplicationLayout />}>
            <Route path="underlyings" element={<div>Basiswerte</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: 'Stammdaten · Emittenten' })).toHaveAttribute(
      'href',
      '/issuers-admin',
    );
  });

  it('provides an explicit keyboard focus indicator for main navigation links', () => {
    render(
      <MemoryRouter initialEntries={['/underlyings']}>
        <Routes>
          <Route path="/" element={<ApplicationLayout />}>
            <Route path="underlyings" element={<div>Basiswerte</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    const mainNavigation = screen.getByRole('navigation', { name: 'Hauptnavigation' });
    for (const link of Array.from(mainNavigation.querySelectorAll('a'))) {
      expect(link).toHaveClass('focus-visible:ring-2', 'focus-visible:ring-sky-400');
    }
  });
});
