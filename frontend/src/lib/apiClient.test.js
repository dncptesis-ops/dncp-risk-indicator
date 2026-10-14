import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiGet } from './apiClient';

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubFetch(respuesta) {
  const fetchMock = vi.fn().mockResolvedValue(respuesta);
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

describe('apiGet', () => {
  it('arma la URL con la base configurada y omite los parámetros vacíos', async () => {
    const fetchMock = stubFetch({ ok: true, json: () => Promise.resolve({ ok: 1 }) });

    const data = await apiGet('/r018/kpi', { year: 2024, buyer_id: '', proc_method: null });

    expect(data).toEqual({ ok: 1 });
    expect(fetchMock).toHaveBeenCalledWith(
      'http://api.test/r018/kpi?year=2024',
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('convierte una respuesta HTTP de error en un Error con status y ruta', async () => {
    stubFetch({ ok: false, status: 422, statusText: 'Unprocessable Entity' });

    await expect(apiGet('/r018/kpi', { year: 1900 })).rejects.toThrow(
      'Error 422 Unprocessable Entity en /r018/kpi',
    );
  });

  it('explica un fallo de red (API caída o CORS)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    await expect(apiGet('/r063/kpi')).rejects.toThrow(/No se pudo conectar con la API/);
  });
});
