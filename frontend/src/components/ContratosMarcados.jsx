import { Button, Icon, Popover, Portal, Stack, Text } from '@chakra-ui/react';
import { ChevronDown } from 'lucide-react';
import EnlaceExterno from './EnlaceExterno';
import { urlFichaContrato } from '../utils/dncp';

// Enlaces a la ficha de los contratos marcados de un proceso (R063 y R064).
// Con uno solo va su codigo; con varios, un boton que abre la lista, para que la
// celda no crezca (hay procesos con decenas de contratos marcados).
function FichaContrato({ contrato }) {
  const href = urlFichaContrato(contrato.award_id);
  if (!href) {
    return <Text fontSize='sm'>{contrato.contract_id}</Text>;
  }
  return (
    <EnlaceExterno
      href={href}
      label={`Ficha del contrato ${contrato.contract_id} en el portal de la DNCP`}
    >
      {contrato.contract_id}
    </EnlaceExterno>
  );
}

// Sin contratos no muestra nada: pasa si la API publicada es anterior a este campo
export default function ContratosMarcados({ contratos = [] }) {
  if (contratos.length === 0) return null;
  if (contratos.length === 1) return <FichaContrato contrato={contratos[0]} />;

  return (
    <Popover.Root positioning={{ placement: 'bottom-end' }} lazyMount unmountOnExit>
      <Popover.Trigger asChild>
        <Button
          variant='plain'
          size='xs'
          fontSize='sm'
          colorPalette='blue'
          color='colorPalette.fg'
          px={0}
          h='auto'
        >
          Ver los {contratos.length}
          <Icon asChild boxSize={3.5}>
            <ChevronDown />
          </Icon>
        </Button>
      </Popover.Trigger>
      <Portal>
        <Popover.Positioner>
          <Popover.Content w='auto' minW='56'>
            <Popover.Arrow>
              <Popover.ArrowTip />
            </Popover.Arrow>
            <Popover.Body p={3}>
              <Text fontSize='xs' color='fg.muted' mb={2}>
                Ficha de cada contrato en la DNCP
              </Text>
              <Stack as='ul' listStyleType='none' gap={1.5} maxH='60' overflowY='auto' pr={1}>
                {contratos.map(c => (
                  <li key={c.contract_id}>
                    <FichaContrato contrato={c} />
                  </li>
                ))}
              </Stack>
            </Popover.Body>
          </Popover.Content>
        </Popover.Positioner>
      </Portal>
    </Popover.Root>
  );
}
