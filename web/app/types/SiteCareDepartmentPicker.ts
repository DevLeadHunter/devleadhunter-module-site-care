import type { SiteCareSearchLabelledChoice } from './SiteCareSearch'

/** `departments` are the choices offered; `maximumCount` caps how many can be picked. */
export type SiteCareDepartmentPickerProps = {
  departments: SiteCareSearchLabelledChoice[]
  maximumCount: number
}
