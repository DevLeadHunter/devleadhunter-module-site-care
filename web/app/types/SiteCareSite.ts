export type SiteCareIssueKind =
  | 'hack'
  | 'security'
  | 'risk'
  | 'late'
  | 'mail'
  | 'mobile'
  | 'contact'
  | 'dated'
  | 'google'

/** What the tag of a row names: a type of issue, « nothing to report » (`ok`) or « site to look at again » (`review`). */
export type SiteCareLeadKind = SiteCareIssueKind | 'ok' | 'review'

export type SiteCareTone = 'red' | 'amber' | 'green' | 'neutral' | 'ink' | 'violet'

export type SiteCareSiteTab = 'to_write' | 'written' | 'no_email' | 'nothing' | 'review' | 'all'

export type SiteCareSiteStateKey =
  | 'to_write'
  | 'no_email'
  | 'written'
  | 'replied'
  | 'care'
  | 'nothing'
  | 'review'
  | 'do_not_contact'

export type SiteCarePointKey =
  | 'https'
  | 'php'
  | 'cms'
  | 'hacked'
  | 'contact_mail'
  | 'spf'
  | 'dmarc'
  | 'google_phone'
  | 'tel_link'
  | 'year'
  | 'mobile'
  | 'search'

export type SiteCareSiteLead = {
  kind: SiteCareLeadKind
  kind_label: string
  tone: SiteCareTone
  tech: string | null
  sentence: string
}

export type SiteCareSiteState = {
  key: SiteCareSiteStateKey
  label: string
  tone: SiteCareTone
}

export type SiteCareSiteListItem = {
  id: number
  business_name: string
  trade_label: string
  city: string | null
  country: string
  domain: string
  website: string
  email: string | null
  tab: SiteCareSiteTab
  state: SiteCareSiteState
  lead: SiteCareSiteLead
  also: string | null
  checked_at: string
}

export type SiteCareSitePoint = {
  key: SiteCarePointKey
  kind: SiteCareIssueKind
  kind_label: string
  tech: string | null
  fact: string
}

export type SiteCareOfferLine = {
  label: string
  price_label: string
}

export type SiteCareMessage = {
  subject: string
  paragraphs: string[]
  paragraphs_with_link: string[]
}

export type SiteCareSentMessage = {
  kind: string
  kind_label: string
  subject: string
  sent_at: string
  status_label: string
}

export type SiteCareSiteCarePlan = {
  id: number
  monthly_price_cents: number
  started_at: string
}

export type SiteCareSiteDetail = SiteCareSiteListItem & {
  phone: string | null
  google_rating: number | null
  google_reviews_count: number | null
  google_maps_url: string | null
  unread_text: string | null
  fixes: SiteCareSitePoint[]
  watches: SiteCareSitePoint[]
  good_line: string | null
  hidden_line: string | null
  offer: SiteCareOfferLine[]
  monthly_label: string
  message: SiteCareMessage | null
  page_url: string | null
  can_send: boolean
  send_refusal: string | null
  sent_messages: SiteCareSentMessage[]
  care_plan: SiteCareSiteCarePlan | null
}

export type SiteCareSiteCounts = {
  total: number
  with_email: number
  to_fix: number
  written: number
}

export type SiteCareTradeFilter = {
  key: string
  label: string
}

/** Answer of `GET /site-care/sites`: the counts cover every site, `matching_count` the tab and filters asked. */
export type SiteCareSiteListResponse = {
  counts: SiteCareSiteCounts
  tab_counts: Record<SiteCareSiteTab, number>
  trades: SiteCareTradeFilter[]
  matching_count: number
  sites: SiteCareSiteListItem[]
}

/** Query of `GET /site-care/sites`; a null filter is left out of the request. */
export type SiteCareSiteListQuery = {
  tab: SiteCareSiteTab
  trade: string | null
  kind: SiteCareIssueKind | null
  q: string | null
  limit: number
  offset: number
}

export type SiteCareIssueKindFilter = {
  kind: SiteCareIssueKind
  label: string
}

export type SiteCareSiteTabLabel = {
  key: SiteCareSiteTab
  label: string
}

export type SiteCareSiteEmailUpdate = {
  email: string
}

export type SiteCareSendPayload = {
  with_page_link: boolean
}
