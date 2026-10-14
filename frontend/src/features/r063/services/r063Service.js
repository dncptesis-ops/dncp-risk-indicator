// Endpoints de R063 (contratos sin documento publicado).
import { apiGet } from '../../../lib/apiClient';

export const fetchR063Kpi = params => apiGet('/r063/kpi', params);

export const fetchR063Monthly = params => apiGet('/r063/monthly', params);

export const fetchR063TopEntities = params => apiGet('/r063/top-entities', params);

export const fetchR063Processes = params => apiGet('/r063/processes', params);
