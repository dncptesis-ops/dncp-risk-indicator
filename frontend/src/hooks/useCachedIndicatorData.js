import { useQuery } from '@tanstack/react-query';
import { indicatorKeys } from '../lib/queryKeys';

// Datos no paginados (KPI, serie mensual) con caché de TanStack Query.
export default function useCachedIndicatorData(fetchFn, filters, indicator, type) {
  return useQuery({
    queryKey: indicatorKeys.summary(indicator, type, filters),
    queryFn: () => fetchFn(filters),
    enabled: !!fetchFn,
  });
}
