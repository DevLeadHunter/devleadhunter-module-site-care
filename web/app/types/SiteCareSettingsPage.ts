import type {
  SiteCareCheckedPoint,
  SiteCarePresenter,
  SiteCarePriceKey,
  SiteCareWritingTrigger,
} from './SiteCareSettings'

export type SiteCareFixedPriceField = {
  key: SiteCarePriceKey
  label: string
  euros: number
}

/** The settings as the page edits them: prices in euros, the corrections quoted case by case left out. */
export type SiteCareSettingsForm = {
  fixedPrices: SiteCareFixedPriceField[]
  monthlyPriceEuros: number
  trigger: SiteCareWritingTrigger
  points: SiteCareCheckedPoint[]
  presenter: SiteCarePresenter
}

export type SiteCareCheckedPointFamily = {
  label: string
  points: SiteCareCheckedPoint[]
}
