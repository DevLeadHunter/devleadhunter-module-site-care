export type SiteCarePublicPageTitle = {
  start: string
  mark: string
  end: string
}

export type SiteCarePublicPageFinding = {
  label: string
  lead: string
  rest: string
}

/** `tag_label` is null for a correction that is quoted: the card then shows no tag. */
export type SiteCarePublicPageOffer = {
  label: string
  price_label: string
  note: string
  tag_label: string | null
  reassurances: string[]
}

/** `site_url` and `photo_url` are empty strings when the presenter set none. */
export type SiteCarePublicPagePresenter = {
  name: string
  tagline: string
  site_url: string
  site_label: string
  photo_url: string
}

export type SiteCarePublicPage = {
  business_name: string
  domain: string
  title: SiteCarePublicPageTitle
  intro: string
  seen: SiteCarePublicPageFinding
  changes: string[]
  proof_steps: string[]
  offer: SiteCarePublicPageOffer
  goods: string[]
  other_fixes: string[]
  watches: string[]
  other_points_count: number
  presenter: SiteCarePublicPagePresenter
  reply_mailto: string
  forward_mailto: string
}
