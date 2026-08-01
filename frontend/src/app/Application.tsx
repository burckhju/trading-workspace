import { useMemo } from 'react';
import { RouterProvider } from 'react-router-dom';

import { createApplicationRouter } from './router';

export function Application() {
  const router = useMemo(() => createApplicationRouter(), []);

  return <RouterProvider router={router} />;
}
