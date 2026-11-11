import type {
  SiteCareCarePlan,
  SiteCareCarePlanCreatePayload,
  SiteCareCarePlanListResponse,
} from '../types/SiteCareCarePlan'
import type { SiteCareSearch, SiteCareSearchCreatePayload, SiteCareSearchOptions } from '../types/SiteCareSearch'
import type { SiteCareSettings } from '../types/SiteCareSettings'
import type {
  SiteCareSendPayload,
  SiteCareSiteDetail,
  SiteCareSiteEmailUpdate,
  SiteCareSiteListQuery,
  SiteCareSiteListResponse,
} from '../types/SiteCareSite'
import type { SiteCareWatchResponse } from '../types/SiteCareWatch'
import { ApiClient } from '~/services/api'

const SITE_CARE_API_BASE: string = '/api/v1/site-care'

const API_CLIENT_FALLBACK_PREFIX: string = 'API request failed'

/** HTTP client of the site care module: the prospects' sites, the searches, the watch, the follow-ups, the settings. */
export class SiteCareService {
  /**
   * List the sites of one tab of « Mes prospects », with the counts of every tab.
   * @param query - The tab, the filters and the window of rows asked.
   * @returns The counts, the trades present and the rows.
   */
  static listSites(query: SiteCareSiteListQuery): Promise<SiteCareSiteListResponse> {
    return ApiClient.get<SiteCareSiteListResponse>(`${SITE_CARE_API_BASE}/sites`, { params: query })
  }

  /**
   * Fetch the sheet of one prospect.
   * @param siteId - The site to fetch.
   * @returns What was seen on the site, the offer and the message.
   */
  static getSite(siteId: number): Promise<SiteCareSiteDetail> {
    return ApiClient.get<SiteCareSiteDetail>(`${SITE_CARE_API_BASE}/sites/${siteId}`)
  }

  /**
   * Type or correct the email address of a prospect by hand.
   * @param siteId - The site to update.
   * @param update - The address.
   * @returns The updated sheet.
   */
  static updateSiteEmail(siteId: number, update: SiteCareSiteEmailUpdate): Promise<SiteCareSiteDetail> {
    return ApiClient.patch<SiteCareSiteDetail>(`${SITE_CARE_API_BASE}/sites/${siteId}`, update)
  }

  /**
   * Look for the email address of a prospect on its own website.
   * @param siteId - The site to read.
   * @returns The sheet, its `email` filled when an address was found.
   */
  static findSiteEmail(siteId: number): Promise<SiteCareSiteDetail> {
    return ApiClient.post<SiteCareSiteDetail>(`${SITE_CARE_API_BASE}/sites/${siteId}/find-email`, {})
  }

  /**
   * Look at a site again, from the outside.
   * @param siteId - The site to check.
   * @returns The sheet after the new check.
   */
  static recheckSite(siteId: number): Promise<SiteCareSiteDetail> {
    return ApiClient.post<SiteCareSiteDetail>(`${SITE_CARE_API_BASE}/sites/${siteId}/recheck`, {})
  }

  /**
   * Send the message of a sheet to the prospect: an email really leaves.
   * @param siteId - The site whose owner is written to.
   * @param payload - Whether the message carries the link of the page prepared for the prospect.
   * @returns The sheet once the message is sent.
   * @throws Error carrying the reason, in plain words, when the API refuses the send (409).
   */
  static sendMessage(siteId: number, payload: SiteCareSendPayload): Promise<SiteCareSiteDetail> {
    return ApiClient.post<SiteCareSiteDetail>(`${SITE_CARE_API_BASE}/sites/${siteId}/send`, payload)
  }

  /**
   * Take a site out of « Mes prospects ».
   * @param siteId - The site to remove.
   * @returns A promise resolved once the site left the list.
   */
  static async removeSite(siteId: number): Promise<void> {
    await ApiClient.delete(`${SITE_CARE_API_BASE}/sites/${siteId}`)
  }

  /**
   * Read what a search can target: the countries and the trades, each with how many businesses are available.
   * @returns The countries and the trades.
   */
  static getSearchOptions(): Promise<SiteCareSearchOptions> {
    return ApiClient.get<SiteCareSearchOptions>(`${SITE_CARE_API_BASE}/search-options`)
  }

  /**
   * Launch a search.
   * @param payload - The trades, the country, the cities and how many prospects are wanted.
   * @returns The search, as it starts.
   * @throws Error carrying the reason when a search is already running (409).
   */
  static startSearch(payload: SiteCareSearchCreatePayload): Promise<SiteCareSearch> {
    return ApiClient.post<SiteCareSearch>(`${SITE_CARE_API_BASE}/searches`, payload)
  }

  /**
   * Read the search under way, else the last one.
   * @returns The search, or null when none was ever launched.
   */
  static async getCurrentSearch(): Promise<SiteCareSearch | null> {
    const search: SiteCareSearch | null | undefined = await ApiClient.get(`${SITE_CARE_API_BASE}/searches/current`)
    return search ?? null
  }

  /**
   * Read the watch: what changed today on the prospects' sites and the dates coming up.
   * @returns The events of today and the deadlines.
   */
  static getWatch(): Promise<SiteCareWatchResponse> {
    return ApiClient.get<SiteCareWatchResponse>(`${SITE_CARE_API_BASE}/watch`)
  }

  /**
   * List the clients in monthly follow-up.
   * @returns The three figures and the follow-ups.
   */
  static listCarePlans(): Promise<SiteCareCarePlanListResponse> {
    return ApiClient.get<SiteCareCarePlanListResponse>(`${SITE_CARE_API_BASE}/care-plans`)
  }

  /**
   * Put a prospect in monthly follow-up.
   * @param siteId - The site to follow.
   * @param payload - The monthly price agreed.
   * @returns The sheet, now carrying its follow-up.
   */
  static startCarePlan(siteId: number, payload: SiteCareCarePlanCreatePayload): Promise<SiteCareSiteDetail> {
    return ApiClient.post<SiteCareSiteDetail>(`${SITE_CARE_API_BASE}/sites/${siteId}/care-plan`, payload)
  }

  /**
   * Stop a monthly follow-up.
   * @param carePlanId - The follow-up to stop.
   * @returns A promise resolved once it is stopped.
   */
  static async stopCarePlan(carePlanId: number): Promise<void> {
    await ApiClient.delete(`${SITE_CARE_API_BASE}/care-plans/${carePlanId}`)
  }

  /**
   * Send the report of the month to a client in follow-up: an email really leaves.
   * @param carePlanId - The follow-up whose report to send.
   * @returns The follow-up once the report is sent.
   * @throws Error carrying the reason when the API refuses the send (409).
   */
  static sendCarePlanReport(carePlanId: number): Promise<SiteCareCarePlan> {
    return ApiClient.post<SiteCareCarePlan>(`${SITE_CARE_API_BASE}/care-plans/${carePlanId}/report`, {})
  }

  /**
   * Read the module's settings.
   * @returns The prices, when to write, the points looked at and who writes.
   */
  static getSettings(): Promise<SiteCareSettings> {
    return ApiClient.get<SiteCareSettings>(`${SITE_CARE_API_BASE}/settings`)
  }

  /**
   * Save the module's settings.
   * @param settings - The settings, in the shape they were read.
   * @returns The settings as saved.
   */
  static saveSettings(settings: SiteCareSettings): Promise<SiteCareSettings> {
    return ApiClient.put<SiteCareSettings>(`${SITE_CARE_API_BASE}/settings`, settings)
  }

  /**
   * Pick the sentence to show after a failed call: the API's own reason (a 409 `detail`) when it gave one.
   * @param error - What the call threw.
   * @param fallback - The sentence to show when the API gave none.
   * @returns The API's own sentence, else the fallback.
   */
  static failureMessage(error: unknown, fallback: string): string {
    if (!(error instanceof Error) || error instanceof TypeError) {
      return fallback
    }
    const hasReadableSentence: boolean =
      error.message.trim() !== '' &&
      !error.message.startsWith(API_CLIENT_FALLBACK_PREFIX) &&
      !error.message.includes('[object Object]')
    return hasReadableSentence ? error.message : fallback
  }
}
