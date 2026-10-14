import { useCallback, useMemo, useState } from 'react';
import { Box, Container, Flex, Heading, Text, VStack } from '@chakra-ui/react';
import { FileText, FileX } from 'lucide-react';
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
  fetchR063Kpi,
  fetchR063Monthly,
  fetchR063TopEntities,
  fetchR063Processes,
} from '../features/r063/services/r063Service';
import { formatDate, formatNumber, formatPercentage } from '../utils/format';
import { useColorModeValue } from '@/hooks/use-color-mode';

// Configuración de R063
const CONTEXT_DESCRIPTION =
  'La ley exige que todos los contratos firmados se publiquen con su documento. Si este número es alto, significa que hay instituciones que están adjudicando dinero público pero no están mostrando el contrato firmado. Esto impide que la ciudadanía pueda verificar qué se acordó exactamente y a qué precio.';

const KPI_LABELS = {
  total: 'Procesos con contratos activos',
  alert: 'Procesos con algún contrato sin documento publicado',
  percentage: 'Porcentaje',
  formula:
    'Fórmula OCP: (Procesos con algún contrato activo sin documento firmado / Procesos con contratos activos) × 100',
};

const KPI_ICONS = {
  total: FileText,
  alert: FileX,
};

const TABLE_COLUMNS = [
  {
    key: 'title',
    header: 'Proceso',
    minW: '260px',
    render: row => row.title || '—',
  },
  {
    key: 'process_date',
    header: 'Primer contrato activo',
    type: 'short',
    render: row => formatDate(row.process_date),
  },
  {
    key: 'unsigned_contracts',
    header: 'Contratos sin documento',
    type: 'number',
    render: row => (
      <Flex direction='column' align='flex-end' gap={0.5}>
        <Text>
          {row.unsigned_contracts} de {row.active_contracts}
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
    header: 'Procesos con contratos activos',
    type: 'number',
    render: row => formatNumber(row.total_processes),
  },
  {
    key: 'r063_count',
    header: 'Sin documento publicado',
    type: 'number',
    render: row => formatNumber(row.r063_count),
  },
  {
    key: 'r063_percentage',
    header: '%',
    type: 'number',
    render: row => formatPercentage(row.r063_percentage),
  },
];

export default function IndicatorR063() {
  const [filters, handleFiltersChange] = useFiltersFromURL();
  const [entitiesExpanded, setEntitiesExpanded] = useState(false);
  const { buyers, years } = useCommonData();
  const chartLineColor = useColorModeValue('#e53e3e', '#fc8181');

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
  } = useCachedIndicatorData(fetchR063Kpi, filters, 'r063', 'kpi');
  const {
    data: monthlyData,
    isLoading: monthlyLoading,
    isError: monthlyError,
    refetch: refetchMonthly,
  } = useCachedIndicatorData(fetchR063Monthly, filters, 'r063', 'monthly');

  return (
    <Container maxW='6xl' py={{ base: 6, md: 10 }}>
      <VStack gap={6} align='stretch'>
        <Box>
          <Text
            fontSize='sm'
            fontWeight='semibold'
            color='red.fg'
            mb={1}
            textTransform='uppercase'
            letterSpacing='wide'
          >
            Indicador R063 · Contrato no Publicado
          </Text>
          <Heading as='h1' size={{ base: 'xl', md: '2xl' }} color='fg'>
            Procesos con Contratos sin Documento Publicado
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
          colorPalette='red'
          totalKey='total_processes'
          countKey='r063_count'
          percentageKey='r063_percentage'
        />

        <TimeSeriesChart
          data={monthlyData?.data ?? []}
          loading={monthlyLoading}
          error={monthlyError}
          onRetry={refetchMonthly}
          title='¿Está empeorando o mejorando?'
          percentageKey='r063_percentage'
          colorHex={chartLineColor}
          nota={
            // solo aplica sin filtro de año o con 2025
            (filters.year == null || filters.year === 2025) && (
              <NotaDatos label='Nota sobre los datos de septiembre y octubre de 2025'>
                En septiembre y octubre de 2025, los datos abiertos de la DNCP no incluyen los
                documentos de muchos contratos que sí figuran en su portal. En esos meses el
                porcentaje sale más alto de lo real.
              </NotaDatos>
            )
          }
        />

        <EntityRankingSwitcher
          fetchFunction={fetchR063TopEntities}
          columns={rankingColumns}
          title={
            entidadElegida
              ? `¿Qué unidades de ${entidadElegida} lideran esta alerta?`
              : '¿Qué instituciones lideran esta alerta?'
          }
          tableTitle={
            entidadElegida
              ? `Unidades de contratación de ${entidadElegida}`
              : 'Ranking de Instituciones — Contrato no Publicado'
          }
          nameKey='entity'
          countKey='r063_count'
          percentageKey='r063_percentage'
          colorHex={chartLineColor}
          onRowClick={entidadElegida ? undefined : handleEntityClick}
          filters={filters}
          isExpanded={entitiesExpanded}
          onExpand={() => setEntitiesExpanded(true)}
          onCollapse={() => setEntitiesExpanded(false)}
          indicatorKey='r063'
        />

        <DataTable
          columns={TABLE_COLUMNS}
          fetchFunction={fetchR063Processes}
          filters={filters}
          indicatorKey='r063'
          title='Procesos con contratos sin documento publicado'
        />
      </VStack>
    </Container>
  );
}
