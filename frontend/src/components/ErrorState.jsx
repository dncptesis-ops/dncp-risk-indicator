import { Alert, Button } from '@chakra-ui/react';
import { RotateCw } from 'lucide-react';

// Aviso de error con botón para reintentar. Se usa en vez de mostrar 0 o vacío.
export default function ErrorState({ title = 'No se pudieron cargar los datos', onRetry }) {
  return (
    <Alert.Root status='error' borderRadius='xl' alignItems='center'>
      <Alert.Indicator />
      <Alert.Content>
        <Alert.Title>{title}</Alert.Title>
        <Alert.Description>
          La API no respondió. Revisá la conexión o intentá de nuevo en unos minutos.
        </Alert.Description>
      </Alert.Content>
      {onRetry && (
        <Button size='sm' variant='outline' colorPalette='red' onClick={() => onRetry()}>
          <RotateCw size={14} />
          Reintentar
        </Button>
      )}
    </Alert.Root>
  );
}
