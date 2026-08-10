import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'X-API-Key': import.meta.env.VITE_API_KEY || 'dev-key',
  },
})

// --- Deals ---
export const fetchDeals = (params: Record<string, any>) =>
  api.get('/deals', { params }).then((r) => r.data)

export const fetchDeal = (id: number) =>
  api.get(`/deals/${id}`).then((r) => r.data)

export const updateDeal = (id: number, body: Record<string, any>) =>
  api.patch(`/deals/${id}`, body).then((r) => r.data)

export const addDealNote = (id: number, body: { note: string; author?: string }) =>
  api.post(`/deals/${id}/notes`, body).then((r) => r.data)

// --- Parcels ---
export const fetchParcels = (params: Record<string, any>) =>
  api.get('/parcels', { params }).then((r) => r.data)

export const fetchParcel = (id: number) =>
  api.get(`/parcels/${id}`).then((r) => r.data)

export const fetchParcelComps = (id: number, params?: Record<string, any>) =>
  api.get(`/parcels/${id}/comps`, { params }).then((r) => r.data)

// --- Market ---
export const fetchMarketOverview = () =>
  api.get('/market/overview').then((r) => r.data)

export const fetchSubmarkets = () =>
  api.get('/market/submarkets').then((r) => r.data)

export const fetchSubmarket = (name: string) =>
  api.get(`/market/submarkets/${encodeURIComponent(name)}`).then((r) => r.data)

export const fetchListings = (params?: Record<string, any>) =>
  api.get('/market/listings', { params }).then((r) => r.data)

// --- Pipeline ---
export const fetchPipeline = () =>
  api.get('/pipeline').then((r) => r.data)

// --- Agents ---
export const fetchAgentStatus = () =>
  api.get('/agents/status').then((r) => r.data)

export const triggerAgent = (name: string) =>
  api.post(`/agents/${name}/trigger`).then((r) => r.data)

// --- Pro Forma ---
export const calculateProforma = (body: Record<string, any>) =>
  api.post('/proforma', body).then((r) => r.data)

// --- Alerts (legacy in-memory) ---
export const fetchAlerts = () =>
  api.get('/alerts').then((r) => r.data)

export const createAlert = (body: Record<string, any>) =>
  api.post('/alerts', body).then((r) => r.data)

export const deleteAlert = (id: number) =>
  api.delete(`/alerts/${id}`).then((r) => r.data)

// --- Subscribers (DB-backed, drives the 2x/week digest) ---
export interface SubscriberFilters {
  min_lease_rate_nnn?: number | null
  min_new_build_rent_nnn?: number | null
  max_land_price_per_sqft?: number | null
  max_vacancy_rate?: number | null
  market_type?: string | null
  min_deal_score?: number | null
  county?: string | null
}

export interface Subscriber {
  id: number
  name: string
  email?: string
  phone?: string
  filters: SubscriberFilters
  delivery: string
  frequency: string
  active: boolean
  created_at?: string
  updated_at?: string
}

export const fetchSubscribers = (params?: Record<string, any>) =>
  api.get('/subscribers', { params }).then((r) => r.data as { subscribers: Subscriber[] })

export const createSubscriber = (body: Partial<Subscriber>) =>
  api.post('/subscribers', body).then((r) => r.data as Subscriber)

export const updateSubscriber = (id: number, body: Partial<Subscriber>) =>
  api.patch(`/subscribers/${id}`, body).then((r) => r.data as Subscriber)

export const deleteSubscriber = (id: number) =>
  api.delete(`/subscribers/${id}`).then((r) => r.data)

export const previewDigest = (id: number) =>
  api.post(`/subscribers/${id}/preview`).then((r) => r.data)

// --- Digests ---
export const fetchDigests = (params?: Record<string, any>) =>
  api.get('/digests', { params }).then((r) => r.data)

export const fetchDigest = (id: number) =>
  api.get(`/digests/${id}`).then((r) => r.data)

// --- National markets ---
export const fetchNationalMarkets = (params?: Record<string, any>) =>
  api.get('/market/national', { params }).then((r) => r.data)

export default api
