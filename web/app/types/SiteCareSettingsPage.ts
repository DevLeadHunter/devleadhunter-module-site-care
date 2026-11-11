import type {
  SiteCareCheckedPoint,
  SiteCarePresenter,
  SiteCarePriceKey,
  SiteCareWritingTrigger,
} from './SiteCareSettings'

/** The price of a correction as the form edits it, in euros. */
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

/** The points looked at on a site, under the family the API files them in. */
export type SiteCareCheckedPointFamily = {
  label: string
  points: SiteCareCheckedPoint[]
}
