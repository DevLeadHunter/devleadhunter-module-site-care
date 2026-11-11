import type { RouteLocationNormalized } from 'vue-router'
import { useModuleStore } from '~/stores/moduleStore'
import { SITE_CARE_MODULE_KEY, SITE_CARE_SECTION_PATH } from '../constants/siteCareModule'

/** Sends to the dashboard while the module is off; a page of its own section also switches the sidebar to it. */
export default defineNuxtRouteMiddleware(async (to: RouteLocationNormalized) => {
  const moduleStore: ReturnType<typeof useModuleStore> = useModuleStore()
  if (import.meta.client && !(await moduleStore.isModuleEnabled(SITE_CARE_MODULE_KEY))) {
    return navigateTo('/dashboard')
  }

  const isModuleSectionPage: boolean =
    to.path === SITE_CARE_SECTION_PATH || to.path.startsWith(`${SITE_CARE_SECTION_PATH}/`)
  if (isModuleSectionPage) {
    moduleStore.setModule(SITE_CARE_MODULE_KEY)
  }
})
