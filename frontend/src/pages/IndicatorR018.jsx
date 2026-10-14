import { useCallback, useMemo, useState } from 'react';
import { Box, Container, Heading, Text, VStack } from '@chakra-ui/react';
import { FileText, AlertTriangle } from 'lucide-react';
import ContextBox from '../components/ContextBox';
import FilterBar from '../components/FilterBar';
import KpiSummary from '../components/KpiSummary';
import TimeSeriesChart from '../components/TimeSeriesChart';
import EntityRankingSwitcher from '../components/EntityRankingSwitcher';
import DataTable from '../components/DataTable';
import useCachedIndicatorData from '../hooks/useCachedIndicatorData';
import useCommonData from '../hooks/useCommonData';
import useFiltersFromURL from '../hooks/useFiltersFromURL';
import {
  fetchR018Kpi,
  fetchR018Monthly,
  fetchR018TopEntities,
  fetchR018Suppliers,
  fetchR018Tenders,
} from '../features/r018/services/r018Service';
import { formatDate, METHOD_LABEL, formatNumber, formatPercentage } from '../utils/format';
import { useColorModeValue } from '@/hooks/use-color-mode';

const CONTEXT_DESCRIPTION =
  'La ley exige competencia en las compras públicas. Si una licitación recibe una sola oferta, no hubo competencia real. Un porcentaje alto puede indicar que el estado está comprando a proveedores sin alternativas, lo que puede encarecer las compras y reducir la calidad.';

const KPI_LABELS = {
  total: 'Total de licitaciones competitivas',
  alert: 'Licitaciones con un solo oferente',
  percentage: 'Porcentaje',
  formula:
    'Fórmula OCP: (Licitaciones con único oferente / Total de licitaciones competitivas) × 100',
};

const KPI_ICONS = {
  total: FileText,
  alert: AlertTriangle,
};

const TABLE_COLUMNS = [
  {
    key: 'title',
    header: 'Licitación',
    minW: '260px',
    render: row => row.title || '—',
  },
  {
    key: 'procedure_date',
    header: 'Fecha',
    type: 'short',
    render: row => formatDate(row.procedure_date),
  },
  {
    key: 'procurement_method',
    header: 'Método',
    type: 'short',
    render: row => METHOD_LABEL[row.procurement_method] || row.procurement_method || '—',
  },
  {
    key: 'suppliers',
    header: 'Proveedor único',
    minW: '180px',
    render: row => row.suppliers || '—',
  },
];

const ENTITY_RANKING_COLUMNS = [
  { key: 'entity', header: 'Institución', minW: '220px' },
  {
    key: 'total_competitive',
    header: 'Licitaciones competitivas',
    type: 'number',
    render: row => formatNumber(row.total_competitive),
  },
  {
    key: 'r018_count',
    header: 'Único oferente',
    type: 'number',
    render: row => formatNumber(row.r018_count),
  },
  {
    key: 'r018_percentage',
    header: '%',
    type: 'number',
    render: row => formatPercentage(row.r018_percentage),
  },
];

const SUPPLIER_RANKING_COLUMNS = [
  { key: 'supplier_name', header: 'Proveedor', minW: '220px' },
  { key: 'ruc', header: 'RUC', type: 'short' },
  {
    key: 'sole_bidder_count',
    header: 'Licitaciones ganadas como único oferente',
    type: 'number',
    render: row => formatNumber(row.sole_bidder_count),
  },
];

export default function IndicatorR018() {
  const [filters, handleFiltersChange] = useFiltersFromURL();
  const [entitiesExpanded, setEntitiesExpanded] = useState(false);
  const [suppliersExpanded, setSuppliersExpanded] = useState(false);
  const { buyers, years } = useCommonData();

  const chartLineColor = useColorModeValue('#c05621', '#fbd38d');

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
      {
        ...ENTITY_RANKING_COLUMNS[0],
        header: entidadElegida ? 'Unidad de contratación' : 'Institución',
      },
      ...ENTITY_RANKING_COLUMNS.slice(1),
    ],
    [entidadElegida],
  );

  const {
    data: kpiData,
    isLoading: kpiLoading,
    isError: kpiError,
    refetch: refetchKpi,
  } = useCachedIndicatorData(fetchR018Kpi, filters, 'r018', 'kpi');
  const {
    data: monthlyData,
    isLoading: monthlyLoading,
    isError: monthlyError,
    refetch: refetchMonthly,
  } = useCachedIndicatorData(fetchR018Monthly, filters, 'r018', 'monthly');

  const handleEntitiesExpand = useCallback(() => {
    setEntitiesExpanded(true);
  }, []);

  const handleSuppliersExpand = useCallback(() => {
    setSuppliersExpanded(true);
  }, []);

  const handleEntitiesCollapse = useCallback(() => {
    setEntitiesExpanded(false);
  }, []);

  const handleSuppliersCollapse = useCallback(() => {
    setSuppliersExpanded(false);
  }, []);

  const anyExpanded = entitiesExpanded || suppliersExpanded;

  return (
    <Container maxW='6xl' py={{ base: 6, md: 10 }}>
      <VStack gap={6} align='stretch'>
        <Box>
          <Text
            fontSize='sm'
            fontWeight='semibold'
            color='orange.fg'
            mb={1}
            textTransform='uppercase'
            letterSpacing='wide'
          >
            Indicador R018 · Única Oferta
          </Text>
          <Heading as='h1' size={{ base: 'xl', md: '2xl' }} color='fg'>
            Licitaciones con un Solo Oferente
          </Heading>
        </Box>

        <ContextBox description={CONTEXT_DESCRIPTION} />

        <FilterBar
          filters={filters}
          onFiltersChange={handleFiltersChange}
          showProcMethod
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
          colorPalette='orange'
          totalKey='total_competitive'
          countKey='r018_count'
          percentageKey='r018_percentage'
        />

        <TimeSeriesChart
          data={monthlyData?.data ?? []}
          loading={monthlyLoading}
          error={monthlyError}
          onRetry={refetchMonthly}
          title='¿Está empeorando o mejorando?'
          percentageKey='r018_percentage'
          colorHex={chartLineColor}
        />

        <Box
          display='grid'
          gridTemplateColumns={anyExpanded ? '1fr' : { base: '1fr', lg: '1fr 1fr' }}
          gap={6}
        >
          <Box gridColumn={entitiesExpanded ? '1 / -1' : undefined}>
            <EntityRankingSwitcher
              fetchFunction={fetchR018TopEntities}
              columns={rankingColumns}
              title={
                entidadElegida
                  ? `¿Qué unidades de ${entidadElegida} lideran esta alerta?`
                  : '¿Qué instituciones lideran esta alerta?'
              }
              tableTitle={
                entidadElegida
                  ? `Unidades de contratación de ${entidadElegida}`
                  : 'Ranking de Instituciones — Única Oferta'
              }
              nameKey='entity'
              countKey='r018_count'
              percentageKey='r018_percentage'
              colorHex={chartLineColor}
              onRowClick={entidadElegida ? undefined : handleEntityClick}
              filters={filters}
              isExpanded={entitiesExpanded}
              onExpand={handleEntitiesExpand}
              onCollapse={handleEntitiesCollapse}
              indicatorKey='r018'
            />
          </Box>

          <Box gridColumn={suppliersExpanded ? '1 / -1' : undefined}>
            <EntityRankingSwitcher
              fetchFunction={fetchR018Suppliers}
              columns={SUPPLIER_RANKING_COLUMNS}
              title='¿Qué empresas ganan como oferente único?'
              tableTitle='Ranking de Proveedores — Única Oferta'
              nameKey='supplier_name'
              countKey='sole_bidder_count'
              colorHex={chartLineColor}
              filters={filters}
              isExpanded={suppliersExpanded}
              onExpand={handleSuppliersExpand}
              onCollapse={handleSuppliersCollapse}
              indicatorKey='r018-suppliers'
            />
          </Box>
        </Box>

        <DataTable
          columns={TABLE_COLUMNS}
          fetchFunction={fetchR018Tenders}
          filters={filters}
          indicatorKey='r018'
          title='Licitaciones con único oferente'
        />
      </VStack>
    </Container>
  );
}
