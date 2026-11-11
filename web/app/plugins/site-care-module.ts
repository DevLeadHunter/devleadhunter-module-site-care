import type { SiteCareProspectDrawerEntry, SiteCareSiteChangeNotice } from '../types/SiteCareDrawerStack'
import { defineAsyncComponent } from 'vue'
import { DashboardModuleRegistry } from '~/utils/dashboardModuleRegistry'
import { DrawerKindRegistry } from '~/utils/drawerKindRegistry'
import { SettingsNavRegistry } from '~/utils/settingsNavRegistry'
import { useSiteCareSiteChanges } from '../composables/useSiteCareSiteChanges'
import { SITE_CARE_DASHBOARD_MODULE, SITE_CARE_MODULE_KEY, SITE_CARE_SETTINGS_PATH } from '../constants/siteCareModule'

/** Plugs site care into the core's registries: the module switcher, the prospect sheet drawer, the settings menu. */
export default defineNuxtPlugin((): void => {
  DashboardModuleRegistry.register(SITE_CARE_DASHBOARD_MODULE)

  DrawerKindRegistry.register({
    kind: 'site-care-site',
    moduleKey: SITE_CARE_MODULE_KEY,
    component: defineAsyncComponent(() => import('../components/ui/SiteCareProspectDrawer.vue')),
    entryProps: (entry: SiteCareProspectDrawerEntry): Record<string, unknown> => ({ siteId: entry.siteId }),
    notifyChange: (notice: SiteCareSiteChangeNotice): void => {
      useSiteCareSiteChanges().notifySiteChanged(notice)
    },
  })

  SettingsNavRegistry.register({
    moduleKey: SITE_CARE_MODULE_KEY,
    groupHeading: 'Compte',
    entry: { to: SITE_CARE_SETTINGS_PATH, label: 'Entretien de sites', icon: 'i-lucide-shield-check' },
  })
})
