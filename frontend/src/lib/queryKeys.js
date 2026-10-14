// Query keys de TanStack Query: [indicador, tipo, filtros, (paginación)].
export const indicatorKeys = {
  summary: (indicator, type, filters) => [indicator, type, filters],

  paginated: (indicator, type, filters, page, pageSize) => [
    indicator,
    type,
    filters,
    { page, pageSize },
  ],
};
