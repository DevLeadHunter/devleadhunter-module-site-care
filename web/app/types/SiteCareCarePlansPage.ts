export type SiteCareCarePlanAction = 'send-report' | 'stop'

export type SiteCareCarePlanPendingAction = {
  carePlanId: number
  action: SiteCareCarePlanAction
}

export type SiteCareCarePlanActionFailure = {
  carePlanId: number
  message: string
}
