import { Box, Flex, Icon, Skeleton, Text } from '@chakra-ui/react';
import { NavLink } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

// Tarjeta de KPI de la página de inicio.
export default function KpiCard({
  icon,
  label,
  value,
  description,
  to,
  accentColor,
  accentBg,
  iconColor = 'white',
  isLoading = false,
}) {
  const isClickable = Boolean(to && to !== '#');

  return (
    <Box
      as={isClickable ? NavLink : 'div'}
      to={isClickable ? to : undefined}
      role={isClickable ? 'group' : 'region'}
      bg={accentBg}
      border='1px solid'
      borderColor='border'
      borderRadius='2xl'
      p={{ base: 6, md: 8 }}
      shadow='sm'
      transition='all 0.25s ease'
      textDecoration='none'
      color='inherit'
      _hover={
        isClickable
          ? {
              shadow: 'lg',
              borderColor: accentColor,
              transform: 'translateY(-4px)',
            }
          : {}
      }
      _focusVisible={
        isClickable
          ? {
              outline: '3px solid',
              outlineColor: accentColor,
              outlineOffset: '2px',
            }
          : {}
      }
    >
      <Flex align='center' gap={3} mb={5}>
        <Flex
          align='center'
          justify='center'
          boxSize={12}
          borderRadius='xl'
          bg={accentColor}
          color={iconColor}
          shadow='md'
        >
          <Icon as={icon} boxSize={6} />
        </Flex>
        <Text fontWeight='semibold' fontSize='lg' color='fg'>
          {label}
        </Text>
      </Flex>

      {isLoading ? (
        <Skeleton height='64px' width='120px' borderRadius='lg' mb={3} />
      ) : (
        <Text
          fontSize={{ base: '4xl', md: '5xl' }}
          fontWeight='extrabold'
          color={accentColor}
          lineHeight='1'
          mb={3}
        >
          {value}
        </Text>
      )}

      {isLoading ? (
        <Skeleton height='20px' width='80%' borderRadius='md' mb={2} />
      ) : (
        description && (
          <Text fontSize='sm' color='fg.muted' lineHeight='tall' mb={isClickable ? 4 : 0}>
            {description}
          </Text>
        )
      )}

      {isClickable && (
        <Flex align='center' gap={1} color={accentColor} fontWeight='medium' fontSize='sm'>
          <Text>Explorar indicador</Text>
          <Icon
            as={ArrowRight}
            boxSize={4}
            transition='transform 0.2s'
            _groupHover={{ transform: 'translateX(4px)' }}
          />
        </Flex>
      )}
    </Box>
  );
}
