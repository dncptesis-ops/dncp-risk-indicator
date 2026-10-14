import {
  Box,
  Container,
  Flex,
  Text,
  HStack,
  IconButton,
  useBreakpointValue,
  Menu,
  Portal,
} from '@chakra-ui/react';
import { Outlet, NavLink, ScrollRestoration, useLocation } from 'react-router-dom';
import { Home, AlertTriangle, FileX, Edit3, Menu as MenuIcon } from 'lucide-react';
import NavItem from '@/components/layout/NavItem';
import { ColorModeButton } from '@/components/ui/color-mode';
import DataUpdatedAt from '@/components/DataUpdatedAt';

const NAV_LINKS = [
  { to: '/', icon: Home, label: 'Inicio' },
  { to: '/r018', icon: AlertTriangle, label: 'R018: Única Oferta' },
  { to: '/r063', icon: FileX, label: 'R063: Contrato no Publicado' },
  { to: '/r064', icon: Edit3, label: 'R064: Contrato Modificado' },
];

const MobileMenuItem = ({ to, icon, children }) => (
  <Menu.Item
    asChild
    value={to}
    color='white'
    bg='transparent'
    gap={2}
    px={3}
    py={2}
    _hover={{ bg: 'whiteAlpha.200', textDecoration: 'none' }}
    _currentPage={{ bg: 'whiteAlpha.300', fontWeight: 'bold' }}
    transition='all 0.2s'
  >
    <NavLink to={to} end={to === '/'}>
      <Box as={icon} boxSize={4} color='white' />
      <Text color='white' fontWeight='medium'>
        {children}
      </Text>
    </NavLink>
  </Menu.Item>
);

export const MainLayout = () => {
  // con los nombres completos el menu recien entra en una linea desde xl (1280px)
  const isMobile = useBreakpointValue({ base: true, xl: false });
  // El inicio tiene su propio pie, que ya muestra la fecha de actualización.
  const esInicio = useLocation().pathname === '/';

  return (
    <Flex direction='column' minH='100vh' bg='bg.subtle'>
      <Box
        as='nav'
        bg='gray.800'
        px={{ base: 2, md: 8 }}
        py={{ base: 2, md: 3 }}
        shadow='md'
        position='sticky'
        top={0}
        zIndex='sticky'
      >
        <Flex maxW='7xl' mx='auto' align='center' justify='space-between'>
          <Text
            fontSize={{ base: 'md', md: 'xl' }}
            fontWeight='bold'
            letterSpacing='tight'
            color='white'
            lineClamp={1}
          >
            Control Ciudadano DNCP
          </Text>

          <HStack gap={2}>
            {!isMobile &&
              NAV_LINKS.map(link => (
                <NavItem key={link.to} to={link.to} icon={link.icon}>
                  {link.label}
                </NavItem>
              ))}

            {isMobile && (
              <Menu.Root closeOnSelect>
                <Menu.Trigger asChild>
                  <IconButton
                    variant='ghost'
                    color='white'
                    aria-label='Abrir menú de navegación'
                    _hover={{ bg: 'whiteAlpha.200' }}
                  >
                    <MenuIcon size={20} color='white' />
                  </IconButton>
                </Menu.Trigger>
                <Portal>
                  <Menu.Positioner>
                    <Menu.Content
                      bg='gray.800'
                      borderColor='whiteAlpha.300'
                      minW='200px'
                      p={1}
                      color='white'
                    >
                      {NAV_LINKS.map(link => (
                        <MobileMenuItem key={link.to} to={link.to} icon={link.icon}>
                          {link.label}
                        </MobileMenuItem>
                      ))}
                    </Menu.Content>
                  </Menu.Positioner>
                </Portal>
              </Menu.Root>
            )}

            <ColorModeButton />
          </HStack>
        </Flex>
      </Box>

      <Box as='main' p={{ base: 4, md: 8 }} flex='1'>
        <Box maxW='7xl' mx='auto'>
          <Outlet />
        </Box>
      </Box>

      {!esInicio && (
        <Box as='footer' borderTopWidth='1px' px={{ base: 4, md: 8 }} py={4}>
          <Container maxW='6xl'>
            <DataUpdatedAt />
          </Container>
        </Box>
      )}

      <ScrollRestoration />
    </Flex>
  );
};
