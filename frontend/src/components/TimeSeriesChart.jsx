import { useMemo } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  Tooltip,
  XAxis,
  YAxis,
  ResponsiveContainer,
} from 'recharts';
import { Box, Flex, Heading, Skeleton, Text } from '@chakra-ui/react';
import { useColorModeValue } from '../hooks/use-color-mode';
import { formatPercentage } from '../utils/format';
import ErrorState from './ErrorState';

// Gráfico de línea con el porcentaje mensual.
export default function TimeSeriesChart({
  data = [],
  loading = false,
  error = false,
  onRetry,
  title = '¿Está empeorando o mejorando?',
  percentageKey = 'r018_percentage',
  colorHex = '#dd6b20',
  nota = null, // aclaracion opcional junto al titulo (NotaDatos)
}) {
  const mutedColor = useColorModeValue('#4a5568', '#a0aec0'); // gray.600 / gray.400
  const gridColor = useColorModeValue('#e2e8f0', '#2d3748'); // border claro / oscuro
  const tooltipBg = useColorModeValue('#ffffff', '#1a202c'); // blanco / gray.900
  const tooltipColor = useColorModeValue('#1a202c', '#f7fafc'); // texto oscuro / texto claro

  const chartData = useMemo(() => {
    return data.map(item => ({
      ...item,
      monthLabel: formatMonthLabel(item.month),
    }));
  }, [data]);

  if (loading) {
    return (
      <Box>
        <Skeleton height='24px' width='280px' mb={4} />
        <Skeleton height='300px' borderRadius='xl' />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Flex align='center' gap={1} mb={4}>
          <Heading as='h3' size='md' color='fg'>
            {title}
          </Heading>
          {nota}
        </Flex>
        <ErrorState title='No se pudo cargar la evolución mensual' onRetry={onRetry} />
      </Box>
    );
  }

  if (!data.length) {
    return (
      <Box>
        <Flex align='center' gap={1} mb={4}>
          <Heading as='h3' size='md' color='fg'>
            {title}
          </Heading>
          {nota}
        </Flex>
        <Box
          textAlign='center'
          py={10}
          color='fg.muted'
          bg='bg.panel'
          borderWidth='1px'
          borderColor='border'
          borderRadius='xl'
          role='status'
          aria-label='No hay datos disponibles'
        >
          <Text>No hay datos disponibles para el período seleccionado.</Text>
        </Box>
      </Box>
    );
  }

  return (
    <Box>
      <Flex align='center' gap={1} mb={4}>
        <Heading as='h3' size='md' color='fg'>
          {title}
        </Heading>
        {nota}
      </Flex>
      <Box
        bg='bg.panel'
        borderWidth='1px'
        borderColor='border'
        borderRadius='xl'
        p={{ base: 2, md: 4 }}
        shadow='sm'
        aria-label='Gráfico de tendencia mensual'
      >
        <ResponsiveContainer width='100%' height={320}>
          <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 10 }}>
            <CartesianGrid strokeDasharray='3 3' stroke={gridColor} />
            <XAxis
              dataKey='monthLabel'
              tick={{ fontSize: 12, fill: mutedColor }}
              tickLine={false}
              axisLine={{ stroke: gridColor }}
            />
            <YAxis
              tick={{ fontSize: 12, fill: mutedColor }}
              tickLine={false}
              axisLine={{ stroke: gridColor }}
              // el eje no baja de 0
              tickFormatter={formatPercentage}
              domain={[min => Math.max(0, min - 0.5), 'dataMax + 0.5']}
            />
            <Tooltip
              contentStyle={{
                borderRadius: '8px',
                backgroundColor: tooltipBg,
                color: tooltipColor,
                border: `1px solid ${gridColor}`,
                fontSize: '13px',
              }}
              formatter={value => [formatPercentage(value), 'Porcentaje']}
              labelFormatter={label => `Mes: ${label}`}
            />
            <Line
              type='monotone'
              dataKey={percentageKey}
              stroke={colorHex}
              strokeWidth={2.5}
              dot={{ r: 4, fill: colorHex, strokeWidth: 0 }}
              activeDot={{ r: 6, fill: colorHex, stroke: tooltipBg, strokeWidth: 2 }}
              animationDuration={800}
            />
          </LineChart>
        </ResponsiveContainer>
      </Box>
    </Box>
  );
}

// "2023-01" -> "Ene 23"
function formatMonthLabel(month) {
  if (!month) return '';
  const [year, m] = month.split('-');
  const months = [
    'Ene',
    'Feb',
    'Mar',
    'Abr',
    'May',
    'Jun',
    'Jul',
    'Ago',
    'Sep',
    'Oct',
    'Nov',
    'Dic',
  ];
  const idx = parseInt(m, 10) - 1;
  if (idx < 0 || idx > 11) return month;
  return `${months[idx]} ${year.slice(2)}`;
}
