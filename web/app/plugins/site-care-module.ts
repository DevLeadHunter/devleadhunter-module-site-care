import { DashboardModuleRegistry } from '~/utils/dashboardModuleRegistry'
import { SettingsNavRegistry } from '~/utils/settingsNavRegistry'
import { SITE_CARE_DASHBOARD_MODULE, SITE_CARE_MODULE_KEY, SITE_CARE_SETTINGS_PATH } from '../constants/siteCareModule'

/** Plugs site care into the core's registries: the module switcher and the settings menu. */
export default defineNuxtPlugin((): void => {
  DashboardModuleRegistry.register(SITE_CARE_DASHBOARD_MODULE)

  SettingsNavRegistry.register({
    moduleKey: SITE_CARE_MODULE_KEY,
    groupHeading: 'Compte',
    entry: { to: SITE_CARE_SETTINGS_PATH, label: 'Entretien de sites', icon: 'i-lucide-shield-check' },
  })
})
