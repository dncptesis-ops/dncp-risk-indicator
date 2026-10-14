import {
  Box,
  ButtonGroup,
  IconButton,
  NativeSelect,
  Pagination as ChakraPagination,
  Text,
} from '@chakra-ui/react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];

// Paginación con selector de filas por página (si se pasa onPageSizeChange).
export default function Pagination({
  page,
  totalPages,
  onPageChange,
  totalRows,
  pageSize,
  onPageSizeChange,
}) {
  const count = totalRows ?? totalPages * (pageSize ?? 20);
  const effectivePageSize = pageSize ?? Math.max(1, Math.ceil(count / totalPages));

  const startRow = Math.min((page - 1) * effectivePageSize + 1, count);
  const endRow = Math.min(page * effectivePageSize, count);

  const pageSizeSelect = onPageSizeChange && (
    <Box display='flex' alignItems='center' gap={2}>
      <Text fontSize='sm' color='fg.muted' whiteSpace='nowrap'>
        Mostrar
      </Text>
      <NativeSelect.Root size='sm' width='76px'>
        <NativeSelect.Field
          value={String(pageSize)}
          onChange={e => onPageSizeChange(Number(e.currentTarget.value))}
          aria-label='Registros por página'
        >
          {PAGE_SIZE_OPTIONS.map(size => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </NativeSelect.Field>
        <NativeSelect.Indicator />
      </NativeSelect.Root>
    </Box>
  );

  // el resumen de registros se muestra siempre, los botones solo si hay más de una página
  if (totalPages <= 1) {
    if (totalRows == null && !onPageSizeChange) return null;
    return (
      <Box
        display='flex'
        alignItems='center'
        justifyContent={onPageSizeChange ? 'space-between' : 'center'}
        flexWrap='wrap'
        gap={3}
        mt={4}
      >
        {pageSizeSelect}
        {totalRows != null && (
          <Text fontSize='sm' color='fg.muted' aria-live='polite' role='status'>
            Mostrando {totalRows} de {totalRows} registros
          </Text>
        )}
      </Box>
    );
  }

  return (
    <Box
      display='flex'
      alignItems='center'
      justifyContent='space-between'
      flexWrap='wrap'
      gap={3}
      mt={4}
      role='navigation'
      aria-label='Paginación'
    >
      {pageSizeSelect}

      <ChakraPagination.Root
        count={count}
        pageSize={effectivePageSize}
        page={page}
        onPageChange={e => onPageChange(e.page)}
      >
        <ButtonGroup variant='ghost' size='sm'>
          <ChakraPagination.PrevTrigger asChild>
            <IconButton aria-label='Página anterior'>
              <ChevronLeft />
            </IconButton>
          </ChakraPagination.PrevTrigger>

          <ChakraPagination.Items
            render={pageItem => (
              <IconButton
                variant={{ base: 'ghost', _selected: 'outline' }}
                aria-label={`Ir a página ${pageItem.value}`}
              >
                {pageItem.value}
              </IconButton>
            )}
          />

          <ChakraPagination.NextTrigger asChild>
            <IconButton aria-label='Página siguiente'>
              <ChevronRight />
            </IconButton>
          </ChakraPagination.NextTrigger>
        </ButtonGroup>
      </ChakraPagination.Root>

      {totalRows != null && (
        <Text fontSize='sm' color='fg.muted' aria-live='polite' role='status'>
          Mostrando {startRow}–{endRow} de {totalRows} registros
        </Text>
      )}
    </Box>
  );
}
