import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { NotFoundPage } from './NotFoundPage';

describe('NotFoundPage', () => {
  it('explains the recovery path and keeps the existing start-page navigation', () => {
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: 'Seite nicht gefunden' })).toBeInTheDocument();
    expect(
      screen.getByText(/Die angeforderte Seite ist unter dieser Adresse nicht verfügbar/),
    ).toBeInTheDocument();

    const recoveryLink = screen.getByRole('link', { name: 'Zur Startseite' });
    expect(recoveryLink).toHaveAttribute('href', '/');
    expect(recoveryLink).toHaveClass('focus-visible:ring-2');
  });
});
