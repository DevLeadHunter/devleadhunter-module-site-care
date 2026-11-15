import type { ModuleAssistantAnswer } from '~/types/ModuleAssistant'
import type { SiteCareSiteListItem } from './SiteCareSite'

/** An answer of the assistant, whose cards are the sites of « Mes prospects ». */
export type SiteCareAssistantAnswer = ModuleAssistantAnswer<SiteCareSiteListItem>
