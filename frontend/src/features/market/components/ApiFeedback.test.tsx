import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MarketApiError } from '../services/http';
import { ErrorNotice, LoadingNotice } from './ApiFeedback';

describe('ApiFeedback', () => {
  it('renders the API error message for a structured market error', () => {
    const error = new MarketApiError(409, {
      code: 'UNDERLYING_CONCURRENT_MODIFICATION',
      message: 'Der Basiswert wurde zwischenzeitlich geändert.',
      details: [],
      timestamp: '2026-08-05T09:00:00Z',
    });

    render(<ErrorNotice error={error} />);

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Der Basiswert wurde zwischenzeitlich geändert.',
    );
  });

  it('renders the generic fallback for unknown errors', () => {
    render(<ErrorNotice error={new Error('internal detail')} />);

    expect(screen.getByRole('alert')).toHaveTextContent('Die Daten konnten nicht geladen werden.');
  });

  it('renders the default and a custom loading label', () => {
    const { rerender } = render(<LoadingNotice />);
    expect(screen.getByRole('status')).toHaveTextContent('Daten werden geladen …');

    rerender(<LoadingNotice label="Basiswert wird gespeichert …" />);
    expect(screen.getByRole('status')).toHaveTextContent('Basiswert wird gespeichert …');
  });
});
