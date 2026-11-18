import type { SiteCareLeadKind, SiteCareSiteState, SiteCareTone } from './SiteCareSite'

export type SiteCareWatchSiteChange = {
  key: string
  site_id: number
  kind: SiteCareLeadKind
  kind_label: string
  tone: SiteCareTone
  tech: string | null
  sentence: string
  business_name: string
  trade_label: string
  city: string | null
  seen_label: string
  state: SiteCareSiteState
}

/** One date after which some sites will have a problem; `site_id` is set when it concerns a single site. */
export type SiteCareWatchDate = {
  key: string
  kind: SiteCareLeadKind
  kind_label: string
  tone: SiteCareTone
  title: string
  detail: string
  countdown_label: string
  sites_label: string
  action_label: string
  site_id: number | null
}

/** Answer of `GET /site-care/watch`; `summary_line` is null while the owner follows no site. */
export type SiteCareWatchResponse = {
  summary_line: string | null
  new_issues: SiteCareWatchSiteChange[]
  upcoming_dates: SiteCareWatchDate[]
  gone_sites: SiteCareWatchSiteChange[]
}
