// Endpoints de R018 (licitaciones con un solo oferente).
import { apiGet } from '../../../lib/apiClient';

export const fetchR018Kpi = params => apiGet('/r018/kpi', params);

export const fetchR018Monthly = params => apiGet('/r018/monthly', params);

export const fetchR018TopEntities = params => apiGet('/r018/top-entities', params);

export const fetchR018Suppliers = params => apiGet('/r018/suppliers', params);

export const fetchR018Tenders = params => apiGet('/r018/tenders', params);
