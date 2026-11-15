import type { SiteCareMessage } from './SiteCareSite'

export type SiteCareMessageCardProps = {
  businessName: string
  email: string | null
  message: SiteCareMessage
  hasPreparedPage: boolean
}
