import { Box, Button, Container, Flex, Heading, Icon, Text } from '@chakra-ui/react';
import { ChevronDown } from 'lucide-react';

// Portada de la página de inicio.
export default function HeroSection({ scrollTargetRef }) {
  const handleScroll = () => {
    scrollTargetRef?.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <Box as='section' bg='bg.muted' borderBottom='1px solid' borderColor='border'>
      <Container maxW='4xl' py={{ base: 16, md: 28 }}>
        <Text
          display='inline-block'
          bg='blue.subtle'
          color='blue.fg'
          px={4}
          py={1}
          borderRadius='full'
          fontWeight='semibold'
          fontSize='sm'
          mb={6}
        >
          Proyecto Académico · Universidad Autónoma de Asunción (UAA)
        </Text>

        <Heading
          as='h1'
          size={{ base: '3xl', md: '5xl' }}
          fontWeight='extrabold'
          lineHeight='1.1'
          letterSpacing='tight'
          color='fg'
          mb={6}
        >
          Los recursos públicos,
          <br />
          <Text as='span' color='blue.solid'>
            bajo lupa ciudadana.
          </Text>
        </Heading>

        <Text
          fontSize={{ base: 'md', md: 'xl' }}
          color='fg.muted'
          maxW='2xl'
          lineHeight='tall'
          mb={10}
        >
          Esta plataforma traduce millones de datos de contrataciones públicas en tres alertas
          claras para que cualquier ciudadano pueda exigir mayor transparencia, sin necesidad de ser
          experto en leyes ni en compras públicas.
        </Text>

        <Button
          size='lg'
          colorPalette='blue'
          fontSize='md'
          px={8}
          py={6}
          shadow='md'
          _hover={{ shadow: 'lg', transform: 'translateY(-2px)' }}
          transition='all 0.2s'
          onClick={handleScroll}
          aria-label='Explorar los indicadores de riesgo'
        >
          <Flex align='center' gap={2}>
            Explorar los Indicadores
            <Icon as={ChevronDown} boxSize={5} />
          </Flex>
        </Button>
      </Container>
    </Box>
  );
}
