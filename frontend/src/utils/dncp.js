// El buscador de licitaciones del portal encuentra el proceso por su numero de
// licitacion, que es la parte del ocid despues del prefijo de la DNCP:
// ocds-03ad3f-434749-1 -> 434749.
// No se arma la pagina directa del proceso porque cambia segun el tipo
// (convocatoria, sin difusion, etc.).
const PORTAL_DNCP = 'https://www.contrataciones.gov.py';

export function urlPortalDNCP(ocid) {
  const m = /^ocds-03ad3f-(\d+)/.exec(ocid ?? '');
  return m ? `${PORTAL_DNCP}/buscador/licitaciones.html?nro_nombre_licitacion=${m[1]}` : null;
}

// La ficha de un contrato (documentos, modificaciones, terminacion) si tiene pagina
// directa, con el award_id del contrato. Para R063 y R064.
// El buscador de contratos no sirve: no encuentra las contrataciones por excepcion (CE-).
export function urlFichaContrato(awardId) {
  return awardId ? `${PORTAL_DNCP}/licitaciones/adjudicacion/contrato/${awardId}.html` : null;
}
