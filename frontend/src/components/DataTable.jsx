import { useCallback, useState } from 'react';
import { Box, Flex, Heading, Skeleton, Spinner, Table, Text } from '@chakra-ui/react';
import Pagination from './Pagination';
import usePaginatedIndicatorData from '../hooks/usePaginatedIndicatorData';
import ErrorState from './ErrorState';
import EnlaceExterno from './EnlaceExterno';
import { cellStyles, headerStyles } from '../utils/tableColumns';
import { urlPortalDNCP } from '../utils/dncp';

const DEFAULT_PAGE_SIZE = 10;

// Tabla de casos con paginación en el backend.
// columns: [{ key, header, type?, minW?, render? }], ver utils/tableColumns.js
export default function DataTable({
  columns = [],
  title = 'Detalle de procedimientos',
  urlKey = 'api_url',
  fetchFunction,
  filters,
  indicatorKey,
  pageSize: initialPageSize = DEFAULT_PAGE_SIZE,
}) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);

  // volver a la página 1 si cambian los filtros
  const filtersKey = JSON.stringify(filters);
  const [prevFiltersKey, setPrevFiltersKey] = useState(filtersKey);
  if (prevFiltersKey !== filtersKey) {
    setPrevFiltersKey(filtersKey);
    setPage(1);
  }

  const {
    data: paginatedData,
    isLoading: loading,
    isFetching,
    isError,
    refetch,
    totalPages,
  } = usePaginatedIndicatorData(fetchFunction, filters, indicatorKey, 'list', {
    page,
    pageSize,
  });

  const rows = paginatedData?.data ?? [];
  const totalCount = paginatedData?.total_count ?? 0;

  const handlePageChange = useCallback(newPage => {
    setPage(newPage);
  }, []);

  const handlePageSizeChange = useCallback(newPageSize => {
    setPageSize(newPageSize);
    setPage(1); // volver a la primera página al cambiar el tamaño
  }, []);

  if (isError) {
    return (
      <Box>
        <Heading as='h3' size='md' mb={4} color='fg'>
          {title}
        </Heading>
        <ErrorState title='No se pudo cargar el listado' onRetry={refetch} />
      </Box>
    );
  }

  if (loading && !paginatedData) {
    return (
      <Box>
        <Skeleton height='24px' width='220px' mb={4} />
        <Skeleton height='320px' borderRadius='xl' />
      </Box>
    );
  }

  return (
    <Box>
      <Heading as='h3' size='md' mb={4} color='fg'>
        {title}
      </Heading>

      {!rows.length ? (
        <Box
          textAlign='center'
          py={10}
          color='fg.muted'
          borderWidth='1px'
          borderColor='border'
          borderRadius='xl'
          bg='bg'
          role='status'
          aria-live='polite'
          aria-label='No se encontraron registros'
        >
          <Text>No se encontraron registros para los filtros aplicados.</Text>
        </Box>
      ) : (
        <>
          <Box position='relative'>
            <Box
              overflowX='auto'
              borderWidth='1px'
              borderColor='border'
              borderRadius='xl'
              shadow='sm'
              bg='bg'
              aria-label='Tabla de datos detallados'
              opacity={isFetching && !loading ? 0.6 : 1}
              transition='opacity 0.15s ease'
            >
              <Table.Root size='sm' variant='outline' striped width='100%'>
                <Table.Header>
                  <Table.Row bg='bg.subtle'>
                    <Table.ColumnHeader
                      whiteSpace='nowrap'
                      fontWeight='semibold'
                      pl={3}
                      pr={1}
                      py={3}
                      w='52px'
                    >
                      #
                    </Table.ColumnHeader>
                    {columns.map(col => (
                      <Table.ColumnHeader
                        key={col.key}
                        {...headerStyles(col)}
                        fontWeight='semibold'
                        px={4}
                        py={3}
                      >
                        {col.header}
                      </Table.ColumnHeader>
                    ))}
                    <Table.ColumnHeader whiteSpace='nowrap' fontWeight='semibold' px={4} py={3}>
                      Fuente
                    </Table.ColumnHeader>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {rows.map((row, idx) => {
                    const portal = urlPortalDNCP(row.ocid);
                    return (
                      <Table.Row key={row.release_id || idx}>
                        <Table.Cell pl={3} pr={1} py={2.5} fontSize='sm' color='fg.muted'>
                          {(page - 1) * pageSize + idx + 1}
                        </Table.Cell>
                        {columns.map(col => (
                          <Table.Cell key={col.key} px={4} py={2.5} {...cellStyles(col)}>
                            {col.render ? col.render(row) : (row[col.key] ?? '—')}
                          </Table.Cell>
                        ))}
                        <Table.Cell px={4} py={2.5} whiteSpace='nowrap'>
                          {portal || row[urlKey] ? (
                            <Flex direction='column' gap={1}>
                              {portal && (
                                <EnlaceExterno
                                  href={portal}
                                  label={`Ver ${row.title || 'la licitación'} en el portal de la DNCP`}
                                >
                                  Ver licitación
                                </EnlaceExterno>
                              )}
                              {row[urlKey] && (
                                <EnlaceExterno
                                  href={row[urlKey]}
                                  label={`Ver los datos OCDS de ${row.title || 'este proceso'}`}
                                >
                                  Datos (JSON)
                                </EnlaceExterno>
                              )}
                            </Flex>
                          ) : (
                            <Text color='fg.muted' fontSize='xs'>
                              —
                            </Text>
                          )}
                        </Table.Cell>
                      </Table.Row>
                    );
                  })}
                </Table.Body>
              </Table.Root>
            </Box>

            {isFetching && !loading && (
              <Box
                position='absolute'
                top='50%'
                left='50%'
                transform='translate(-50%, -50%)'
                zIndex={10}
                display='flex'
                flexDirection='column'
                alignItems='center'
                gap={2}
                bg='bg'
                p={4}
                borderRadius='md'
                shadow='md'
                role='status'
                aria-live='polite'
              >
                <Spinner size='lg' color='blue.500' />
                <Text fontSize='sm' color='fg.muted'>
                  Cargando página...
                </Text>
              </Box>
            )}
          </Box>

          <Pagination
            page={page}
            totalPages={totalPages}
            onPageChange={handlePageChange}
            totalRows={totalCount}
            pageSize={pageSize}
            onPageSizeChange={handlePageSizeChange}
          />
        </>
      )}
    </Box>
  );
}
