/** A trade chip of the search: its label and how many businesses are available in the country chosen. */
export type SiteCareSearchTradeChoice = {
  key: string
  label: string
  availableCount: number
  isSelected: boolean
}

/** A way to reach the prospects, as the search shows it; the ones not available yet are marked « Bientôt ». */
export type SiteCareContactChannelChoice = {
  key: string
  label: string
  description: string
  icon: string
  isSelected: boolean
  isAvailable: boolean
}

export type SiteCareSearchRecapRow = {
  label: string
  value: string
}
