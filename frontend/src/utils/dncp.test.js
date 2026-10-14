import { describe, expect, it } from 'vitest';
import { urlFichaContrato, urlPortalDNCP } from './dncp';

describe('urlPortalDNCP', () => {
  it('busca el proceso por su numero de licitacion', () => {
    expect(urlPortalDNCP('ocds-03ad3f-434749-1')).toBe(
      'https://www.contrataciones.gov.py/buscador/licitaciones.html?nro_nombre_licitacion=434749',
    );
  });

  it('funciona con ocid sin el sufijo final', () => {
    expect(urlPortalDNCP('ocds-03ad3f-415212')).toMatch(/nro_nombre_licitacion=415212$/);
  });

  it('devuelve null si no hay ocid o no es de la DNCP', () => {
    expect(urlPortalDNCP(null)).toBeNull();
    expect(urlPortalDNCP('ocds-otro-123')).toBeNull();
  });
});

describe('urlFichaContrato', () => {
  it('arma la ficha con el award_id, del sistema viejo o del nuevo', () => {
    expect(urlFichaContrato('431467-distribuidora-ypacarai-sa-1')).toBe(
      'https://www.contrataciones.gov.py/licitaciones/adjudicacion/contrato/431467-distribuidora-ypacarai-sa-1.html',
    );
    expect(urlFichaContrato('1f0925ed-7c33-6fe2-aa2b-217a63bc8f4d')).toMatch(
      /contrato\/1f0925ed-7c33-6fe2-aa2b-217a63bc8f4d\.html$/,
    );
  });

  it('devuelve null si el contrato no tiene award_id', () => {
    expect(urlFichaContrato(null)).toBeNull();
  });
});
