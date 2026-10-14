// Cliente de la API. La URL base sale de VITE_API_BASE_URL.

const BASE_URL = import.meta.env.VITE_API_BASE_URL;

if (!BASE_URL) {
  // Error legible en desarrollo si falta la configuración.
  throw new Error(
    'VITE_API_BASE_URL no está definida. Creá un archivo .env en la raíz del proyecto ' +
      'con: VITE_API_BASE_URL=http://127.0.0.1:8000 (ver .env.example).',
  );
}

// arma el query string sin los valores null/undefined
function buildQueryString(params = {}) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== '') {
      search.append(key, String(value));
    }
  }
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

// GET a la API; lanza un Error si la respuesta no es OK
export async function apiGet(path, params = {}) {
  const url = `${BASE_URL.replace(/\/$/, '')}${path}${buildQueryString(params)}`;

  let res;
  try {
    res = await fetch(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
  } catch (err) {
    // Error de red / CORS / backend caído.
    throw new Error(`No se pudo conectar con la API (${url}): ${err.message}`, { cause: err });
  }

  if (!res.ok) {
    throw new Error(`Error ${res.status} ${res.statusText} en ${path}`);
  }

  return res.json();
}
