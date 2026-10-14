import { Link as ChakraLink, Text, Icon } from '@chakra-ui/react';
import { NavLink } from 'react-router-dom';

// `asChild`: Chakra aplica sus estilos sobre el NavLink de React Router. El
// NavLink activo lleva aria-current="page", que es lo que mira `_currentPage`.
const NavItem = ({ to, icon, children }) => (
  <ChakraLink
    asChild
    px={4}
    py={2}
    borderRadius='md'
    _hover={{ bg: 'whiteAlpha.200', textDecoration: 'none' }}
    _currentPage={{ bg: 'whiteAlpha.300', fontWeight: 'bold' }}
    display='flex'
    alignItems='center'
    gap={2}
    color='white'
    transition='all 0.2s'
  >
    <NavLink to={to} end={to === '/'}>
      <Icon as={icon} boxSize={4} />
      <Text fontWeight='medium' whiteSpace='nowrap'>
        {children}
      </Text>
    </NavLink>
  </ChakraLink>
);

export default NavItem;
