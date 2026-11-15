export type SiteCareProspectEmailProps = {
  email: string | null
  emailSourceLabel: string | null
  emailSearchResult: string | null
  isFormOpen: boolean
  canSave: boolean
  isSaving: boolean
  isActionPending: boolean
}

export type SiteCareProspectEmailEmits = {
  'open-form': []
  save: []
}
