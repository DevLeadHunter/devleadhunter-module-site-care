import type { SiteCareTone } from './SiteCareSite'

/** `emptyText` is shown in place of the cards while `cardCount` is zero. */
export type SiteCareBoardColumnProps = {
  title: string
  description: string
  cardCount: number
  tone: SiteCareTone
  emptyText: string
}
