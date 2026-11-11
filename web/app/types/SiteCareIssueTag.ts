import type { SiteCareLeadKind, SiteCareTone } from './SiteCareSite'

/** `label` and `tone` are shown as the API sends them; only the icon is picked here, from `kind`. */
export type SiteCareIssueTagProps = {
  kind: SiteCareLeadKind
  label: string
  tone: SiteCareTone
}
