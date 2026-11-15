import type { SiteCareCheckedPoint, SiteCarePriceKey, SiteCareWritingTrigger } from './SiteCareSettings'

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
  presenterRole: string
  presenterTagline: string
}

export type SiteCareCheckedPointFamily = {
  label: string
  points: SiteCareCheckedPoint[]
}

export type SiteCareSettingsSection = 'prices' | 'trigger' | 'points'

export type SiteCareSettingsSectionTab = {
  key: SiteCareSettingsSection
  label: string
  title: string
  infoAccessibleLabel: string
  infoText: string
}

export type SiteCareWritingTriggerOption = {
  value: SiteCareWritingTrigger
  label: string
  description: string
}
