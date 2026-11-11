export type SiteCareSearchCountryOption = {
  code: string
  label: string
  available_count: number
}

export type SiteCareSearchTradeOption = {
  key: string
  label: string
  available_by_country: Record<string, number>
}

export type SiteCareSearchOptions = {
  countries: SiteCareSearchCountryOption[]
  trades: SiteCareSearchTradeOption[]
}

export type SiteCareSearchStatus = 'pending' | 'running' | 'completed' | 'failed'

/** A search of the module (`Search` of the API); `note` says why it brought fewer businesses, or why it failed. */
export type SiteCareSearch = {
  id: number
  status: SiteCareSearchStatus
  status_label: string
  requested_count: number
  checked_count: number
  imported_count: number
  trades_label: string
  zone_label: string
  note: string | null
  created_at: string
  completed_at: string | null
}

/** Body of `POST /site-care/searches`: no trade means every trade, no city every city of the country. */
export type SiteCareSearchCreatePayload = {
  trades: string[]
  country: string
  cities: string[]
  count: number
}
