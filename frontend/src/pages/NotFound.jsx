import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Button, Container, Heading, Icon, Text } from '@chakra-ui/react';
import { FileX } from 'lucide-react';

const REDIRECT_SECONDS = 5;

export default function NotFound() {
  const navigate = useNavigate();
  const [countdown, setCountdown] = useState(REDIRECT_SECONDS);

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          navigate('/', { replace: true });
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [navigate]);

  return (
    <Box bg='bg.muted' minH='calc(100vh - 200px)'>
      <Container maxW='2xl' py={{ base: 20, md: 32 }} textAlign='center'>
        <Box
          display='inline-flex'
          alignItems='center'
          justifyContent='center'
          boxSize={20}
          borderRadius='full'
          bg='red.subtle'
          color='red.fg'
          mb={8}
        >
          <Icon as={FileX} boxSize={10} />
        </Box>

        <Heading
          as='h1'
          size={{ base: '4xl', md: '5xl' }}
          fontWeight='extrabold'
          lineHeight='1.1'
          letterSpacing='tight'
          color='fg'
          mb={4}
        >
          404
        </Heading>

        <Heading as='h2' size={{ base: 'xl', md: '2xl' }} fontWeight='bold' color='fg' mb={6}>
          Esta página{' '}
          <Text as='span' color='blue.solid'>
            no existe
          </Text>
        </Heading>

        <Text fontSize='lg' color='fg.muted' maxW='md' mx='auto' mb={8} lineHeight='tall'>
          La ruta que buscás no fue encontrada o fue movida.
        </Text>

        <Text fontSize='sm' color='fg.muted' mb={8}>
          Serás redirigido al inicio en{' '}
          <Text as='span' fontWeight='bold' color='blue.solid'>
            {countdown}
          </Text>{' '}
          {countdown === 1 ? 'segundo' : 'segundos'}...
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
          onClick={() => navigate('/', { replace: true })}
        >
          Volver al inicio
        </Button>
      </Container>
    </Box>
  );
}
