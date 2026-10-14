import { act, renderHook } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import useFiltersFromURL from './useFiltersFromURL';

function renderConUrl(url) {
  const wrapper = ({ children }) => <MemoryRouter initialEntries={[url]}>{children}</MemoryRouter>;
  return renderHook(
    () => {
      const [filters, setFilters] = useFiltersFromURL();
      return { filters, setFilters, search: useLocation().search };
    },
    { wrapper },
  );
}

describe('useFiltersFromURL', () => {
  it('lee los filtros de la URL y convierte year a número', () => {
    const { result } = renderConUrl('/r018?year=2024&buyer_id=DNCP-SICP-CODE-306&otro=x');
    expect(result.current.filters).toEqual({ year: 2024, buyer_id: 'DNCP-SICP-CODE-306' });
  });

  it('devuelve el mismo objeto en cada render si la URL no cambia', () => {
    // Si fuera un objeto nuevo en cada render, las tablas volverían a la página 1
    // con cualquier re-render de la página (por ejemplo al tocar "Ver todas").
    const { result, rerender } = renderConUrl('/r018?year=2024');
    const primero = result.current.filters;
    rerender();
    expect(result.current.filters).toBe(primero);
  });

  it('escribe los filtros en la URL y omite los vacíos', () => {
    const { result } = renderConUrl('/r018?year=2024');
    act(() => {
      result.current.setFilters({ year: 2025, buyer_id: '', proc_method: 'open' });
    });
    expect(result.current.search).toBe('?year=2025&proc_method=open');
    expect(result.current.filters).toEqual({ year: 2025, proc_method: 'open' });
  });
});
