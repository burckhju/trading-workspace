import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { expect, it, vi } from 'vitest';

import { PerformanceWorkspace } from '../features/performance/pages/PerformanceWorkspace';
import { performanceApiClient } from '../features/performance/services/client';
import { closedTradeReport } from '../test/closedTradesFixtures';
import { realizedGrossReport, reportFilters } from '../test/realizedGrossFixtures';
import { ApplicationLayout } from './ApplicationLayout';

vi.mock('../features/performance/services/client', () => ({
  performanceApiClient: { realizedGross: vi.fn(), closedTrades: vi.fn() },
}));

it('preserves keyboard focus inside the continuing report owner but focuses main after global navigation', async () => {
  const user = userEvent.setup();
  const api = vi.mocked(performanceApiClient);
  api.realizedGross.mockImplementation((filters) =>
    Promise.resolve(realizedGrossReport({ filters })),
  );
  api.closedTrades.mockImplementation((filters) => Promise.resolve(closedTradeReport({ filters })));
  const router = createMemoryRouter(
    [
      {
        element: <ApplicationLayout />,
        children: [
          {
            path: '/performance/realized-gross',
            element: <PerformanceWorkspace kind="realized-gross" />,
          },
          {
            path: '/performance/closed-trades',
            element: <PerformanceWorkspace kind="closed-trades" />,
          },
        ],
      },
    ],
    {
      initialEntries: [
        `/performance/realized-gross?${new URLSearchParams({
          report_context: 'realized-gross',
          ...reportFilters,
          report_view: 'candidates',
          report_page: '1',
        })}`,
      ],
    },
  );
  render(<RouterProvider router={router} />);
  expect(await screen.findByTestId('realized-gross-total')).toHaveTextContent('10,00 EUR');
  const form = screen.getByRole('form', { name: 'Performance-Zeitraum auswählen' });
  const closed = screen.getByRole('button', { name: 'Trades mit Vollabschluss im Zeitraum' });
  closed.focus();
  await user.keyboard('{Enter}');
  expect(await screen.findByTestId('closed-trades-total')).toHaveTextContent('50,00 EUR');
  expect(closed).toHaveFocus();
  expect(closed).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByRole('form', { name: 'Performance-Zeitraum auswählen' })).toBe(form);
  expect(api.closedTrades).toHaveBeenCalledExactlyOnceWith(reportFilters, expect.any(AbortSignal));

  // A sidebar switch still starts at the main content, even for the same report owner.
  await user.click(screen.getByRole('button', { name: 'Navigation öffnen' }));
  const globalPerformance = within(
    screen.getByRole('navigation', { name: 'Hauptnavigation' }),
  ).getByRole('link', { name: 'Performance' });
  globalPerformance.focus();
  await user.keyboard('{Enter}');
  expect(router.state.location.pathname).toBe('/performance/realized-gross');
  expect(screen.getByRole('main')).toHaveFocus();
});
