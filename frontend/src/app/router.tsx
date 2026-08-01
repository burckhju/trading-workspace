import { createBrowserRouter } from 'react-router-dom';

import { ApplicationLayout } from '../layouts/ApplicationLayout';
import { FoundationPage } from '../pages/FoundationPage';
import { NotFoundPage } from '../pages/NotFoundPage';

export function createApplicationRouter() {
  return createBrowserRouter([
    {
      path: '/',
      element: <ApplicationLayout />,
      children: [
        {
          index: true,
          element: <FoundationPage />,
        },
        {
          path: '*',
          element: <NotFoundPage />,
        },
      ],
    },
  ]);
}
