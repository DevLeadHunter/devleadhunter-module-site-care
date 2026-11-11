import type { SiteCarePublicPage } from './SiteCarePublicPage'

export type SiteCareProspectPageProps = {
  page: SiteCarePublicPage
}

export type SiteCareProspectPageEmits = {
  'reply-click': []
  'forward-click': []
}

export type SiteCareIntroAroundDomain = {
  beforeDomain: string
  domain: string | null
  afterDomain: string
}
