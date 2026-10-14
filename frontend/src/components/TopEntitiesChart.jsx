import { Box, Flex, Heading, Skeleton, Text } from '@chakra-ui/react';
import { formatNumber, formatPercentage } from '../utils/format';

// Top 10 del ranking como lista de barras en HTML (no SVG) para que los
// nombres largos no se corten. Toda la fila es clicable.
export default function TopEntitiesChart({
  data = [],
  loading = false,
  title = '¿Qué instituciones lideran esta alerta?',
  nameKey = 'entity',
  countKey = 'r018_count',
  percentageKey = undefined,
  colorHex = '#3182ce',
  onBarClick = undefined,
  selectedId = null,
  showTitle = true,
}) {
  if (loading) {
    return (
      <Box>
        <Skeleton height='24px' width='280px' mb={4} />
        <Skeleton height='300px' borderRadius='xl' />
      </Box>
    );
  }

  const tituloId = `ranking-title-${nameKey}`;
  const encabezado = showTitle && (
    <Heading as='h3' size='md' mb={4} color='fg' id={tituloId}>
      {title}
    </Heading>
  );

  if (!data.length) {
    return (
      <Box>
        {encabezado}
        <Box
          textAlign='center'
          py={10}
          color='fg.muted'
          bg='bg.panel'
          borderWidth='1px'
          borderColor='border'
          borderRadius='xl'
          role='status'
        >
          <Text>No hay datos de ranking disponibles.</Text>
        </Box>
      </Box>
    );
  }

  const maximo = Math.max(...data.map(item => item[countKey] ?? 0), 1);

  return (
    <Box>
      {encabezado}
      <Box
        as='ol'
        listStyleType='none'
        bg='bg.panel'
        borderWidth='1px'
        borderColor='border'
        borderRadius='xl'
        p={{ base: 2, md: 3 }}
        shadow='sm'
        aria-labelledby={showTitle ? tituloId : undefined}
        aria-label={showTitle ? undefined : title}
      >
        {data.map((item, idx) => {
          const nombre = item[nameKey] || 'Sin nombre';
          const valor = item[countKey] ?? 0;
          const pct = percentageKey ? item[percentageKey] : null;
          const id = item.entity_id || item.tenderer_id || nombre;
          const seleccionada = selectedId != null && selectedId === id;
          const textoValor = `${formatNumber(valor)}${pct != null ? ` · ${formatPercentage(pct)}` : ''}`;
          const clicable = Boolean(onBarClick);

          return (
            <Box as='li' key={id}>
              <Box
                as={clicable ? 'button' : 'div'}
                type={clicable ? 'button' : undefined}
                onClick={clicable ? () => onBarClick(item) : undefined}
                aria-pressed={clicable ? seleccionada : undefined}
                aria-label={
                  clicable
                    ? `${idx + 1}. ${nombre}: ${textoValor} casos. Filtrar por esta institución`
                    : undefined
                }
                display='block'
                w='100%'
                textAlign='start'
                px={3}
                py={2}
                borderRadius='md'
                cursor={clicable ? 'pointer' : 'default'}
                bg={seleccionada ? 'bg.emphasized' : 'transparent'}
                _hover={clicable ? { bg: 'bg.muted' } : undefined}
                _focusVisible={{ outline: '2px solid', outlineColor: 'border.emphasized' }}
                transition='background 0.15s ease'
              >
                <Flex justify='space-between' align='baseline' gap={3} mb={1.5}>
                  <Text fontSize='sm' color='fg' lineHeight='short'>
                    <Text as='span' color='fg.muted' mr={1.5}>
                      {idx + 1}.
                    </Text>
                    {nombre}
                  </Text>
                  <Text
                    fontSize='sm'
                    fontWeight='semibold'
                    color='fg'
                    whiteSpace='nowrap'
                    fontVariantNumeric='tabular-nums'
                  >
                    {textoValor}
                  </Text>
                </Flex>
                <Box
                  h='8px'
                  w={`${Math.max((valor / maximo) * 100, 1)}%`}
                  bg={colorHex}
                  borderEndRadius='4px'
                  aria-hidden='true'
                />
              </Box>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}
