import { Navigate, useLocation } from 'react-router-dom';
import { TodayPage } from '../features/operational_workspace/pages/TodayPage';

const legacyUnderlyingFilters = ['query', 'lifecycle', 'venue', 'currency', 'offset'];

export function StartPage() {
  const { search, hash } = useLocation();
  const query = new URLSearchParams(search);
  if (legacyUnderlyingFilters.some((key) => query.has(key)))
    return <Navigate to={`/underlyings${search}${hash}`} replace />;
  return <TodayPage />;
}
