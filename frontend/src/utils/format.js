// Número con punto de miles: 54256 -> "54.256"
export function formatNumber(value) {
  if (value == null || isNaN(value)) return '—';
  return Number(value).toLocaleString('es-PY');
}

// Porcentaje con un decimal: 2.2 -> "2,2%", null -> "—"
export function formatPercentage(value) {
  if (value == null || isNaN(value)) return '—';
  return (
    Number(value).toLocaleString('es-PY', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }) + '%'
  );
}

// Paraguay es UTC-3 todo el año desde 2024. Con 'America/Asuncion' algunos
// navegadores todavía dan UTC-4, por eso el offset va fijo.
const OFFSET_PARAGUAY_MS = -3 * 60 * 60 * 1000;

function enHoraParaguay(value) {
  const d = new Date(value);
  return isNaN(d) ? null : new Date(d.getTime() + OFFSET_PARAGUAY_MS);
}

// Fecha en hora de Paraguay: "2026-07-24T04:00:00Z" -> "24 jul 2026"
export function formatDate(value) {
  if (!value) return '—';
  const d = value.includes('T') ? enHoraParaguay(value) : new Date(`${value}T00:00:00Z`);
  if (!d || isNaN(d)) return '—';
  return d.toLocaleDateString('es-PY', {
    timeZone: 'UTC',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

// Fecha y hora de Paraguay: "2026-09-04T15:12:39Z" -> "4 sept. 2026, 12:12"
export function formatDateTime(value) {
  if (!value) return '—';
  const d = enHoraParaguay(value);
  if (!d) return '—';
  return d.toLocaleString('es-PY', {
    timeZone: 'UTC',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  });
}

export const METHOD_LABEL = {
  open: 'Abierto',
  selective: 'Selectivo',
};
