/** What can be done on a follow-up from its row: send the report of the month, or stop the follow-up. */
export type SiteCareCarePlanAction = 'send-report' | 'stop'

/** The action running on a follow-up; the other buttons wait meanwhile. */
export type SiteCareCarePlanPendingAction = {
  carePlanId: number
  action: SiteCareCarePlanAction
}

/** Why an action on a follow-up failed, written under the row it belongs to. */
export type SiteCareCarePlanActionFailure = {
  carePlanId: number
  message: string
}
