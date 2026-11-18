import type { SiteCareTone } from './SiteCareSite'

/** `emptyText` is shown in place of the cards while `count` is zero. */
export type SiteCareBoardColumnProps = {
  title: string
  hint: string
  count: number
  tone: SiteCareTone
  emptyText: string
}
