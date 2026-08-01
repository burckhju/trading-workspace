import { render, screen } from '@testing-library/react';

import { Application } from './Application';

describe('Application', () => {
  it('renders the technical Sprint 0 landing page', async () => {
    window.history.pushState({}, '', '/');

    render(<Application />);

    expect(
      await screen.findByRole('heading', { name: 'Technisches Frontend-Grundgerüst' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Trading Workspace')).toBeInTheDocument();
  });

  it('renders the not-found page for unknown routes', async () => {
    window.history.pushState({}, '', '/unknown');

    render(<Application />);

    expect(
      await screen.findByRole('heading', { name: 'Seite nicht gefunden' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Zur Startseite' })).toHaveAttribute('href', '/');
  });
});
