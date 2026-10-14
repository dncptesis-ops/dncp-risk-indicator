import { useRef } from 'react';
import { Box, Container, Flex, Heading, Icon, List, SimpleGrid, Text } from '@chakra-ui/react';
import { Building2, FileX, Edit3, Database, Eye, MousePointerClick } from 'lucide-react';
import useCachedIndicatorData from '../hooks/useCachedIndicatorData';
import { fetchR018Kpi } from '../features/r018/services/r018Service';
import { fetchR063Kpi } from '../features/r063/services/r063Service';
import { fetchR064Kpi } from '../features/r064/services/r064Service';
import { formatNumber, formatPercentage } from '../utils/format';
import HeroSection from '../components/HeroSection';
import KpiCard from '../components/KpiCard';
import DataUpdatedAt from '../components/DataUpdatedAt';

const SIN_FILTROS = {};
const ERROR_KPI = 'No se pudo cargar este indicador. Intentá de nuevo en unos minutos.';

export default function Home() {
  const dashboardRef = useRef(null);

  // misma query key que cada indicador sin filtros, así queda en caché
  const {
    data: r018,
    isLoading: loading018,
    isError: error018,
  } = useCachedIndicatorData(fetchR018Kpi, SIN_FILTROS, 'r018', 'kpi');
  const {
    data: r063,
    isLoading: loading063,
    isError: error063,
  } = useCachedIndicatorData(fetchR063Kpi, SIN_FILTROS, 'r063', 'kpi');
  const {
    data: r064,
    isLoading: loading064,
    isError: error064,
  } = useCachedIndicatorData(fetchR064Kpi, SIN_FILTROS, 'r064', 'kpi');

  return (
    <Box>
      {/* Portada */}
      <HeroSection scrollTargetRef={dashboardRef} />

      {/* Indicadores */}
      <Box as='section' ref={dashboardRef} py={{ base: 12, md: 20 }}>
        <Container maxW='6xl'>
          <Box textAlign='center' mb={12}>
            <Heading as='h2' size={{ base: '2xl', md: '3xl' }} fontWeight='bold' color='fg' mb={3}>
              Tres indicadores, una mirada clara
            </Heading>
            <Text fontSize='lg' color='fg.muted' maxW='2xl' mx='auto'>
              Seleccioná un indicador para ver su evolución en el tiempo, filtrar por entidad y año,
              y entender dónde están los focos de riesgo en la contratación pública paraguaya.
            </Text>
          </Box>

          <SimpleGrid columns={{ base: 1, md: 3 }} gap={{ base: 6, md: 8 }}>
            <KpiCard
              icon={Building2}
              label='Única Oferta'
              value={loading018 ? null : error018 ? '—' : formatPercentage(r018?.r018_percentage)}
              description={
                loading018
                  ? null
                  : error018
                    ? ERROR_KPI
                    : `De ${formatNumber(r018?.total_competitive)} procesos competitivos históricos, ${formatNumber(r018?.r018_count)} tuvieron un solo oferente.`
              }
              to='/r018'
              accentColor='blue.solid'
              accentBg='blue.subtle'
              iconColor='blue.contrast'
              isLoading={loading018}
            />

            <KpiCard
              icon={FileX}
              label='Contrato no Publicado'
              value={loading063 ? null : error063 ? '—' : formatPercentage(r063?.r063_percentage)}
              description={
                loading063
                  ? null
                  : error063
                    ? ERROR_KPI
                    : `De ${formatNumber(r063?.total_processes)} procesos con contratos activos, ${formatNumber(r063?.r063_count)} tienen al menos un contrato sin su documento firmado publicado para la ciudadanía.`
              }
              to='/r063'
              accentColor='red.solid'
              accentBg='red.subtle'
              iconColor='red.contrast'
              isLoading={loading063}
            />

            <KpiCard
              icon={Edit3}
              label='Contrato Modificado'
              value={loading064 ? null : error064 ? '—' : formatPercentage(r064?.r064_percentage)}
              description={
                loading064
                  ? null
                  : error064
                    ? ERROR_KPI
                    : `De ${formatNumber(r064?.total_processes)} procesos con contratos firmados, ${formatNumber(r064?.r064_count)} tuvieron alguna modificación después de la firma.`
              }
              to='/r064'
              accentColor='teal.solid'
              accentBg='teal.subtle'
              iconColor='teal.contrast'
              isLoading={loading064}
            />
          </SimpleGrid>
        </Container>
      </Box>

      <Box as='section' bg='bg.muted' py={{ base: 12, md: 20 }}>
        <Container maxW='6xl'>
          <SimpleGrid columns={{ base: 1, md: 2 }} gap={{ base: 8, md: 16 }}>
            <Box>
              <Heading as='h2' size={{ base: 'xl', md: '2xl' }} fontWeight='bold' color='fg' mb={6}>
                ¿Por qué importa esto?
              </Heading>
              <Text fontSize='md' color='fg.muted' lineHeight='tall' mb={4}>
                Esta plataforma no inventa indicadores arbitrarios. Se basa en el modelo{' '}
                <Text as='strong' color='fg'>
                  OCDS (Open Contracting Data Standard)
                </Text>
                , un estándar internacional promovido por la{' '}
                <Text as='strong' color='fg'>
                  Open Contracting Partnership (OCP)
                </Text>{' '}
                para estructurar datos de contrataciones públicas de forma abierta y comparable.
              </Text>
              <Text fontSize='md' color='fg.muted' lineHeight='tall' mb={4}>
                Cruzamos los datos públicos de la Dirección Nacional de Contrataciones Públicas
                (DNCP) con las metodologías de detección de patrones de la OCP.{' '}
                <Text as='strong' color='fg'>
                  No acusamos delitos: señalamos dónde hay que mirar más de cerca.
                </Text>
              </Text>
              <Text fontSize='md' color='fg.muted' lineHeight='tall'>
                El objetivo es que cualquier persona —sin formación en leyes, sin ser contadora, sin
                saber de compras públicas— pueda entender de un vistazo si un proceso de
                contratación tuvo señales de alerta.
              </Text>
            </Box>

            <Box
              bg='bg.panel'
              border='1px solid'
              borderColor='border'
              borderRadius='2xl'
              p={{ base: 6, md: 8 }}
              shadow='sm'
            >
              <Text fontWeight='bold' fontSize='lg' color='fg' mb={6}>
                ¿Cómo funciona?
              </Text>
              <List.Root gap={5} listStyle='none'>
                <List.Item>
                  <Flex align='flex-start' gap={4}>
                    <Flex
                      align='center'
                      justify='center'
                      boxSize={10}
                      borderRadius='full'
                      bg='blue.subtle'
                      color='blue.fg'
                      flexShrink={0}
                    >
                      <Icon as={Database} boxSize={5} />
                    </Flex>
                    <Box>
                      <Text fontWeight='semibold' color='fg' mb={1}>
                        1. La DNCP publica los datos brutos
                      </Text>
                      <Text fontSize='sm' color='fg.muted' lineHeight='tall'>
                        Cada licitación, contrato y modificación se registra en el portal público de
                        la DNCP en formato OCDS.
                      </Text>
                    </Box>
                  </Flex>
                </List.Item>

                <List.Item>
                  <Flex align='flex-start' gap={4}>
                    <Flex
                      align='center'
                      justify='center'
                      boxSize={10}
                      borderRadius='full'
                      bg='amber.subtle'
                      color='amber.fg'
                      flexShrink={0}
                    >
                      <Icon as={Eye} boxSize={5} />
                    </Flex>
                    <Box>
                      <Text fontWeight='semibold' color='fg' mb={1}>
                        2. Nuestra plataforma los procesa
                      </Text>
                      <Text fontSize='sm' color='fg.muted' lineHeight='tall'>
                        Aplicamos reglas de detección basadas en la metodología de la OCP para
                        identificar patrones de riesgo.
                      </Text>
                    </Box>
                  </Flex>
                </List.Item>

                <List.Item>
                  <Flex align='flex-start' gap={4}>
                    <Flex
                      align='center'
                      justify='center'
                      boxSize={10}
                      borderRadius='full'
                      bg='teal.subtle'
                      color='teal.fg'
                      flexShrink={0}
                    >
                      <Icon as={MousePointerClick} boxSize={5} />
                    </Flex>
                    <Box>
                      <Text fontWeight='semibold' color='fg' mb={1}>
                        3. Vos vigilás
                      </Text>
                      <Text fontSize='sm' color='fg.muted' lineHeight='tall'>
                        Explorá los indicadores, filtrá por entidad o año, y compartí tus hallazgos.
                        La transparencia se construye entre todos.
                      </Text>
                    </Box>
                  </Flex>
                </List.Item>
              </List.Root>
            </Box>
          </SimpleGrid>
        </Container>
      </Box>

      <Box
        as='footer'
        bg='gray.900'
        color='gray.400'
        py={{ base: 8, md: 12 }}
        borderTop='4px solid'
        borderColor='blue.600'
      >
        <Container maxW='6xl'>
          {/* <SimpleGrid columns={{ base: 1, md: 3 }} gap={8} mb={8}> */}
          <SimpleGrid columns={{ base: 1, md: 2 }} gap={8} mb={8}>
            <Box>
              <Text fontWeight='bold' color='white' fontSize='lg' mb={3}>
                Control Ciudadano DNCP
              </Text>
              <Text fontSize='sm' lineHeight='tall'>
                Proyecto académico de la Universidad Autónoma de Asunción (UAA).
              </Text>
            </Box>

            {/* <Box>
              <Text fontWeight='bold' color='white' fontSize='lg' mb={3}>
                Código Abierto
              </Text>
              <Text fontSize='sm' lineHeight='tall' mb={3}>
                Todo el código de esta plataforma está disponible públicamente. Creemos que la
                transparencia empieza por casa.
              </Text>
              <Link
                href='https://github.com'
                target='_blank'
                rel='noopener noreferrer'
                color='blue.400'
                fontWeight='medium'
                fontSize='sm'
                display='inline-flex'
                alignItems='center'
                gap={2}
                _hover={{ color: 'blue.300' }}
              >
                <Icon as={Code2} boxSize={4} />
                Ver repositorio en GitHub
              </Link>
            </Box> */}

            <Box>
              <Text fontWeight='bold' color='white' fontSize='lg' mb={3}>
                Aclaración
              </Text>
              <Text fontSize='sm' lineHeight='tall' color='gray.500'>
                Los datos mostrados en esta plataforma son un reflejo automatizado del portal de la
                DNCP y{' '}
                <Text as='strong' color='gray.400'>
                  no constituyen sentencias legales ni acusaciones formales
                </Text>
                . Los indicadores señalan patrones estadísticos que merecen atención ciudadana, no
                determinan responsabilidades.
              </Text>
            </Box>
          </SimpleGrid>

          <Box borderTop='1px solid' borderColor='gray.700' pt={6}>
            <DataUpdatedAt textAlign='center' color='gray.400' mb={2} />
            <Text fontSize='xs' textAlign='center' color='gray.500'>
              &copy; {new Date().getFullYear()} Control Ciudadano DNCP — Universidad Autónoma de
              Asunción (UAA). Todos los derechos reservados.
            </Text>
          </Box>
        </Container>
      </Box>
    </Box>
  );
}
