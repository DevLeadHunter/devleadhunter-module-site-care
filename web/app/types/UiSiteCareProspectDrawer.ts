import type { SiteCareSiteChangeNotice } from './SiteCareDrawerStack'
import type { SiteCareSiteDetail, SiteCareSitePoint, SiteCareTone } from './SiteCareSite'

export type UiSiteCareProspectDrawerProps = {
  open: boolean
  siteId: number | null
  showBack: boolean
}

export type UiSiteCareProspectDrawerEmits = {
  close: []
  back: []
  updated: [notice: SiteCareSiteChangeNotice]
}

export type SiteCareProspectSheetAction =
  | 'send'
  | 'find-email'
  | 'save-email'
  | 'recheck'
  | 'start-care-plan'
  | 'stop-care-plan'
  | 'remove'

export type SiteCareSiteActionOutcome = {
  updatedSite: SiteCareSiteDetail | null
  failureMessage: string | null
}

export type SiteCareFindingGroup = {
  title: string
  tone: SiteCareTone
  points: SiteCareSitePoint[]
}
