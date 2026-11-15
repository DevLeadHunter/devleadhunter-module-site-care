<template>
  <div class="flex min-h-full flex-col gap-7">
    <div class="flex items-center justify-between gap-4">
      <SiteCareBackLink :to="SITE_CARE_SECTION_PATH">Mes prospects</SiteCareBackLink>
      <div v-if="queuePosition !== null" class="flex items-center gap-1">
        <span class="text-sm text-[var(--app-ink-soft)]">Site {{ queuePosition }} sur {{ queuedSiteIds.length }}</span>
        <NuxtLink
          v-if="nextQueuedSiteRoute !== null && isSiteStillToHandle"
          :to="nextQueuedSiteRoute"
          class="inline-flex h-11 w-11 items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
          aria-label="Passer au site suivant sans écrire"
          title="Passer au site suivant sans écrire"
        >
          <UIcon name="i-lucide-chevron-right" class="h-5 w-5" />
        </NuxtLink>
      </div>
    </div>

    <UiLoader v-if="site === null && isLoadingSite" label="Chargement du site…" />

    <UiEmptyState
      v-else-if="site === null"
      title="Ce site n’a pas pu être chargé"
      description="Il a peut-être été retiré de vos prospects. Revenez à la liste, ou réessayez."
    >
      <template #action>
        <button type="button" class="app-btn-secondary" @click="loadSite">
          <UIcon name="i-lucide-refresh-cw" class="h-4 w-4" />
          Réessayer
        </button>
      </template>
    </UiEmptyState>

    <div v-else class="flex flex-wrap items-start gap-7">
      <div class="flex min-w-0 flex-[999_1_30rem] flex-col gap-5">
        <SiteCarePageHeader :title="site.business_name" :description="tradeAndCityLabel" />

        <SiteCareFindingCard
          v-if="step === 'finding'"
          :site="site"
          :is-rechecking="pendingAction === 'recheck'"
          :is-action-pending="pendingAction !== null"
          @recheck="recheckSite"
        />

        <SiteCareMessageCard
          v-else-if="step === 'message' && site.message !== null"
          v-model:has-page-link="hasPageLink"
          :business-name="site.business_name"
          :email="site.email"
          :message="site.message"
          :has-prepared-page="site.page_url !== null"
        />

        <SiteCareOutcomeCard
          v-else-if="step === 'sent'"
          :title="`Message envoyé à ${site.business_name}`"
          description="Il passe dans « Écrits ». Son ouverture et la réponse s’affichent dans « Suivi des emails »."
        />

        <SiteCareOutcomeCard
          v-else-if="step === 'removed'"
          title="Retiré de vos prospects"
          :description="`${site.business_name} sort de la liste. Son site ne sera plus relu.`"
          :has-check-mark="false"
        />
      </div>

      <SiteCareStepActionCard
        class="flex-[1_1_22rem] @4xl:max-w-[26rem]"
        :title="stepTitle"
        :step-count="isWritingFlowShown ? WRITING_STEPS.length : 0"
        :reached-step-count="writingStepNumber"
      >
        <SiteCareOfferList
          v-if="site.offer.length > 0 && step !== 'removed'"
          :offer-lines="site.offer"
          :monthly-label="site.monthly_label"
        />

        <SiteCareProspectEmail
          v-if="step === 'finding' && site.message !== null"
          v-model:email-draft="emailDraft"
          :email="site.email"
          :email-source-label="site.email_source_label"
          :email-search-result="emailSearchResult"
          :is-form-open="isEmailFormOpen"
          :can-save="canSaveEmail"
          :is-saving="pendingAction === 'save-email'"
          :is-action-pending="pendingAction !== null"
          @open-form="openEmailForm"
          @save="saveEmail"
        />

        <p v-if="refusalSentence" class="text-[15px] leading-relaxed text-[var(--app-ink-soft)]">
          {{ refusalSentence }}
        </p>

        <SiteCareSentMessageList
          v-if="site.sent_messages.length > 0 && step !== 'removed'"
          :sent-messages="site.sent_messages"
        />

        <SiteCareCarePlanDetails
          v-if="isCarePlanShown && step !== 'removed'"
          v-model:monthly-euros="carePlanMonthlyEuros"
          :care-plan-summary="carePlanSummary"
          :is-form-open="isCarePlanFormOpen"
          :can-start="canStartCarePlan"
          :is-starting="pendingAction === 'start-care-plan'"
          :is-action-pending="pendingAction !== null"
          @start="startCarePlan"
        />

        <p v-if="actionFailureMessage" class="text-sm leading-relaxed text-[var(--app-red)]" role="alert">
          {{ actionFailureMessage }}
        </p>

        <div class="flex flex-col gap-2.5">
          <template v-if="step === 'finding'">
            <SiteCareButton
              v-if="canWrite"
              size="large"
              class="w-full"
              trailing-icon="i-lucide-arrow-right"
              @click="goToStep('message')"
            >
              Relire le message
            </SiteCareButton>
            <SiteCareButton
              v-else-if="isEmailMissing"
              size="large"
              class="w-full"
              leading-icon="i-lucide-search"
              :is-disabled="pendingAction !== null"
              :is-loading="pendingAction === 'find-email'"
              @click="findEmail"
            >
              Chercher son email
            </SiteCareButton>
            <SiteCareButton
              v-else-if="site.tab === 'review'"
              size="large"
              class="w-full"
              leading-icon="i-lucide-refresh-cw"
              :is-disabled="pendingAction !== null"
              :is-loading="pendingAction === 'recheck'"
              @click="recheckSite"
            >
              Recontrôler le site
            </SiteCareButton>
            <SiteCareButton
              v-if="isEmailMissing && !isEmailFormOpen"
              variant="secondary"
              size="large"
              class="w-full"
              @click="openEmailForm"
            >
              La saisir à la main
            </SiteCareButton>
            <SiteCareButton
              v-if="canOfferCarePlan"
              variant="secondary"
              size="large"
              class="w-full"
              leading-icon="i-lucide-repeat"
              @click="openCarePlanForm"
            >
              Passer en suivi mensuel
            </SiteCareButton>
            <SiteCareButton
              v-if="site.care_plan !== null"
              variant="secondary"
              size="large"
              class="w-full"
              :is-disabled="pendingAction !== null"
              :is-loading="pendingAction === 'stop-care-plan'"
              @click="stopCarePlanConfirmModal?.open()"
            >
              Arrêter le suivi
            </SiteCareButton>
            <SiteCareButton
              variant="secondary"
              size="large"
              class="w-full"
              :is-disabled="pendingAction !== null"
              :is-loading="pendingAction === 'remove'"
              @click="removeConfirmModal?.open()"
            >
              Retirer de la liste
            </SiteCareButton>
          </template>

          <template v-else-if="step === 'message'">
            <SiteCareButton
              size="large"
              class="w-full"
              leading-icon="i-lucide-send"
              :is-disabled="pendingAction !== null || !site.can_send"
              :is-loading="pendingAction === 'send'"
              @click="sendMessage"
            >
              Envoyer par email
            </SiteCareButton>
            <SiteCareButton
              variant="secondary"
              size="large"
              class="w-full"
              leading-icon="i-lucide-arrow-left"
              :is-disabled="pendingAction !== null"
              @click="goToStep('finding')"
            >
              Revenir au constat
            </SiteCareButton>
          </template>

          <template v-else>
            <SiteCareButton
              v-if="nextQueuedSiteRoute !== null"
              :to="nextQueuedSiteRoute"
              size="large"
              class="w-full"
              trailing-icon="i-lucide-arrow-right"
            >
              Site suivant
            </SiteCareButton>
            <SiteCareButton
              :to="SITE_CARE_SECTION_PATH"
              :variant="nextQueuedSiteRoute !== null ? 'secondary' : 'primary'"
              size="large"
              class="w-full"
            >
              Revenir à mes prospects
            </SiteCareButton>
          </template>
        </div>
      </SiteCareStepActionCard>
    </div>

    <UiConfirmModal
      ref="removeConfirmModal"
      title="Retirer de la liste"
      :message="removeConfirmMessage"
      confirm-text="Retirer"
      cancel-text="Annuler"
      @confirm="removeSite"
    />
    <UiConfirmModal
      ref="stopCarePlanConfirmModal"
      title="Arrêter le suivi"
      :message="stopCarePlanConfirmMessage"
      confirm-text="Arrêter le suivi"
      cancel-text="Annuler"
      @confirm="stopCarePlan"
    />
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import type { UseDashboardScrollReturn, UseToastReturn } from '~/types/Composables'
import type { UiConfirmModalHandle } from '~/types/UiConfirmModal'
import type { UseSiteCareWritingQueueReturn } from '../../../../composables/useSiteCareWritingQueue'
import type { SiteCareSettings } from '../../../../types/SiteCareSettings'
import type { SiteCareSiteDetail } from '../../../../types/SiteCareSite'
import type {
  SiteCareSiteAction,
  SiteCareSiteActionOutcome,
  SiteCareSiteOutcomeStep,
  SiteCareSitePageStep,
  SiteCareSiteWritingStep,
} from '../../../../types/SiteCareSitePage'
import { computed, onMounted, ref, watch } from 'vue'
import { useDashboardScroll } from '~/composables/useDashboardScroll'
import { useToast } from '~/composables/useToast'
import { formatEuros } from '~/utils/currency'
import { formatLongMonthDate } from '~/utils/date'
import { FieldsValidation } from '~/utils/fieldsValidation'
import { useSiteCareWritingQueue } from '../../../../composables/useSiteCareWritingQueue'
import {
  SITE_CARE_SECTION_PATH,
  SITE_CARE_SITES_PATH,
  SITE_CARE_WRITING_QUEUE_QUERY,
} from '../../../../constants/siteCareModule'
import { SiteCareService } from '../../../../services/siteCareService'
import { SiteCareBusinessLabels } from '../../../../utils/siteCareBusinessLabels'

definePageMeta({ layout: 'dashboard', middleware: ['auth', 'site-care-module'] })

const route: ReturnType<typeof useRoute> = useRoute()
const toast: UseToastReturn = useToast()
const { scrollToTop }: UseDashboardScrollReturn = useDashboardScroll()
const { queuedSiteIds, ensureQueue }: UseSiteCareWritingQueueReturn = useSiteCareWritingQueue()

const CENTS_PER_EURO: number = 100

const WRITING_STEPS: SiteCareSiteWritingStep[] = ['finding', 'message']

const WRITING_STEP_NAMES: Record<SiteCareSiteWritingStep, string> = {
  finding: 'le constat',
  message: 'le message',
}

const OUTCOME_STEP_TITLES: Record<SiteCareSiteOutcomeStep, string> = {
  sent: 'Message envoyé',
  removed: 'Retiré de vos prospects',
}

const site: Ref<SiteCareSiteDetail | null> = ref(null)
const isLoadingSite: Ref<boolean> = ref(true)
const step: Ref<SiteCareSitePageStep> = ref('finding')
const hasPageLink: Ref<boolean> = ref(false)
const pendingAction: Ref<SiteCareSiteAction | null> = ref(null)
const actionFailureMessage: Ref<string | null> = ref(null)
const isEmailFormOpen: Ref<boolean> = ref(false)
const emailDraft: Ref<string> = ref('')
const emailSearchResult: Ref<string | null> = ref(null)
const isCarePlanFormOpen: Ref<boolean> = ref(false)
const carePlanMonthlyEuros: Ref<number | null> = ref(null)
const removeConfirmModal: Ref<UiConfirmModalHandle | null> = ref(null)
const stopCarePlanConfirmModal: Ref<UiConfirmModalHandle | null> = ref(null)

const pageTitle: ComputedRef<string> = computed(
  (): string => `${site.value?.business_name ?? 'Un prospect'} · DevLeadHunter`,
)

const siteId: ComputedRef<number | null> = computed((): number | null => {
  const rawSiteId: string | string[] | undefined = route.params.siteId
  const parsedSiteId: number = Number(Array.isArray(rawSiteId) ? rawSiteId[0] : rawSiteId)
  return Number.isInteger(parsedSiteId) && parsedSiteId > 0 ? parsedSiteId : null
})

const isInWritingQueue: ComputedRef<boolean> = computed(
  (): boolean => route.query.queue === SITE_CARE_WRITING_QUEUE_QUERY.queue,
)

const queuePosition: ComputedRef<number | null> = computed((): number | null => {
  if (!isInWritingQueue.value || siteId.value === null) {
    return null
  }
  const queueIndex: number = queuedSiteIds.value.indexOf(siteId.value)
  return queueIndex === -1 ? null : queueIndex + 1
})

const nextQueuedSiteId: ComputedRef<number | null> = computed((): number | null => {
  if (!isInWritingQueue.value) {
    return null
  }
  const queueIndex: number = siteId.value === null ? -1 : queuedSiteIds.value.indexOf(siteId.value)
  const nextSiteIds: number[] = queuedSiteIds.value
    .slice(queueIndex + 1)
    .filter((queuedSiteId: number): boolean => queuedSiteId !== siteId.value)
  return nextSiteIds[0] ?? null
})

const nextQueuedSiteRoute: ComputedRef<RouteLocationRaw | null> = computed((): RouteLocationRaw | null =>
  nextQueuedSiteId.value === null
    ? null
    : { path: `${SITE_CARE_SITES_PATH}/${nextQueuedSiteId.value}`, query: SITE_CARE_WRITING_QUEUE_QUERY },
)

const tradeAndCityLabel: ComputedRef<string> = computed((): string =>
  site.value === null ? '' : SiteCareBusinessLabels.placeOf(site.value.trade_label, site.value.city),
)

const canWrite: ComputedRef<boolean> = computed(
  (): boolean => site.value !== null && site.value.message !== null && site.value.can_send,
)

const isEmailMissing: ComputedRef<boolean> = computed(
  (): boolean => site.value !== null && site.value.message !== null && site.value.email === null,
)

const isWritingFlowShown: ComputedRef<boolean> = computed(
  (): boolean =>
    step.value !== 'removed' &&
    (canWrite.value || isEmailMissing.value || step.value === 'message' || step.value === 'sent'),
)

const isSiteStillToHandle: ComputedRef<boolean> = computed(
  (): boolean => step.value === 'finding' || step.value === 'message',
)

const writingStepNumber: ComputedRef<number> = computed((): number => {
  const currentStep: SiteCareSitePageStep = step.value
  if (currentStep === 'sent' || currentStep === 'removed') {
    return WRITING_STEPS.length
  }
  return WRITING_STEPS.indexOf(currentStep) + 1
})

const stepTitle: ComputedRef<string> = computed((): string => {
  const currentStep: SiteCareSitePageStep = step.value
  if (currentStep === 'sent' || currentStep === 'removed') {
    return OUTCOME_STEP_TITLES[currentStep]
  }
  if (!isWritingFlowShown.value) {
    return site.value?.state.label ?? ''
  }
  return `Étape ${writingStepNumber.value} sur ${WRITING_STEPS.length} : ${WRITING_STEP_NAMES[currentStep]}`
})

const refusalSentence: ComputedRef<string | null> = computed((): string | null => {
  if (step.value !== 'finding' || site.value === null || site.value.message === null || site.value.email === null) {
    return null
  }
  return site.value.can_send ? null : site.value.send_refusal
})

const canSaveEmail: ComputedRef<boolean> = computed(
  (): boolean => FieldsValidation.isEmail(emailDraft.value) && emailDraft.value.trim() !== (site.value?.email ?? ''),
)

const isCarePlanShown: ComputedRef<boolean> = computed(
  (): boolean =>
    site.value !== null &&
    (site.value.care_plan !== null || site.value.sent_messages.length > 0 || isCarePlanFormOpen.value),
)

const canOfferCarePlan: ComputedRef<boolean> = computed(
  (): boolean =>
    site.value !== null &&
    site.value.care_plan === null &&
    site.value.sent_messages.length > 0 &&
    !isCarePlanFormOpen.value,
)

const canStartCarePlan: ComputedRef<boolean> = computed(
  (): boolean =>
    typeof carePlanMonthlyEuros.value === 'number' &&
    Number.isFinite(carePlanMonthlyEuros.value) &&
    carePlanMonthlyEuros.value > 0,
)

const carePlanSummary: ComputedRef<string | null> = computed((): string | null => {
  if (site.value === null || site.value.care_plan === null) {
    return null
  }
  const monthlyPrice: string = formatEuros(site.value.care_plan.monthly_price_cents)
  return `${monthlyPrice} par mois, depuis le ${formatLongMonthDate(site.value.care_plan.started_at)}.`
})

const removeConfirmMessage: ComputedRef<string> = computed(
  (): string => `${site.value?.business_name ?? 'Ce prospect'} sort de vos prospects, et son site ne sera plus relu.`,
)

const stopCarePlanConfirmMessage: ComputedRef<string> = computed(
  (): string =>
    `Le suivi mensuel de ${site.value?.business_name ?? 'ce client'} s’arrête : son site n’est plus regardé chaque mois.`,
)

useSeoMeta({ title: pageTitle })

/** Forget everything about the site shown before, so nothing of it lingers on the next one. */
function resetPage(): void {
  site.value = null
  step.value = 'finding'
  hasPageLink.value = false
  pendingAction.value = null
  actionFailureMessage.value = null
  isEmailFormOpen.value = false
  emailDraft.value = ''
  emailSearchResult.value = null
  isCarePlanFormOpen.value = false
  carePlanMonthlyEuros.value = null
}

/**
 * Read the walk of « Traiter les sites » when the page belongs to it; a failure only hides the counter.
 * @returns A promise resolved once the walk is read, or given up.
 */
async function loadWritingQueueIfWalking(): Promise<void> {
  if (isInWritingQueue.value) {
    await ensureQueue().catch((): void => undefined)
  }
}

/**
 * Load the site of the address, and the walk of « Traiter les sites » when the page belongs to it.
 * @returns A promise resolved once the site is shown, or its failure is.
 */
async function loadSite(): Promise<void> {
  const requestedSiteId: number | null = siteId.value
  isLoadingSite.value = true
  try {
    if (requestedSiteId === null) {
      site.value = null
      return
    }
    const [loadedSite]: [SiteCareSiteDetail, unknown] = await Promise.all([
      SiteCareService.getSite(requestedSiteId),
      loadWritingQueueIfWalking(),
    ])
    if (requestedSiteId === siteId.value) {
      showSite(loadedSite)
    }
  } catch {
    if (requestedSiteId === siteId.value) {
      site.value = null
    }
  } finally {
    if (requestedSiteId === siteId.value) {
      isLoadingSite.value = false
    }
  }
}

/**
 * Show a site as the API returned it, with its address ready to be corrected.
 * @param shownSite - The site to show.
 */
function showSite(shownSite: SiteCareSiteDetail): void {
  site.value = shownSite
  emailDraft.value = shownSite.email ?? ''
  if (shownSite.page_url === null) {
    hasPageLink.value = false
  }
}

/**
 * Show a step of the page and bring it back to its top.
 * @param nextStep - The step to show.
 */
function goToStep(nextStep: SiteCareSitePageStep): void {
  actionFailureMessage.value = null
  step.value = nextStep
  scrollToTop()
}

/**
 * Run one action on the site shown, then show the site as the API returned it.
 * @param action - The action, shown as pending meanwhile.
 * @param request - The call to make for the site.
 * @param failureFallback - The sentence to give when the API says nothing readable about a failure.
 * @returns The updated site, or the sentence saying why the action failed; neither when another action is pending.
 */
async function runSiteAction(
  action: SiteCareSiteAction,
  request: (actedSiteId: number) => Promise<SiteCareSiteDetail>,
  failureFallback: string,
): Promise<SiteCareSiteActionOutcome> {
  const actedSiteId: number | null = site.value?.id ?? null
  if (actedSiteId === null || pendingAction.value !== null) {
    return { updatedSite: null, failureMessage: null }
  }
  pendingAction.value = action
  actionFailureMessage.value = null
  try {
    const updatedSite: SiteCareSiteDetail = await request(actedSiteId)
    if (actedSiteId === site.value?.id) {
      showSite(updatedSite)
    }
    return { updatedSite, failureMessage: null }
  } catch (error: unknown) {
    return { updatedSite: null, failureMessage: SiteCareService.failureMessage(error, failureFallback) }
  } finally {
    pendingAction.value = null
  }
}

/**
 * Send the message to the prospect; a refusal of the API stays written in the card.
 * @returns A promise resolved once the message is sent, or the refusal is shown.
 */
async function sendMessage(): Promise<void> {
  const outcome: SiteCareSiteActionOutcome = await runSiteAction(
    'send',
    (actedSiteId: number): Promise<SiteCareSiteDetail> =>
      SiteCareService.sendMessage(actedSiteId, { with_page_link: hasPageLink.value }),
    'Le message n’est pas parti. Réessayez dans un instant.',
  )
  if (outcome.updatedSite !== null) {
    goToStep('sent')
  }
  actionFailureMessage.value = outcome.failureMessage
}

/**
 * Look for the prospect's address on its website; the form to type it opens when none is found.
 * @returns A promise resolved once the result is shown.
 */
async function findEmail(): Promise<void> {
  emailSearchResult.value = null
  const outcome: SiteCareSiteActionOutcome = await runSiteAction(
    'find-email',
    (actedSiteId: number): Promise<SiteCareSiteDetail> => SiteCareService.findSiteEmail(actedSiteId),
    'La recherche de l’adresse n’a pas abouti. Réessayez dans un instant.',
  )
  if (outcome.updatedSite !== null) {
    const foundEmail: string | null = outcome.updatedSite.email
    emailSearchResult.value =
      foundEmail === null
        ? 'Aucune adresse trouvée sur son site. Vous pouvez la saisir.'
        : 'Adresse trouvée sur son site.'
    isEmailFormOpen.value = foundEmail === null
  }
  actionFailureMessage.value = outcome.failureMessage
}

/** Open the field that types or corrects the prospect's address. */
function openEmailForm(): void {
  emailDraft.value = site.value?.email ?? ''
  isEmailFormOpen.value = true
}

/**
 * Save the address typed or corrected by hand.
 * @returns A promise resolved once the address is saved, or the failure is shown.
 */
async function saveEmail(): Promise<void> {
  if (!canSaveEmail.value) {
    return
  }
  const typedEmail: string = emailDraft.value.trim()
  const outcome: SiteCareSiteActionOutcome = await runSiteAction(
    'save-email',
    (actedSiteId: number): Promise<SiteCareSiteDetail> =>
      SiteCareService.updateSiteEmail(actedSiteId, { email: typedEmail }),
    'L’adresse n’a pas pu être enregistrée.',
  )
  if (outcome.updatedSite !== null) {
    isEmailFormOpen.value = false
    emailSearchResult.value = null
    toast.success('Adresse enregistrée.')
  }
  actionFailureMessage.value = outcome.failureMessage
}

/**
 * Look at the site again from the outside.
 * @returns A promise resolved once the new check is shown, or the failure is.
 */
async function recheckSite(): Promise<void> {
  const outcome: SiteCareSiteActionOutcome = await runSiteAction(
    'recheck',
    (actedSiteId: number): Promise<SiteCareSiteDetail> => SiteCareService.recheckSite(actedSiteId),
    'Le site n’a pas pu être recontrôlé.',
  )
  if (outcome.updatedSite !== null) {
    toast.success('Site recontrôlé.')
  }
  actionFailureMessage.value = outcome.failureMessage
}

/**
 * Open the small form that starts the monthly follow-up, its price prefilled with the one of the settings.
 * @returns A promise resolved once the price is prefilled, or left empty when the settings cannot be read.
 */
async function openCarePlanForm(): Promise<void> {
  isCarePlanFormOpen.value = true
  if (carePlanMonthlyEuros.value !== null) {
    return
  }
  const settings: SiteCareSettings | null = await SiteCareService.getSettings().catch((): null => null)
  if (settings !== null && carePlanMonthlyEuros.value === null) {
    carePlanMonthlyEuros.value = settings.monthly_price_cents / CENTS_PER_EURO
  }
}

/**
 * Put the prospect in monthly follow-up at the price typed.
 * @returns A promise resolved once the follow-up started, or the failure is shown.
 */
async function startCarePlan(): Promise<void> {
  const monthlyEuros: number | null = carePlanMonthlyEuros.value
  if (!canStartCarePlan.value || monthlyEuros === null) {
    return
  }
  const outcome: SiteCareSiteActionOutcome = await runSiteAction(
    'start-care-plan',
    (actedSiteId: number): Promise<SiteCareSiteDetail> =>
      SiteCareService.startCarePlan(actedSiteId, { monthly_price_cents: Math.round(monthlyEuros * CENTS_PER_EURO) }),
    'Le suivi mensuel n’a pas pu démarrer.',
  )
  if (outcome.updatedSite !== null) {
    isCarePlanFormOpen.value = false
    toast.success('Suivi mensuel démarré.')
  }
  actionFailureMessage.value = outcome.failureMessage
}

/**
 * Stop the monthly follow-up of the prospect, once confirmed, then read the site again.
 * @returns A promise resolved once the follow-up stopped, or the failure is shown.
 */
async function stopCarePlan(): Promise<void> {
  const carePlanId: number | null = site.value?.care_plan?.id ?? null
  if (carePlanId === null) {
    return
  }
  const outcome: SiteCareSiteActionOutcome = await runSiteAction(
    'stop-care-plan',
    async (actedSiteId: number): Promise<SiteCareSiteDetail> => {
      await SiteCareService.stopCarePlan(carePlanId)
      return SiteCareService.getSite(actedSiteId)
    },
    'L’arrêt du suivi n’a pas pu être confirmé. Rechargez la page pour vérifier.',
  )
  if (outcome.updatedSite !== null) {
    toast.success('Suivi arrêté.')
  }
  actionFailureMessage.value = outcome.failureMessage
}

/**
 * Take the prospect out of the list, once confirmed.
 * @returns A promise resolved once the prospect is removed, or the failure is shown.
 */
async function removeSite(): Promise<void> {
  const removedSiteId: number | null = site.value?.id ?? null
  if (removedSiteId === null || pendingAction.value !== null) {
    return
  }
  pendingAction.value = 'remove'
  actionFailureMessage.value = null
  try {
    await SiteCareService.removeSite(removedSiteId)
    goToStep('removed')
  } catch (error: unknown) {
    actionFailureMessage.value = SiteCareService.failureMessage(error, 'Le prospect n’a pas pu être retiré.')
  } finally {
    pendingAction.value = null
  }
}

watch(
  (): number | null => siteId.value,
  async (): Promise<void> => {
    resetPage()
    scrollToTop()
    await loadSite()
  },
)

onMounted(async (): Promise<void> => {
  await loadSite()
})
</script>
