import type { ProductModuleKey } from '~/types/ProductModule'
import type { DashboardModuleDefinition, UiSidebarGroup } from '~/types/UiSidebar'
import { MODULE_ASSISTANT_ICON, MODULE_ASSISTANT_LABEL } from '~/constants/moduleAssistant'

export const SITE_CARE_MODULE_KEY: ProductModuleKey = 'site-care'

export const SITE_CARE_SECTION_PATH: string = '/dashboard/site-care'

export const SITE_CARE_SITES_PATH: string = `${SITE_CARE_SECTION_PATH}/sites`

export const SITE_CARE_SEARCH_PATH: string = `${SITE_CARE_SECTION_PATH}/search`

export const SITE_CARE_WATCH_PATH: string = `${SITE_CARE_SECTION_PATH}/watch`

export const SITE_CARE_CARE_PLANS_PATH: string = `${SITE_CARE_SECTION_PATH}/care-plans`

export const SITE_CARE_ASSISTANT_PATH: string = `${SITE_CARE_SECTION_PATH}/assistant`

export const SITE_CARE_SETTINGS_PATH: string = '/dashboard/settings/site-care'

export const SITE_CARE_WRITING_QUEUE_QUERY: Record<string, string> = { queue: '1' }

/** The address query of « Mes prospects » that narrows the list to the sites one date of the watch concerns. */
export const SITE_CARE_WATCH_DATE_QUERY_NAME: string = 'date'

export const SITE_CARE_SITE_LIST_MAXIMUM_LIMIT: number = 500

const SITE_CARE_NAV_GROUPS: UiSidebarGroup[] = [
  {
    heading: 'Pilotage',
    links: [{ to: '/dashboard', label: 'Tableau de bord', icon: 'i-lucide-layout-dashboard' }],
  },
  {
    heading: 'Prospection',
    links: [
      { to: SITE_CARE_SECTION_PATH, label: 'Mes prospects', icon: 'i-lucide-users' },
      { to: SITE_CARE_WATCH_PATH, label: 'Veille', icon: 'i-lucide-bell' },
      { to: SITE_CARE_ASSISTANT_PATH, label: MODULE_ASSISTANT_LABEL, icon: MODULE_ASSISTANT_ICON },
      { to: '/dashboard/emails', label: 'Suivi des emails', icon: 'i-lucide-send' },
    ],
  },
  {
    heading: 'Clients',
    links: [{ to: SITE_CARE_CARE_PLANS_PATH, label: 'Clients en suivi', icon: 'i-lucide-repeat' }],
  },
]

export const SITE_CARE_DASHBOARD_MODULE: DashboardModuleDefinition = {
  key: SITE_CARE_MODULE_KEY,
  label: 'Entretien de sites',
  icon: 'i-lucide-shield-check',
  home: SITE_CARE_SECTION_PATH,
  primaryCta: { label: 'Trouver des prospects', to: SITE_CARE_SEARCH_PATH, icon: 'i-lucide-search' },
  tabBarMainAction: { label: MODULE_ASSISTANT_LABEL, to: SITE_CARE_ASSISTANT_PATH, icon: MODULE_ASSISTANT_ICON },
  navGroups: SITE_CARE_NAV_GROUPS,
  activityCategoryLabels: { 'site-care': 'Entretien de sites' },
}
