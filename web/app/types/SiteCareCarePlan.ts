export type SiteCareCarePlanReportState = 'due' | 'sent'

export type SiteCareCarePlan = {
  id: number
  site_id: number
  business_name: string
  trade_label: string
  city: string | null
  domain: string
  last_check_summary: string
  last_checked_label: string
  report_state: SiteCareCarePlanReportState
  report_label: string
  report_detail: string
  monthly_label: string
  since_label: string
  can_send_report: boolean
}

export type SiteCareCarePlanStats = {
  client_count: number
  monthly_revenue_label: string
  reports_due_count: number
}

export type SiteCareCarePlanListResponse = {
  stats: SiteCareCarePlanStats
  plans: SiteCareCarePlan[]
}

export type SiteCareCarePlanCreatePayload = {
  monthly_price_cents: number
}
