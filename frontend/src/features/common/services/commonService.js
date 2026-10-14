// Endpoints /common: buyers, years y status.
import { apiGet } from '@/lib/apiClient';

export async function fetchBuyers() {
  const res = await apiGet('/common/buyers');
  return (res.data ?? []).map(b => ({ value: b.buyer_id, label: b.name }));
}

export async function fetchYears() {
  const res = await apiGet('/common/years');
  return res.years ?? [];
}
export async function fetchUpdatedAt() {
  const res = await apiGet('/common/status');
  return res.updated_at ?? null;
}
