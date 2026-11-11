import type { SiteCareSiteChangeNotice } from './SiteCareDrawerStack'
import type { SiteCareSiteDetail, SiteCareSitePoint, SiteCareTone } from './SiteCareSite'

/** Props of the sheet of one prospect: what was seen on its site, the message, and the actions on it. */
export type UiSiteCareProspectDrawerProps = {
  open: boolean
  siteId: number | null
  showBack: boolean
}

/** Events the sheet emits; `updated` carries what changed, for the list behind it. */
export type UiSiteCareProspectDrawerEmits = {
  close: []
  back: []
  updated: [notice: SiteCareSiteChangeNotice]
}

/** The action the sheet is waiting on; one at a time, the others stay disabled meanwhile. */
export type SiteCareProspectSheetAction =
  | 'send'
  | 'find-email'
  | 'save-email'
  | 'recheck'
  | 'start-care-plan'
  | 'stop-care-plan'
  | 'remove'

/** How an action of the sheet ended: the site as the API returned it, or the sentence saying why it failed. */
export type SiteCareSiteActionOutcome = {
  updatedSite: SiteCareSiteDetail | null
  failureMessage: string | null
}

/** A block of points of the sheet: the ones to fix, or the ones to watch. */
export type SiteCareFindingGroup = {
  title: string
  tone: SiteCareTone
  points: SiteCareSitePoint[]
}
