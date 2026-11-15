import type { SiteCareSiteDetail } from './SiteCareSite'

export type SiteCareFindingCardProps = {
  site: SiteCareSiteDetail
  isRechecking: boolean
  isActionPending: boolean
}

export type SiteCareFindingCardEmits = {
  recheck: []
}
