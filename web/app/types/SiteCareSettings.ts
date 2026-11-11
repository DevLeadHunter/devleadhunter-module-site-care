import type { SiteCarePointKey } from './SiteCareSite'

export type SiteCarePriceKey = 'cleanup' | 'php' | 'cms' | 'https' | 'mail' | 'search' | 'touchup' | 'mobile'

/** The price of one correction; `price_cents` is null for a correction quoted case by case. */
export type SiteCarePrice = {
  key: SiteCarePriceKey
  label: string
  price_cents: number | null
}

/** When a site deserves a message: as soon as a point is to fix, or also when three points are to watch. */
export type SiteCareWritingTrigger = 'fix' | 'watch'

export type SiteCareCheckedPoint = {
  key: SiteCarePointKey
  family_label: string
  label: string
  is_enabled: boolean
}

/** Who writes to the prospects; `role` follows « Je suis {name}, » in the message and on the page. */
export type SiteCarePresenter = {
  name: string
  role: string
  tagline: string
  site_url: string
  photo_url: string
}

/** Body and answer of `GET` and `PUT /site-care/settings`; `sender_email` is read-only. */
export type SiteCareSettings = {
  prices: SiteCarePrice[]
  monthly_price_cents: number
  trigger: SiteCareWritingTrigger
  points: SiteCareCheckedPoint[]
  presenter: SiteCarePresenter
  sender_email: string | null
}
