import { useCallback, useEffect, useRef, useState } from 'react';
import { Box, Button, Heading, Skeleton, Spinner, Table, Text } from '@chakra-ui/react';
import { ArrowLeft } from 'lucide-react';
import ErrorState from './ErrorState';
import TopEntitiesChart from './TopEntitiesChart';
import Pagination from './Pagination';
import usePaginatedIndicatorData from '../hooks/usePaginatedIndicatorData';
import { useColorModeValue } from '../hooks/use-color-mode';
import { cellStyles, headerStyles } from '../utils/tableColumns';

const DEFAULT_PAGE_SIZE = 10;
// el gráfico muestra la página 1 de la tabla, así usan la misma consulta
const TOP_N = DEFAULT_PAGE_SIZE;

// Ranking de instituciones: muestra el Top 10 y al expandir la tabla completa paginada.
export default function EntityRankingSwitcher({
  fetchFunction,
  columns = [],
  title = '¿Qué instituciones lideran esta alerta?',
  tableTitle = 'Ranking completo',
  nameKey = 'entity',
  countKey = 'r018_count',
  percentageKey = undefined,
  colorHex = '#3182ce',
  onRowClick = undefined,
  filters = {},
  selectedId = null,
  isExpanded = false,
  onExpand,
  onCollapse,
  indicatorKey = 'ranking',
}) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);

  const highlightBg = useColorModeValue(`${colorHex}15`, `${colorHex}25`);
  const hoverBg = useColorModeValue('gray.50', 'whiteAlpha.50');
  const panelBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  // volver a la página 1 si cambian los filtros (se comparan por valor)
  const filtersKey = JSON.stringify(filters);
  const [prevFiltersKey, setPrevFiltersKey] = useState(filtersKey);
  if (prevFiltersKey !== filtersKey) {
    setPrevFiltersKey(filtersKey);
    setPage(1);
  }

  const {
    data: chartResponse,
    isLoading: chartLoading,
    isError: chartError,
    refetch: refetchChart,
  } = usePaginatedIndicatorData(fetchFunction, filters, indicatorKey, 'ranking', {
    page: 1,
    pageSize: TOP_N,
  });
  const chartData = chartResponse?.data ?? [];

  // la tabla solo se pide al expandir
  const {
    data: tableData,
    isLoading: tableLoading,
    isFetching: tableFetching,
    isError: tableError,
    refetch: refetchTable,
    totalPages,
  } = usePaginatedIndicatorData(
    isExpanded ? fetchFunction : null,
    filters,
    indicatorKey,
    'ranking',
    { page, pageSize },
  );

  // al expandir o volver, llevar el bloque a la vista y el foco al título
  const rootRef = useRef(null);
  const headingRef = useRef(null);
  const prevExpanded = useRef(isExpanded);
  useEffect(() => {
    if (prevExpanded.current === isExpanded) return;
    prevExpanded.current = isExpanded;
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    rootRef.current?.scrollIntoView({
      behavior: reduceMotion ? 'auto' : 'smooth',
      block: 'start',
    });
    headingRef.current?.focus({ preventScroll: true });
  }, [isExpanded]);

  const handleExpand = useCallback(() => {
    setPage(1);
    onExpand?.();
  }, [onExpand]);

  const handleCollapse = useCallback(() => {
    setPage(1);
    onCollapse?.();
  }, [onCollapse]);

  const handlePageChange = useCallback(newPage => {
    setPage(newPage);
  }, []);

  const handlePageSizeChange = useCallback(newPageSize => {
    setPageSize(newPageSize);
    setPage(1); // volver a la primera página al cambiar el tamaño
  }, []);

  const handleRowClick = useCallback(
    row => {
      onRowClick?.(row);
    },
    [onRowClick],
  );

  const handleRowKeyDown = useCallback(
    (e, row) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onRowClick?.(row);
      }
    },
    [onRowClick],
  );

  return (
    // deja lugar para la barra fija
    <Box ref={rootRef} scrollMarginTop='80px'>
      {/* Título y botón */}
      <Box display='flex' alignItems='center' justifyContent='space-between' mb={4}>
        <Heading as='h3' size='md' color='fg' ref={headingRef} tabIndex={-1} outline='none'>
          {isExpanded ? tableTitle : title}
        </Heading>
        {isExpanded ? (
          <Button
            size='sm'
            variant='ghost'
            color={colorHex}
            fontWeight='500'
            onClick={handleCollapse}
            aria-label='Volver a la vista resumen con gráfico Top 10'
          >
            <ArrowLeft size={16} />
            <Text ml={1}>Volver al resumen</Text>
          </Button>
        ) : (
          chartData.length > 0 && (
            <Button
              size='sm'
              variant='ghost'
              color={colorHex}
              fontWeight='500'
              onClick={handleExpand}
              aria-label={`Ver tabla completa de ${tableTitle.toLowerCase()}`}
            >
              Ver todas →
            </Button>
          )
        )}
      </Box>

      {/* Gráfico o tabla */}
      {!isExpanded && chartError ? (
        <ErrorState title='No se pudo cargar el ranking' onRetry={refetchChart} />
      ) : !isExpanded ? (
        <TopEntitiesChart
          data={chartData}
          loading={chartLoading}
          title={title}
          nameKey={nameKey}
          countKey={countKey}
          percentageKey={percentageKey}
          colorHex={colorHex}
          onBarClick={onRowClick}
          selectedId={selectedId}
          showTitle={false}
        />
      ) : (
        <Box
          animation='fadeIn 0.2s ease-out'
          css={{
            '@keyframes fadeIn': {
              from: { opacity: 0 },
              to: { opacity: 1 },
            },
          }}
        >
          {tableError ? (
            <ErrorState title='No se pudo cargar el ranking' onRetry={refetchTable} />
          ) : tableLoading && !tableData ? (
            <Box>
              <Skeleton height='24px' width='280px' mb={4} />
              <Skeleton height='400px' borderRadius='xl' />
            </Box>
          ) : !(tableData?.data ?? []).length ? (
            <Box
              textAlign='center'
              py={10}
              color='fg.muted'
              bg={panelBg}
              borderWidth='1px'
              borderColor={borderColor}
              borderRadius='xl'
            >
              <Text>No se encontraron registros para los filtros aplicados.</Text>
            </Box>
          ) : (
            <>
              <Box position='relative'>
                <Box
                  overflowX='auto'
                  bg={panelBg}
                  borderWidth='1px'
                  borderColor={borderColor}
                  borderRadius='xl'
                  shadow='sm'
                  opacity={tableFetching && !tableLoading ? 0.6 : 1}
                  transition='opacity 0.15s ease'
                >
                  <Table.Root
                    size='sm'
                    variant='line'
                    role='grid'
                    aria-label={tableTitle}
                    width='100%'
                  >
                    <Table.Header>
                      <Table.Row role='row'>
                        <Table.ColumnHeader
                          fontSize='xs'
                          fontWeight='semibold'
                          color='fg.muted'
                          textTransform='uppercase'
                          letterSpacing='wide'
                          py={3}
                          pl={4}
                          pr={0}
                          w='50px'
                          role='columnheader'
                        >
                          #
                        </Table.ColumnHeader>
                        {columns.map(col => (
                          <Table.ColumnHeader
                            key={col.key}
                            {...headerStyles(col)}
                            fontSize='xs'
                            fontWeight='semibold'
                            color='fg.muted'
                            textTransform='uppercase'
                            letterSpacing='wide'
                            py={3}
                            px={4}
                            role='columnheader'
                          >
                            {col.header}
                          </Table.ColumnHeader>
                        ))}
                      </Table.Row>
                    </Table.Header>
                    <Table.Body>
                      {(tableData?.data ?? []).map((row, idx) => {
                        const rowId = row.entity_id || row.tenderer_id || row[nameKey] || idx;
                        const isSelected = selectedId && selectedId === rowId;
                        return (
                          <Table.Row
                            key={rowId}
                            role='row'
                            tabIndex={onRowClick ? 0 : -1}
                            cursor={onRowClick ? 'pointer' : 'default'}
                            bg={isSelected ? highlightBg : 'transparent'}
                            _hover={{ bg: onRowClick ? hoverBg : 'transparent' }}
                            onClick={() => handleRowClick(row)}
                            onKeyDown={e => handleRowKeyDown(e, row)}
                            aria-selected={isSelected || undefined}
                            transition='background 0.15s ease'
                          >
                            <Table.Cell
                              py={3}
                              pl={4}
                              pr={0}
                              fontSize='sm'
                              color='fg.muted'
                              role='gridcell'
                            >
                              {(page - 1) * pageSize + idx + 1}
                            </Table.Cell>
                            {columns.map(col => (
                              <Table.Cell
                                key={col.key}
                                py={3}
                                px={4}
                                fontSize='sm'
                                color='fg'
                                {...cellStyles(col)}
                                role='gridcell'
                              >
                                {col.render ? col.render(row) : (row[col.key] ?? '—')}
                              </Table.Cell>
                            ))}
                          </Table.Row>
                        );
                      })}
                    </Table.Body>
                  </Table.Root>
                </Box>

                {tableFetching && !tableLoading && (
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
                    bg={panelBg}
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
                totalRows={tableData?.total_count ?? 0}
                pageSize={pageSize}
                onPageSizeChange={handlePageSizeChange}
              />
            </>
          )}
        </Box>
      )}
    </Box>
  );
}
