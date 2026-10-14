import { useCallback, useMemo, useState } from 'react';
import { Box, Container, Flex, Heading, Text, VStack } from '@chakra-ui/react';
import { FileText, Edit3 } from 'lucide-react';
import ContextBox from '../components/ContextBox';
import FilterBar from '../components/FilterBar';
import KpiSummary from '../components/KpiSummary';
import TimeSeriesChart from '../components/TimeSeriesChart';
import NotaDatos from '../components/NotaDatos';
import EntityRankingSwitcher from '../components/EntityRankingSwitcher';
import DataTable from '../components/DataTable';
import ContratosMarcados from '../components/ContratosMarcados';
import useCachedIndicatorData from '../hooks/useCachedIndicatorData';
import useCommonData from '../hooks/useCommonData';
import useFiltersFromURL from '../hooks/useFiltersFromURL';
import {
  fetchR064Kpi,
  fetchR064Monthly,
  fetchR064TopEntities,
  fetchR064Processes,
} from '../features/r064/services/r064Service';
import { formatDate, formatNumber, formatPercentage } from '../utils/format';
import { useColorModeValue } from '@/hooks/use-color-mode';

const CONTEXT_DESCRIPTION =
  'Una modificación es un cambio al contrato después de firmado, por ejemplo una ampliación de monto o de plazo. Si bien algunas modificaciones son normales, una cantidad alta puede indicar que el contrato original no se planificó bien, o que se está modificando para favorecer al proveedor después de la adjudicación. Esto puede aumentar el costo final para el estado.';

const KPI_LABELS = {
  total: 'Procesos con contratos firmados',
  alert: 'Procesos con algún contrato modificado',
  percentage: 'Porcentaje',
  formula:
    'Fórmula OCP: (Procesos con algún contrato modificado / Procesos con contratos activos o terminados) × 100',
};

const KPI_ICONS = {
  total: FileText,
  alert: Edit3,
};

const TABLE_COLUMNS = [
  {
    key: 'title',
    header: 'Proceso',
    minW: '260px',
    render: row => row.title || '—',
  },
  {
    key: 'first_amendment_date',
    header: 'Primera modificación',
    type: 'short',
    render: row => formatDate(row.first_amendment_date),
  },
  {
    key: 'amendment_count',
    header: 'Modificaciones',
    type: 'number',
    render: row => row.amendment_count ?? '—',
  },
  {
    key: 'amended_contracts',
    header: 'Contratos modificados',
    type: 'number',
    render: row => (
      <Flex direction='column' align='flex-end' gap={0.5}>
        <Text>
          {row.amended_contracts} de {row.contracts}
        </Text>
        <ContratosMarcados contratos={row.flagged_contracts} />
      </Flex>
    ),
  },
  {
    key: 'entity',
    header: 'Entidad',
    minW: '180px',
    render: row => row.entity || '—',
  },
];

const RANKING_COLUMNS = [
  { key: 'entity', header: 'Institución', minW: '220px' },
  {
    key: 'total_processes',
    header: 'Procesos evaluados',
    type: 'number',
    render: row => formatNumber(row.total_processes),
  },
  {
    key: 'r064_count',
    header: 'Con modificaciones',
    type: 'number',
    render: row => formatNumber(row.r064_count),
  },
  {
    key: 'r064_percentage',
    header: '%',
    type: 'number',
    render: row => formatPercentage(row.r064_percentage),
  },
];

export default function IndicatorR064() {
  const [filters, handleFiltersChange] = useFiltersFromURL();
  const [entitiesExpanded, setEntitiesExpanded] = useState(false);
  const { buyers, years } = useCommonData();

  const chartLineColor = useColorModeValue('#319795', '#4FD1C5');

  const handleEntityClick = useCallback(
    entry => {
      if (entry?.entity_id) {
        handleFiltersChange({ ...filters, buyer_id: entry.entity_id });
      }
    },
    [filters, handleFiltersChange],
  );

  // con una entidad elegida el ranking muestra sus unidades de contratación
  const entidadElegida = filters.buyer_id
    ? (buyers.find(b => b.value === filters.buyer_id)?.label ?? 'la entidad elegida')
    : null;
  const rankingColumns = useMemo(
    () => [
      { ...RANKING_COLUMNS[0], header: entidadElegida ? 'Unidad de contratación' : 'Institución' },
      ...RANKING_COLUMNS.slice(1),
    ],
    [entidadElegida],
  );

  const {
    data: kpiData,
    isLoading: kpiLoading,
    isError: kpiError,
    refetch: refetchKpi,
  } = useCachedIndicatorData(fetchR064Kpi, filters, 'r064', 'kpi');
  const {
    data: monthlyData,
    isLoading: monthlyLoading,
    isError: monthlyError,
    refetch: refetchMonthly,
  } = useCachedIndicatorData(fetchR064Monthly, filters, 'r064', 'monthly');

  return (
    <Container maxW='6xl' py={{ base: 6, md: 10 }}>
      <VStack gap={6} align='stretch'>
        {/* Cabecera */}
        <Box>
          <Text
            fontSize='sm'
            fontWeight='semibold'
            color='teal.fg'
            mb={1}
            textTransform='uppercase'
            letterSpacing='wide'
          >
            Indicador R064 · Contrato Modificado
          </Text>
          <Heading as='h1' size={{ base: 'xl', md: '2xl' }} color='fg'>
            Procesos con Contratos Modificados
          </Heading>
        </Box>

        <ContextBox description={CONTEXT_DESCRIPTION} />

        <FilterBar
          filters={filters}
          onFiltersChange={handleFiltersChange}
          buyers={buyers}
          years={years}
        />

        <KpiSummary
          data={kpiData}
          loading={kpiLoading}
          error={kpiError}
          onRetry={refetchKpi}
          labels={KPI_LABELS}
          icons={KPI_ICONS}
          colorPalette='teal'
          totalKey='total_processes'
          countKey='r064_count'
          percentageKey='r064_percentage'
        />

        <TimeSeriesChart
          data={monthlyData?.data ?? []}
          loading={monthlyLoading}
          error={monthlyError}
          onRetry={refetchMonthly}
          title='¿Está empeorando o mejorando?'
          percentageKey='r064_percentage'
          colorHex={chartLineColor}
          nota={
            // solo aplica sin filtro de año o desde 2024
            (filters.year == null || filters.year >= 2024) && (
              <NotaDatos label='Nota sobre los datos desde mediados de 2024'>
                Desde mediados de 2024 el porcentaje sale más bajo de lo real: los contratos
                recientes todavía no tuvieron tiempo de recibir modificaciones, y los datos abiertos
                de la DNCP no incluyen parte de las modificaciones que sí figuran en su portal.
              </NotaDatos>
            )
          }
        />

        <EntityRankingSwitcher
          fetchFunction={fetchR064TopEntities}
          columns={rankingColumns}
          title={
            entidadElegida
              ? `¿Qué unidades de ${entidadElegida} lideran esta alerta?`
              : '¿Qué instituciones lideran esta alerta?'
          }
          tableTitle={
            entidadElegida
              ? `Unidades de contratación de ${entidadElegida}`
              : 'Ranking de Instituciones — Contrato Modificado'
          }
          nameKey='entity'
          countKey='r064_count'
          percentageKey='r064_percentage'
          colorHex={chartLineColor}
          onRowClick={entidadElegida ? undefined : handleEntityClick}
          filters={filters}
          isExpanded={entitiesExpanded}
          onExpand={() => setEntitiesExpanded(true)}
          onCollapse={() => setEntitiesExpanded(false)}
          indicatorKey='r064'
        />

        <DataTable
          columns={TABLE_COLUMNS}
          fetchFunction={fetchR064Processes}
          filters={filters}
          indicatorKey='r064'
          title='Procesos con contratos modificados'
        />
      </VStack>
    </Container>
  );
}
