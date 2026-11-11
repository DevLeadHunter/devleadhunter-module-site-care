import type { SiteCareWatchEvent } from './SiteCareWatch'

/** A titled block of the watch page: the events of today, or the dates coming up. */
export type SiteCareWatchSection = {
  heading: string
  events: SiteCareWatchEvent[]
}
