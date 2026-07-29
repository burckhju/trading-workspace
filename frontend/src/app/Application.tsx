import { RouterProvider } from 'react-router-dom';

import { applicationRouter } from './router';

export function Application() {
  return <RouterProvider router={applicationRouter} />;
}
