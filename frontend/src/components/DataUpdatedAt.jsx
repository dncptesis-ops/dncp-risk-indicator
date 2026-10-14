import { Text } from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { fetchUpdatedAt } from '@/features/common/services/commonService';
import { formatDateTime } from '@/utils/format';

// Fecha de la última actualización de los datos. Si la API falla no muestra nada.
export default function DataUpdatedAt(props) {
  const { data, isSuccess } = useQuery({
    queryKey: ['common', 'status'],
    queryFn: fetchUpdatedAt,
    staleTime: 5 * 60 * 1000,
  });

  if (!isSuccess || !data) return null;

  return (
    <Text fontSize='sm' color='fg.muted' {...props}>
      Datos de la DNCP actualizados al{' '}
      <time dateTime={data} style={{ whiteSpace: 'nowrap' }}>
        {formatDateTime(data)}
      </time>{' '}
      (hora de Paraguay)
    </Text>
  );
}
