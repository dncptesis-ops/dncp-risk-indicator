import { useQuery } from '@tanstack/react-query';
import { fetchBuyers, fetchYears } from '../features/common/services/commonService';

// Entidades y años para los filtros (caché de 30 min).
export default function useCommonData() {
  const buyersQuery = useQuery({
    queryKey: ['common', 'buyers'],
    queryFn: fetchBuyers,
    staleTime: 30 * 60 * 1000,
  });

  const yearsQuery = useQuery({
    queryKey: ['common', 'years'],
    queryFn: fetchYears,
    staleTime: 30 * 60 * 1000,
  });

  return {
    buyers: buyersQuery.data ?? [],
    buyersLoading: buyersQuery.isLoading,
    years: yearsQuery.data ?? [],
    yearsLoading: yearsQuery.isLoading,
  };
}
