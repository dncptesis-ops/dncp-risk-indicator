import { useState } from 'react';
import { IconButton, Popover, Portal, Text } from '@chakra-ui/react';
import { Info } from 'lucide-react';

// Icono con una aclaracion sobre los datos. Con mouse se abre al pasar por encima;
// en el celular (no hay hover) y con teclado se abre al tocarlo o con Enter.
export default function NotaDatos({ label, children }) {
  const [open, setOpen] = useState(false);
  const conMouse = e => e.pointerType === 'mouse';

  return (
    <Popover.Root
      open={open}
      onOpenChange={e => setOpen(e.open)}
      positioning={{ placement: 'bottom-start' }}
    >
      <Popover.Trigger asChild>
        <IconButton
          aria-label={label}
          variant='ghost'
          size='xs'
          color='fg.muted'
          onPointerEnter={e => conMouse(e) && setOpen(true)}
          onPointerLeave={e => conMouse(e) && setOpen(false)}
        >
          <Info />
        </IconButton>
      </Popover.Trigger>
      <Portal>
        <Popover.Positioner>
          <Popover.Content maxW='sm'>
            <Popover.Arrow>
              <Popover.ArrowTip />
            </Popover.Arrow>
            <Popover.Body>
              <Text fontSize='sm'>{children}</Text>
            </Popover.Body>
          </Popover.Content>
        </Popover.Positioner>
      </Portal>
    </Popover.Root>
  );
}
