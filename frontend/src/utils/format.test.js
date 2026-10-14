import { describe, expect, it } from 'vitest';
import { formatDate, formatDateTime, formatNumber, formatPercentage } from './format';

describe('formatNumber', () => {
  it('usa el punto como separador de miles (es-PY)', () => {
    expect(formatNumber(54256)).toBe('54.256');
  });

  it('muestra "—" cuando no hay dato, nunca 0', () => {
    expect(formatNumber(null)).toBe('—');
    expect(formatNumber(undefined)).toBe('—');
  });
});

describe('formatPercentage', () => {
  it('usa coma decimal y un solo decimal', () => {
    expect(formatPercentage(2.2)).toBe('2,2%');
    expect(formatPercentage(33.94)).toBe('33,9%');
    expect(formatPercentage(15)).toBe('15,0%');
  });

  it('muestra "—" cuando no hay dato', () => {
    expect(formatPercentage(null)).toBe('—');
  });
});

describe('formatDate', () => {
  it('formatea una fecha en español', () => {
    expect(formatDate('2023-03-15')).toMatch(/15.*mar.*2023/);
  });

  it('muestra "—" cuando no hay fecha', () => {
    expect(formatDate(null)).toBe('—');
  });
});

describe('formatDate con hora', () => {
  it('usa el día de Paraguay, no el de UTC ni el del navegador', () => {
    // 01:30 UTC del 25 = 22:30 del 24 en Paraguay.
    expect(formatDate('2026-07-25T01:30:00Z')).toMatch(/24.*jul.*2026/);
  });

  it('muestra "—" con un valor inválido', () => {
    expect(formatDate('basura')).toBe('—');
  });
});

describe('formatDateTime', () => {
  it('muestra la hora de Paraguay (UTC-3), no la UTC', () => {
    expect(formatDateTime('2026-09-04T15:12:39Z')).toMatch(/4.*sept?.*2026.*12:12/);
  });

  it('muestra "—" cuando no hay dato o es inválido', () => {
    expect(formatDateTime(null)).toBe('—');
    expect(formatDateTime('basura')).toBe('—');
  });
});
