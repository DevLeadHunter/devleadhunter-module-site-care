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

export type SiteCareSearchSource = 'base' | 'open_map'

export type SiteCareSearchKeepRule = 'all' | 'issues' | 'security'

/** A choice of a search; `hint` explains it on a line when it has one. */
export type SiteCareSearchLabelledChoice<TKey extends string = string> = {
  key: TKey
  label: string
  hint: string | null
}

/** What a search on OpenStreetMap can ask for; `credit` is the line the licence of the data asks to show. */
export type SiteCareSearchOpenMapOptions = {
  departments: SiteCareSearchLabelledChoice[]
  families: SiteCareSearchLabelledChoice[]
  keep_rules: SiteCareSearchLabelledChoice<SiteCareSearchKeepRule>[]
  max_count: number
  max_departments: number
  credit: string
}

export type SiteCareSearchOptions = {
  sources: SiteCareSearchLabelledChoice<SiteCareSearchSource>[]
  countries: SiteCareSearchCountryOption[]
  trades: SiteCareSearchTradeOption[]
  max_count: number
  open_map: SiteCareSearchOpenMapOptions
}

export type SiteCareSearchStatus = 'pending' | 'running' | 'completed' | 'failed'

/** A search of the module (`Search` of the API); `note` says why it brought fewer businesses, was stopped or failed. */
export type SiteCareSearch = {
  id: number
  status: SiteCareSearchStatus
  status_label: string
  source: SiteCareSearchSource
  source_label: string
  keep_rule_label: string
  requested_count: number
  checked_count: number
  imported_count: number
  progress_label: string
  trades_label: string
  zone_label: string
  note: string | null
  created_at: string
  completed_at: string | null
}

/** A search in the user's base: no trade means every trade, no city every city of the country. */
export type SiteCareSearchOwnBasePayload = {
  source: 'base'
  trades: string[]
  country: string
  cities: string[]
  count: number
}

/** A search on OpenStreetMap: no family means every family; `count` is how many sites are kept at most. */
export type SiteCareSearchOpenMapPayload = {
  source: 'open_map'
  departments: string[]
  families: string[]
  keep_rule: SiteCareSearchKeepRule
  count: number
}

/** Body of `POST /site-care/searches`. */
export type SiteCareSearchCreatePayload = SiteCareSearchOwnBasePayload | SiteCareSearchOpenMapPayload
