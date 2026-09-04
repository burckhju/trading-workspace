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
});
