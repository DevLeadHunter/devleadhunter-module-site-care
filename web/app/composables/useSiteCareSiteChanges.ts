import type { ComputedRef } from 'vue'
import type { DrawerStackEntry } from '~/types/DrawerStack'
import type { SiteCareSiteChangeNotice } from '../types/SiteCareDrawerStack'
import { computed } from 'vue'
import { useDrawerStackStore } from '~/stores/drawerStack'

/** What `useSiteCareSiteChanges` gives: the count and the latest change of the sites, and how to send one. */
export type UseSiteCareSiteChangesReturn = {
  siteChangeCount: ComputedRef<number>
  latestSiteChange: ComputedRef<SiteCareSiteChangeNotice | null>
  notifySiteChanged: (notice: SiteCareSiteChangeNotice) => void
}

/**
 * The changes made to a prospect from its sheet, broadcast through the core drawer stack to the module's pages.
 * @returns The count and latest notice to watch, and the function that broadcasts a change.
 */
export function useSiteCareSiteChanges(): UseSiteCareSiteChangesReturn {
  const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

  /**
   * Tell the pages a site changed; the sheet of a site taken out of the list closes.
   * @param notice - The site as the API returned it, or the identifier of the one removed.
   */
  function notifySiteChanged(notice: SiteCareSiteChangeNotice): void {
    if (notice.type === 'deleted') {
      drawerStack.replaceEntries((entry: DrawerStackEntry): DrawerStackEntry | null =>
        entry.kind === 'site-care-site' && entry.siteId === notice.siteId ? null : entry,
      )
    }
    drawerStack.broadcastChange('site-care-sites', notice)
  }

  return {
    siteChangeCount: computed((): number => drawerStack.changeCountOf('site-care-sites')),
    latestSiteChange: computed((): SiteCareSiteChangeNotice | null => drawerStack.latestChangeOf('site-care-sites')),
    notifySiteChanged,
  }
}
