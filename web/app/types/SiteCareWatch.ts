import type { SiteCareIssueKind, SiteCareLeadKind, SiteCareSiteTab, SiteCareTone } from './SiteCareSite'

/** Where an event leads in « Mes prospects »: the sheet of one site, else the list on a tab and a type of issue. */
export type SiteCareWatchTarget = {
  site_id: number | null
  tab: SiteCareSiteTab | null
  kind: SiteCareIssueKind | null
}

/** One reason to write today (`WatchEvent` of the API). */
export type SiteCareWatchEvent = {
  key: string
  kind: SiteCareLeadKind
  tone: SiteCareTone
  title: string
  detail: string
  when_label: string
  site_count: number
  action_label: string
  target: SiteCareWatchTarget
}

/** Answer of `GET /site-care/watch`. */
export type SiteCareWatchResponse = {
  today: SiteCareWatchEvent[]
  deadlines: SiteCareWatchEvent[]
}
