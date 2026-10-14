// Estilos de columna por tipo:
// - text: nombres y títulos, hacen salto de línea
// - short: fechas, RUC, etiquetas, no se parten
// - number: alineado a la derecha
export function headerStyles(col) {
  return {
    whiteSpace: 'normal',
    textAlign: col.type === 'number' ? 'end' : 'start',
    verticalAlign: 'bottom',
    minW: isText(col) ? col.minW : undefined,
  };
}

export function cellStyles(col) {
  if (col.type === 'number') {
    return { whiteSpace: 'nowrap', textAlign: 'end', fontVariantNumeric: 'tabular-nums' };
  }
  if (col.type === 'short') {
    return { whiteSpace: 'nowrap' };
  }
  return { whiteSpace: 'normal', overflowWrap: 'break-word', minW: col.minW };
}

function isText(col) {
  return col.type !== 'number' && col.type !== 'short';
}
