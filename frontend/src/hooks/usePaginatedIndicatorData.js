import { useQuery } from '@tanstack/react-query';
import { indicatorKeys } from '../lib/queryKeys';

// Datos paginados con caché. Al cambiar de página se deja la anterior visible
// mientras carga; al cambiar los filtros no.
export default function usePaginatedIndicatorData(
  fetchFn,
  filters,
  indicator,
  type,
  { page, pageSize },
) {
  const queryKey = indicatorKeys.paginated(indicator, type, filters, page, pageSize);

  const query = useQuery({
    queryKey,
    queryFn: () =>
      fetchFn({
        ...filters,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      }),
    placeholderData: (previousData, previousQuery) => {
      if (!previousQuery) return undefined;
      const [, , prevFilters] = previousQuery.queryKey;
      const [, , currentFilters] = queryKey;
      return JSON.stringify(prevFilters) === JSON.stringify(currentFilters)
        ? previousData
        : undefined;
    },
    enabled: !!fetchFn,
  });

  const totalPages = Math.max(1, Math.ceil((query.data?.total_count ?? 0) / pageSize));

  return { ...query, totalPages };
}
