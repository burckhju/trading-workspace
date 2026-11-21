import { Navigate, useLocation } from 'react-router-dom';

/** Preserve old direct links, including exact report parameters and fragment. */
export function PerformanceRedirect() {
  const { search, hash } = useLocation();
  return <Navigate to={`/performance/realized-gross${search}${hash}`} replace />;
}
