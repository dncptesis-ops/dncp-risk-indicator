import { ClientOnly, IconButton, Skeleton } from '@chakra-ui/react';
import { ThemeProvider } from 'next-themes';
import * as React from 'react';
import { Moon, Sun } from 'lucide-react';
import { useColorMode } from '@/hooks/use-color-mode';

export function ColorModeProvider(props) {
  return <ThemeProvider attribute='class' disableTransitionOnChange {...props} />;
}

export function ColorModeIcon() {
  const { colorMode } = useColorMode();
  return colorMode === 'dark' ? <Moon /> : <Sun />;
}

export const ColorModeButton = React.forwardRef(function ColorModeButton(props, ref) {
  const { toggleColorMode } = useColorMode();
  return (
    <ClientOnly fallback={<Skeleton boxSize='9' />}>
      <IconButton
        onClick={toggleColorMode}
        variant='ghost'
        color='white'
        _hover={{ bg: 'whiteAlpha.200' }}
        aria-label='Cambiar el modo de color'
        size='sm'
        ref={ref}
        {...props}
        css={{
          _icon: {
            width: '5',
            height: '5',
          },
        }}
      >
        <ColorModeIcon />
      </IconButton>
    </ClientOnly>
  );
});
