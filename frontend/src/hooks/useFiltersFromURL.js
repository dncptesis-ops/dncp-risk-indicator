import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

// fuera del componente: un array nuevo en cada render hacía que las tablas
// volvieran a la página 1
const DEFAULT_FILTER_KEYS = ['year', 'buyer_id', 'proc_method', 'supplier_id'];

// Lee y guarda los filtros en la URL, así una vista filtrada se puede compartir.
// Ej: /r018?year=2024&buyer_id=...
export default function useFiltersFromURL(filterKeys = DEFAULT_FILTER_KEYS) {
  const [searchParams, setSearchParams] = useSearchParams();

  // Construir objeto filters desde la URL, convirtiendo tipos
  const filters = useMemo(() => {
    const result = {};
    for (const key of filterKeys) {
      const raw = searchParams.get(key);
      if (raw == null || raw === '') continue;

      // year siempre es número
      if (key === 'year') {
        const num = Number(raw);
        if (!isNaN(num)) result[key] = num;
      } else {
        result[key] = raw;
      }
    }
    return result;
  }, [searchParams, filterKeys]);

  // Callback compatible con FilterBar.onFiltersChange
  const handleFiltersChange = useCallback(
    newFilters => {
      setSearchParams(
        prev => {
          const next = new URLSearchParams(prev);

          // Limpiar claves de filtro que ya no están
          for (const key of filterKeys) {
            next.delete(key);
          }

          // Setear los nuevos valores (solo si tienen valor)
          for (const [key, value] of Object.entries(newFilters)) {
            if (value != null && value !== '') {
              next.set(key, String(value));
            }
          }

          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams, filterKeys],
  );

  return [filters, handleFiltersChange];
}
