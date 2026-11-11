import type { SiteCareLeadKind, SiteCareTone } from './SiteCareSite'

/** Props of the tag naming a type of issue: its icon comes from `kind`, its word and tone from the API. */
export type SiteCareIssueTagProps = {
  kind: SiteCareLeadKind
  label: string
  tone: SiteCareTone
}
