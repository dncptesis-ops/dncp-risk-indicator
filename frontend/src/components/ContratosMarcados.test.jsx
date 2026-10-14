import { cleanup, render, screen } from '@testing-library/react';
import { ChakraProvider, defaultSystem } from '@chakra-ui/react';
import { afterEach, describe, expect, it } from 'vitest';
import ContratosMarcados from './ContratosMarcados';

const renderizar = contratos =>
  render(
    <ChakraProvider value={defaultSystem}>
      <ContratosMarcados contratos={contratos} />
    </ChakraProvider>,
  );

// sin globals de vitest, testing-library no limpia solo entre pruebas
afterEach(cleanup);

describe('ContratosMarcados', () => {
  it('no muestra nada si la API no trae el campo (API anterior)', () => {
    const { container } = renderizar(undefined);
    expect(container.textContent).toBe('');
  });

  it('con un contrato muestra su codigo como enlace a la ficha', () => {
    renderizar([
      { contract_id: 'LC-13006-23-232036', award_id: '434749-victor-hugo-caceres-palacios-2' },
    ]);
    const enlace = screen.getByRole('link', { name: /LC-13006-23-232036/ });
    expect(enlace.getAttribute('href')).toMatch(
      /adjudicacion\/contrato\/434749-victor-hugo-caceres-palacios-2\.html$/,
    );
  });

  it('sin award_id muestra el codigo sin enlace', () => {
    renderizar([{ contract_id: 'LP-24001-25-250441', award_id: null }]);
    expect(screen.getByText('LP-24001-25-250441')).toBeTruthy();
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('con varios muestra un boton con la cantidad', () => {
    renderizar([
      { contract_id: 'A-1', award_id: 'a-1' },
      { contract_id: 'A-2', award_id: 'a-2' },
      { contract_id: 'A-3', award_id: 'a-3' },
    ]);
    expect(screen.getByRole('button', { name: /Ver los 3/ })).toBeTruthy();
  });
});
