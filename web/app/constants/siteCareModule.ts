import type { ProductModuleKey } from '~/types/ProductModule'
import type { DashboardModuleDefinition, UiSidebarGroup } from '~/types/UiSidebar'

export const SITE_CARE_MODULE_KEY: ProductModuleKey = 'site-care'

/** The module's own section of the dashboard: reaching one of its pages switches the sidebar to the module. */
export const SITE_CARE_SECTION_PATH: string = '/dashboard/site-care'

export const SITE_CARE_SEARCH_PATH: string = `${SITE_CARE_SECTION_PATH}/search`

export const SITE_CARE_WATCH_PATH: string = `${SITE_CARE_SECTION_PATH}/watch`

export const SITE_CARE_CARE_PLANS_PATH: string = `${SITE_CARE_SECTION_PATH}/care-plans`

export const SITE_CARE_SETTINGS_PATH: string = '/dashboard/settings/site-care'

/**
 * The module's navigation: its prospects are businesses that already have a website, so the list, the search and
 * the watch are its own pages; the dashboard and the email follow-up are the core's.
 */
const SITE_CARE_NAV_GROUPS: UiSidebarGroup[] = [
  {
    heading: 'Pilotage',
    links: [{ to: '/dashboard', label: 'Tableau de bord', icon: 'i-lucide-layout-dashboard' }],
  },
  {
    heading: 'Prospection',
    links: [
      { to: SITE_CARE_SECTION_PATH, label: 'Mes prospects', icon: 'i-lucide-users' },
      { to: SITE_CARE_WATCH_PATH, label: 'Veille', icon: 'i-lucide-radar' },
      { to: '/dashboard/emails', label: 'Suivi des emails', icon: 'i-lucide-send' },
    ],
  },
  {
    heading: 'Clients',
    links: [{ to: SITE_CARE_CARE_PLANS_PATH, label: 'Suivis', icon: 'i-lucide-repeat' }],
  },
]

/** Site care in the module switcher, with the label the core shows for its activity-log entries. */
export const SITE_CARE_DASHBOARD_MODULE: DashboardModuleDefinition = {
  key: SITE_CARE_MODULE_KEY,
  label: 'Entretien de sites',
  icon: 'i-lucide-shield-check',
  home: SITE_CARE_SECTION_PATH,
  primaryCta: { label: 'Trouver des prospects', to: SITE_CARE_SEARCH_PATH, icon: 'i-lucide-search' },
  navGroups: SITE_CARE_NAV_GROUPS,
  activityCategoryLabels: { 'site-care': 'Entretien de sites' },
}
