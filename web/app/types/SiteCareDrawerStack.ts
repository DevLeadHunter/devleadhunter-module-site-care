import type { SiteCareSiteDetail } from './SiteCareSite'

/** The sheet of one prospect; it reads the site itself, so the entry survives a reload with nothing stale in it. */
export type SiteCareProspectDrawerEntry = {
  kind: 'site-care-site'
  siteId: number
}

/** Cross-page notice describing the latest change made to a site from its sheet. */
export type SiteCareSiteChangeNotice =
  | { type: 'updated'; site: SiteCareSiteDetail }
  | { type: 'deleted'; siteId: number }

declare module '~/types/DrawerStack' {
  interface ModuleDrawerEntries {
    'site-care-site': SiteCareProspectDrawerEntry
  }

  interface DrawerStackChangeNotices {
    'site-care-sites': SiteCareSiteChangeNotice
  }
}
