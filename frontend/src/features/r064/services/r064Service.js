// Endpoints de R064 (contratos modificados).
import { apiGet } from '../../../lib/apiClient';

export const fetchR064Kpi = params => apiGet('/r064/kpi', params);

export const fetchR064Monthly = params => apiGet('/r064/monthly', params);

export const fetchR064TopEntities = params => apiGet('/r064/top-entities', params);

export const fetchR064Processes = params => apiGet('/r064/processes', params);
