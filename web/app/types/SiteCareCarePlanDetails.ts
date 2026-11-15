export type SiteCareCarePlanDetailsProps = {
  carePlanSummary: string | null
  isFormOpen: boolean
  canStart: boolean
  isStarting: boolean
  isActionPending: boolean
}

export type SiteCareCarePlanDetailsEmits = {
  start: []
}
