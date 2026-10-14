import { Alert, Box, Icon } from '@chakra-ui/react';
import { Info } from 'lucide-react';

// Caja que explica en palabras simples qué mide el indicador.
export default function ContextBox({ title = '¿Qué significa esto?', description }) {
  if (!description) return null;

  return (
    <Alert.Root colorPalette='blue' variant='subtle' borderRadius='xl' borderWidth='1px'>
      <Alert.Indicator>
        <Icon asChild boxSize={5} color='blue.fg'>
          <Info />
        </Icon>
      </Alert.Indicator>
      <Box>
        <Alert.Title fontWeight='semibold' fontSize='md' mb={1}>
          {title}
        </Alert.Title>
        <Alert.Description fontSize='sm' color='fg.muted' lineHeight='tall'>
          {description}
        </Alert.Description>
      </Box>
    </Alert.Root>
  );
}
