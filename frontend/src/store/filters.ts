import { create } from 'zustand'

interface FilterState {
  dealType: string
  tiers: string[]
  minScore: number
  county: string
  submarket: string
  signals: string[]
  status: string[]
  // Lease / land / vacancy thresholds
  minLeaseRateNnn: number | null
  minNewBuildRentNnn: number | null
  maxLandPricePerSqft: number | null
  maxVacancyRate: number | null
  marketType: string // 'all' | 'emerging' | 'primary'
  sortBy: string
  sortDir: string
  selectedDealId: number | null

  setDealType: (v: string) => void
  setTiers: (v: string[]) => void
  setMinScore: (v: number) => void
  setCounty: (v: string) => void
  setSubmarket: (v: string) => void
  setSignals: (v: string[]) => void
  setStatus: (v: string[]) => void
  setMinLeaseRateNnn: (v: number | null) => void
  setMinNewBuildRentNnn: (v: number | null) => void
  setMaxLandPricePerSqft: (v: number | null) => void
  setMaxVacancyRate: (v: number | null) => void
  setMarketType: (v: string) => void
  setSortBy: (v: string) => void
  setSortDir: (v: string) => void
  setSelectedDealId: (v: number | null) => void
  getQueryParams: () => Record<string, string>
  getListingQueryParams: () => Record<string, string>
  getNationalQueryParams: () => Record<string, string>
  reset: () => void
}

const DEFAULTS = {
  dealType: 'all',
  tiers: ['A', 'B', 'C'],
  minScore: 40,
  county: 'all',
  submarket: '',
  signals: [],
  status: ['new', 'researching', 'underwriting', 'active'],
  minLeaseRateNnn: null as number | null,
  minNewBuildRentNnn: null as number | null,
  maxLandPricePerSqft: null as number | null,
  maxVacancyRate: null as number | null,
  marketType: 'all',
  sortBy: 'score',
  sortDir: 'desc',
  selectedDealId: null as number | null,
}

export const useFilterStore = create<FilterState>((set, get) => ({
  ...DEFAULTS,

  setDealType: (v) => set({ dealType: v }),
  setTiers: (v) => set({ tiers: v }),
  setMinScore: (v) => set({ minScore: v }),
  setCounty: (v) => set({ county: v }),
  setSubmarket: (v) => set({ submarket: v }),
  setSignals: (v) => set({ signals: v }),
  setStatus: (v) => set({ status: v }),
  setMinLeaseRateNnn: (v) => set({ minLeaseRateNnn: v }),
  setMinNewBuildRentNnn: (v) => set({ minNewBuildRentNnn: v }),
  setMaxLandPricePerSqft: (v) => set({ maxLandPricePerSqft: v }),
  setMaxVacancyRate: (v) => set({ maxVacancyRate: v }),
  setMarketType: (v) => set({ marketType: v }),
  setSortBy: (v) => set({ sortBy: v }),
  setSortDir: (v) => set({ sortDir: v }),
  setSelectedDealId: (v) => set({ selectedDealId: v }),

  getQueryParams: () => {
    const s = get()
    const params: Record<string, string> = {
      deal_type: s.dealType,
      min_score: String(s.minScore),
      sort_by: s.sortBy,
      sort_dir: s.sortDir,
    }
    if (s.tiers.length) params.tier = s.tiers.join(',')
    if (s.county !== 'all') params.county = s.county
    if (s.submarket) params.submarket = s.submarket
    if (s.signals.length) params.signals = s.signals.join(',')
    if (s.status.length) params.status = s.status.join(',')
    if (s.maxLandPricePerSqft != null) params.max_land_price_per_sqft = String(s.maxLandPricePerSqft)
    return params
  },

  getListingQueryParams: () => {
    const s = get()
    const params: Record<string, string> = {}
    if (s.minLeaseRateNnn != null) params.min_lease_rate_nnn = String(s.minLeaseRateNnn)
    if (s.minNewBuildRentNnn != null) params.min_new_build_rent_nnn = String(s.minNewBuildRentNnn)
    if (s.maxLandPricePerSqft != null) params.max_land_price_per_sqft = String(s.maxLandPricePerSqft)
    return params
  },

  getNationalQueryParams: () => {
    const s = get()
    const params: Record<string, string> = {}
    if (s.maxVacancyRate != null) params.max_vacancy_rate = String(s.maxVacancyRate)
    if (s.maxLandPricePerSqft != null) params.max_land_price_per_sqft = String(s.maxLandPricePerSqft)
    if (s.marketType !== 'all') params.market_type = s.marketType
    return params
  },

  reset: () => set({ ...DEFAULTS }),
}))
