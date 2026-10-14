import { useEffect } from 'react';
import { useNavigate, useRouteError } from 'react-router-dom';
import { Box, Button, Container, Heading, HStack, Icon, Text } from '@chakra-ui/react';
import { TriangleAlert } from 'lucide-react';

// Se muestra si una pagina falla al dibujarse. El detalle queda en la consola,
// al usuario solo se le ofrece recargar o volver al inicio.
export default function ErrorPage() {
  const error = useRouteError();
  const navigate = useNavigate();

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <Container maxW='2xl' py={{ base: 16, md: 24 }} textAlign='center'>
      <Box
        display='inline-flex'
        alignItems='center'
        justifyContent='center'
        boxSize={16}
        borderRadius='full'
        bg='red.subtle'
        color='red.fg'
        mb={6}
      >
        <Icon as={TriangleAlert} boxSize={8} />
      </Box>
      <Heading as='h1' size={{ base: 'xl', md: '2xl' }} color='fg' mb={4}>
        No se pudo mostrar esta página
      </Heading>
      <Text color='fg.muted' mb={8}>
        Ocurrió un error inesperado. Probá recargar la página o volver al inicio.
      </Text>
      <HStack justify='center' gap={3}>
        <Button colorPalette='blue' onClick={() => window.location.reload()}>
          Recargar
        </Button>
        <Button variant='outline' onClick={() => navigate('/', { replace: true })}>
          Volver al inicio
        </Button>
      </HStack>
    </Container>
  );
}
