import { Box, Flex, Grid, Skeleton, Text, Tooltip } from '@chakra-ui/react';
import { formatNumber, formatPercentage } from '../utils/format';
import ErrorState from './ErrorState';
import KpiCard from './KpiCard';

// Resumen del KPI: total, casos marcados y porcentaje.
export default function KpiSummary({
  data,
  loading = false,
  error = false,
  onRetry,
  labels = {},
  icons = {},
  colorPalette = 'orange',
  totalKey = 'total',
  countKey = 'count',
  percentageKey = 'percentage',
}) {
  if (error) {
    return <ErrorState title='No se pudo cargar el resumen del indicador' onRetry={onRetry} />;
  }

  // sin ?? 0: si falta el dato se muestra "—", no 0
  const total = data?.[totalKey];
  const count = data?.[countKey];
  const percentage = data?.[percentageKey];

  return (
    <Grid templateColumns={{ base: '1fr', md: 'repeat(3, 1fr)' }} gap={4}>
      <KpiCard
        icon={icons.total}
        label={labels.total ?? 'Total de procedimientos'}
        value={loading ? undefined : formatNumber(total)}
        isLoading={loading}
        accentColor='gray.solid'
        accentBg='gray.subtle'
        iconColor='gray.contrast'
      />

      <KpiCard
        icon={icons.alert}
        label={labels.alert ?? 'Casos detectados'}
        value={loading ? undefined : formatNumber(count)}
        isLoading={loading}
        accentColor={`${colorPalette}.solid`}
        accentBg={`${colorPalette}.subtle`}
        iconColor={`${colorPalette}.contrast`}
      />

      <Box
        bg='bg.panel'
        borderWidth='1px'
        borderColor='border'
        borderRadius='xl'
        p={5}
        shadow='sm'
        position='relative'
      >
        {loading ? (
          <Flex direction='column' gap={2}>
            <Skeleton height='16px' width='80px' />
            <Skeleton height='40px' width='120px' />
            <Skeleton height='14px' width='160px' />
          </Flex>
        ) : (
          <>
            <Text fontSize='sm' color='fg.muted' fontWeight='medium' mb={1}>
              {labels.percentage ?? 'Porcentaje'}
            </Text>
            <Tooltip.Root openDelay={200} closeDelay={100}>
              <Tooltip.Trigger asChild>
                <Text
                  as='span'
                  fontSize='3xl'
                  fontWeight='bold'
                  color={`${colorPalette}.fg`}
                  cursor='help'
                  tabIndex={0}
                  _focusVisible={{ outline: '2px solid', outlineColor: 'border' }}
                >
                  {formatPercentage(percentage)}
                </Text>
              </Tooltip.Trigger>
              <Tooltip.Positioner>
                <Tooltip.Content>
                  <Tooltip.Arrow />
                  <Text fontSize='xs' maxW='260px'>
                    {labels.formula ??
                      'Fórmula OCP: (Casos detectados / Total de procedimientos) × 100'}
                  </Text>
                </Tooltip.Content>
              </Tooltip.Positioner>
            </Tooltip.Root>
            <Text fontSize='xs' color='fg.muted' mt={2}>
              del total evaluado
            </Text>
          </>
        )}
      </Box>
    </Grid>
  );
}
