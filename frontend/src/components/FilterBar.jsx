import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Box,
  Button,
  HStack,
  Input,
  Portal,
  Popover,
  Select,
  Text,
  createListCollection,
} from '@chakra-ui/react';
import { ChevronDown } from 'lucide-react';

const PROC_METHODS = [
  { value: '', label: 'Todos los métodos' },
  { value: 'open', label: 'Abierto (Licitación Pública)' },
  { value: 'selective', label: 'Selectivo' },
];

// minúsculas y sin tildes, para buscar
const normalizeText = text =>
  text
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();

// Filtros de año, entidad y (en R018) método de contratación.
export default function FilterBar({
  filters = {},
  onFiltersChange,
  showProcMethod = false,
  buyers = [],
  years = [],
}) {
  const [buyerSearch, setBuyerSearch] = useState('');
  const [buyerPopoverOpen, setBuyerPopoverOpen] = useState(false);
  const buyerSearchRef = useRef(null);

  const handleChange = useCallback(
    (key, value) => {
      // Convierte string vacío a undefined para limpiarlo
      const cleaned = value === '' ? undefined : value;
      onFiltersChange?.({ ...filters, [key]: cleaned });
    },
    [filters, onFiltersChange],
  );

  // Enfoca el buscador al abrir el popover
  useEffect(() => {
    if (buyerPopoverOpen) {
      requestAnimationFrame(() => buyerSearchRef.current?.focus());
    }
  }, [buyerPopoverOpen]);

  const selectedBuyer = buyers.find(b => b.value === filters.buyer_id);

  const handleBuyerSelect = useCallback(
    value => {
      handleChange('buyer_id', value || undefined);
      setBuyerPopoverOpen(false);
      setBuyerSearch('');
    },
    [handleChange],
  );

  const yearItems = useMemo(() => {
    const items = years.map(y => ({ value: y, label: String(y) }));
    items.unshift({ value: '', label: 'Todos los años' });
    return items;
  }, [years]);

  const yearCollection = createListCollection({ items: yearItems });
  const methodCollection = createListCollection({ items: PROC_METHODS });
  const filteredBuyers = useMemo(() => {
    if (!buyerSearch.trim()) return buyers;
    const search = normalizeText(buyerSearch.trim());
    return buyers.filter(b => normalizeText(b.label).includes(search));
  }, [buyers, buyerSearch]);

  const buyerItems = [{ value: '', label: 'Todas las entidades' }, ...filteredBuyers];

  return (
    <Box
      as='section'
      bg='bg.subtle'
      borderWidth='1px'
      borderColor='border'
      borderRadius='xl'
      px={{ base: 4, md: 6 }}
      py={4}
      shadow='xs'
      aria-label='Panel de filtros'
    >
      <HStack gap={4} wrap='wrap'>
        {/* Año */}
        <Select.Root
          collection={yearCollection}
          value={[filters.year ? String(filters.year) : '']}
          onValueChange={details => {
            const val = details.value?.[0] ?? '';
            handleChange('year', val ? Number(val) : undefined);
          }}
          size='sm'
          width={{ base: 'full', md: '180px' }}
        >
          <Select.Label srOnly>Año</Select.Label>
          <Select.Control>
            <Select.Trigger>
              <Select.ValueText placeholder='Año' />
            </Select.Trigger>
            <Select.IndicatorGroup>
              <Select.Indicator />
            </Select.IndicatorGroup>
          </Select.Control>
          <Portal>
            <Select.Positioner>
              <Select.Content>
                {yearCollection.items.map(item => (
                  <Select.Item item={item} key={item.value}>
                    {item.label}
                  </Select.Item>
                ))}
              </Select.Content>
            </Select.Positioner>
          </Portal>
        </Select.Root>

        {/* Entidad compradora */}
        <Popover.Root
          open={buyerPopoverOpen}
          onOpenChange={details => {
            setBuyerPopoverOpen(details.open);
            if (details.open) setBuyerSearch('');
          }}
          positioning={{ sameWidth: true, placement: 'bottom-start' }}
          size='sm'
        >
          <Popover.Trigger asChild>
            <Button
              variant='outline'
              size='sm'
              width={{ base: 'full', md: '280px' }}
              justifyContent='space-between'
              fontWeight='normal'
              aria-label='Entidad compradora'
            >
              <Text truncate color={selectedBuyer ? undefined : 'fg.muted'}>
                {selectedBuyer?.label ?? 'Entidad compradora'}
              </Text>
              <ChevronDown size='1em' />
            </Button>
          </Popover.Trigger>
          <Portal>
            <Popover.Positioner>
              <Popover.Content>
                <Popover.Body p={0}>
                  <Box p={2} borderBottomWidth='1px' borderColor='border'>
                    <Input
                      ref={buyerSearchRef}
                      size='sm'
                      placeholder='Buscar entidad...'
                      value={buyerSearch}
                      onChange={e => setBuyerSearch(e.target.value)}
                    />
                  </Box>
                  <Box maxH='260px' overflowY='auto' py={1}>
                    {buyerItems.map(item => {
                      const isSelected = (filters.buyer_id ?? '') === item.value;
                      return (
                        <Box
                          as='button'
                          type='button'
                          key={item.value}
                          onClick={() => handleBuyerSelect(item.value)}
                          w='full'
                          textAlign='start'
                          px={3}
                          py={1.5}
                          fontSize='sm'
                          cursor='pointer'
                          bg={isSelected ? 'bg.emphasized' : undefined}
                          fontWeight={isSelected ? 'medium' : 'normal'}
                          _hover={{ bg: 'bg.emphasized' }}
                        >
                          {item.label}
                        </Box>
                      );
                    })}
                    {filteredBuyers.length === 0 && buyerSearch.trim() && (
                      <Box px={3} py={2} fontSize='sm' color='fg.muted'>
                        No se encontraron entidades
                      </Box>
                    )}
                  </Box>
                </Popover.Body>
              </Popover.Content>
            </Popover.Positioner>
          </Portal>
        </Popover.Root>

        {/* Método de contratación (solo R018) */}
        {showProcMethod && (
          <Select.Root
            collection={methodCollection}
            value={[filters.proc_method ?? '']}
            onValueChange={details => {
              handleChange('proc_method', details.value?.[0] || undefined);
            }}
            size='sm'
            width={{ base: 'full', md: '220px' }}
          >
            <Select.Label srOnly>Método de contratación</Select.Label>
            <Select.Control>
              <Select.Trigger>
                <Select.ValueText placeholder='Método de contratación' />
              </Select.Trigger>
              <Select.IndicatorGroup>
                <Select.Indicator />
              </Select.IndicatorGroup>
            </Select.Control>
            <Portal>
              <Select.Positioner>
                <Select.Content>
                  {methodCollection.items.map(item => (
                    <Select.Item item={item} key={item.value}>
                      {item.label}
                    </Select.Item>
                  ))}
                </Select.Content>
              </Select.Positioner>
            </Portal>
          </Select.Root>
        )}
      </HStack>
    </Box>
  );
}
