export type SiteCareSearchStep = 'source' | 'zone' | 'keep'

/** A trade chip of the search: its label and how many businesses are available in the country chosen. */
export type SiteCareSearchTradeChoice = {
  key: string
  label: string
  availableCount: number
  isSelected: boolean
}

export type SiteCareSearchRecapRow = {
  label: string
  value: string
}
