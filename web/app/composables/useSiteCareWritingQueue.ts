import type { Ref } from 'vue'
import type { SiteCareSiteListItem, SiteCareSiteListResponse } from '../types/SiteCareSite'
import { SITE_CARE_SITE_LIST_MAXIMUM_LIMIT } from '../constants/siteCareModule'
import { SiteCareService } from '../services/siteCareService'

const WRITING_QUEUE_STATE_KEY: string = 'site-care-writing-queue'

export type UseSiteCareWritingQueueReturn = {
  queuedSiteIds: Ref<number[]>
  loadQueue: () => Promise<number[]>
  ensureQueue: () => Promise<void>
}

/**
 * The sites « Traiter les sites » walks through, read when the walk starts and kept from one site's page to the next.
 * @returns The queued sites, and the functions that read them.
 */
export function useSiteCareWritingQueue(): UseSiteCareWritingQueueReturn {
  const queuedSiteIds: Ref<number[]> = useState(WRITING_QUEUE_STATE_KEY, (): number[] => [])

  /**
   * Read the sites of « À écrire » and queue them, in their order.
   * @returns The identifiers queued.
   */
  async function loadQueue(): Promise<number[]> {
    const response: SiteCareSiteListResponse = await SiteCareService.listSites({
      tab: 'to_write',
      trade: null,
      kind: null,
      q: null,
      watch_date: null,
      limit: SITE_CARE_SITE_LIST_MAXIMUM_LIMIT,
      offset: 0,
    })
    queuedSiteIds.value = response.sites.map((site: SiteCareSiteListItem): number => site.id)
    return queuedSiteIds.value
  }

  /**
   * Read the queue only when none is kept, as on a site's page opened straight from its address.
   * @returns A promise resolved once the queue is kept.
   */
  async function ensureQueue(): Promise<void> {
    if (queuedSiteIds.value.length === 0) {
      await loadQueue()
    }
  }

  return { queuedSiteIds, loadQueue, ensureQueue }
}
