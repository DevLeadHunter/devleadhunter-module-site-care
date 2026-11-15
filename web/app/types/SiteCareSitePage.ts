import type { SiteCareSiteDetail } from './SiteCareSite'

export type SiteCareSiteWritingStep = 'finding' | 'message'

export type SiteCareSiteOutcomeStep = 'sent' | 'removed'

export type SiteCareSitePageStep = SiteCareSiteWritingStep | SiteCareSiteOutcomeStep

export type SiteCareSiteAction =
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
