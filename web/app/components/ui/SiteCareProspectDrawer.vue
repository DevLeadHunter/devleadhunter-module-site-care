<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="props.open && props.siteId !== null"
        class="fixed top-0 right-0 bottom-[var(--app-drawer-bottom)] z-50 flex w-full flex-col border-l border-[var(--app-line)] bg-[var(--app-bg)] pt-[env(safe-area-inset-top)] pb-[var(--app-drawer-bottom-padding)] shadow-2xl sm:max-w-[580px] xl:max-w-[480px]"
        role="dialog"
        aria-modal="true"
        aria-labelledby="site-care-prospect-title"
      >
        <UiDrawerHeader
          :title="site?.business_name ?? 'Fiche du prospect'"
          icon="i-lucide-shield-check"
          :show-back="props.showBack"
          title-id="site-care-prospect-title"
          @back="emit('back')"
          @close="emit('close')"
        >
          <template v-if="site" #badges>
            <span class="app-badge mb-1.5" :class="SITE_CARE_TONE_BADGE_CLASSES[site.state.tone]">
              {{ site.state.label }}
            </span>
          </template>
          <template v-if="site" #subtitle>
            <p class="mt-0.5 text-sm text-[var(--app-ink-soft)]">{{ site.trade_label }} · {{ site.city }}</p>
            <p class="mt-1.5 font-[family-name:var(--app-font-mono)] text-xs break-words text-[var(--app-ink-soft)]">
              {{ site.domain }}
            </p>
            <p class="font-[family-name:var(--app-font-mono)] text-xs break-words text-[var(--app-ink-soft)]">
              {{ site.email ?? 'Pas d’email connu' }}
            </p>
          </template>
        </UiDrawerHeader>

        <div class="flex-1 space-y-5 overflow-y-auto px-5 py-5">
          <UiLoader v-if="isLoadingSite" label="Chargement de la fiche…" />

          <section v-else-if="site === null" class="app-card p-5">
            <p class="text-sm text-[var(--app-ink-soft)]">La fiche n’a pas pu être chargée.</p>
            <button type="button" class="btn-secondary mt-3" @click="reloadSite">
              <UIcon name="i-lucide-refresh-cw" class="h-4 w-4" />
              Réessayer
            </button>
          </section>

          <template v-else>
            <section v-if="site.unread_text" class="app-card p-5">
              <h3 class="text-[15px] font-semibold text-[var(--app-ink)]">Contrôle à refaire</h3>
              <p class="mt-3 text-sm leading-relaxed text-[var(--app-ink-soft)]">{{ site.unread_text }}</p>
            </section>

            <section v-for="group in findingGroups" :key="group.title" class="app-card p-5">
              <h3 class="text-[15px] font-semibold text-[var(--app-ink)]">{{ group.title }}</h3>
              <ul class="mt-3 divide-y divide-[var(--app-line)]">
                <li v-for="point in group.points" :key="point.key" class="py-3 first:pt-0 last:pb-0">
                  <div class="flex flex-wrap items-center gap-1.5">
                    <SiteCareIssueTag :kind="point.kind" :label="point.kind_label" :tone="group.tone" />
                    <SiteCareTechnologyChip v-if="point.tech" :technology="point.tech" />
                  </div>
                  <p class="mt-2 text-sm leading-relaxed text-[var(--app-ink)]">{{ point.fact }}</p>
                </li>
              </ul>
            </section>

            <section v-if="site.good_line || site.hidden_line" class="app-card p-5">
              <h3 class="text-[15px] font-semibold text-[var(--app-ink)]">Le reste</h3>
              <div class="mt-3 space-y-2 text-sm leading-relaxed text-[var(--app-ink-soft)]">
                <p v-if="site.good_line">{{ site.good_line }}</p>
                <p v-if="site.hidden_line">{{ site.hidden_line }}</p>
              </div>
            </section>

            <section v-if="site.offer.length > 0" class="app-card p-5">
              <h3 class="text-[15px] font-semibold text-[var(--app-ink)]">Ce que je peux lui proposer</h3>
              <dl class="mt-3 divide-y divide-[var(--app-line)] text-sm text-[var(--app-ink)]">
                <div
                  v-for="line in site.offer"
                  :key="line.label"
                  class="flex items-baseline justify-between gap-4 py-2.5 first:pt-0"
                >
                  <dt class="min-w-0">{{ line.label }}</dt>
                  <dd class="font-[family-name:var(--app-font-mono)] font-medium whitespace-nowrap">
                    {{ line.price_label }}
                  </dd>
                </div>
                <div class="flex items-baseline justify-between gap-4 pt-2.5">
                  <dt class="min-w-0">Ensuite, s’il le souhaite : suivi mensuel</dt>
                  <dd class="font-[family-name:var(--app-font-mono)] font-medium whitespace-nowrap">
                    {{ site.monthly_label }}
                  </dd>
                </div>
              </dl>
            </section>

            <section v-if="site.message" class="app-card p-5">
              <h3 class="text-[15px] font-semibold text-[var(--app-ink)]">Le message</h3>
              <p class="app-label mt-3">Objet</p>
              <p class="mt-1 text-sm font-semibold text-[var(--app-ink)]">{{ site.message.subject }}</p>
              <div class="mt-4 space-y-3">
                <p
                  v-for="(paragraph, paragraphIndex) in messageParagraphs"
                  :key="paragraphIndex"
                  class="text-sm leading-relaxed whitespace-pre-line text-[var(--app-ink)]"
                >
                  {{ paragraph }}
                </p>
              </div>

              <div v-if="site.page_url" class="mt-4 flex min-h-11 items-center">
                <UiSwitch
                  id="site-care-page-link"
                  v-model="shouldAddPageLink"
                  label="Ajouter le lien de la page préparée pour lui"
                />
              </div>

              <div v-if="site.can_send || site.page_url" class="mt-3 flex flex-wrap gap-2.5">
                <button
                  v-if="site.can_send"
                  type="button"
                  class="btn-primary flex-[1_1_12.5rem] disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="pendingAction !== null"
                  @click="sendConfirmModal?.open()"
                >
                  <UIcon
                    :name="pendingAction === 'send' ? 'i-lucide-loader-circle' : 'i-lucide-send'"
                    class="h-4 w-4"
                    :class="{ 'animate-spin': pendingAction === 'send' }"
                  />
                  Envoyer par email
                </button>
                <button
                  v-if="site.page_url"
                  type="button"
                  class="btn-secondary flex-[1_1_12.5rem]"
                  @click="openPreparedPage"
                >
                  Voir la page préparée
                </button>
              </div>

              <p
                v-if="!site.can_send && site.send_refusal"
                class="mt-3 text-sm leading-relaxed text-[var(--app-ink-soft)]"
              >
                {{ site.send_refusal }}
              </p>
              <p v-if="sendFailureMessage" class="mt-3 text-sm leading-relaxed text-[var(--app-red)]" role="alert">
                {{ sendFailureMessage }}
              </p>
            </section>

            <section class="app-card p-5">
              <h3 class="text-[15px] font-semibold text-[var(--app-ink)]">Son email</h3>

              <button
                v-if="site.email === null"
                type="button"
                class="btn-primary mt-3 w-full disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="pendingAction !== null"
                @click="findEmail"
              >
                <UIcon
                  :name="pendingAction === 'find-email' ? 'i-lucide-loader-circle' : 'i-lucide-search'"
                  class="h-4 w-4"
                  :class="{ 'animate-spin': pendingAction === 'find-email' }"
                />
                Chercher son email sur son site
              </button>
              <p v-if="emailSearchResult" class="mt-3 text-sm leading-relaxed text-[var(--app-ink)]" role="status">
                {{ emailSearchResult }}
              </p>

              <form class="mt-3 flex flex-wrap items-end gap-2" @submit.prevent="saveEmail">
                <label class="min-w-0 flex-[1_1_14rem]">
                  <span class="app-label mb-1.5 block">
                    {{ site.email === null ? 'Le saisir à la main' : 'Corriger son email' }}
                  </span>
                  <input
                    v-model="emailDraft"
                    type="email"
                    inputmode="email"
                    autocomplete="off"
                    autocapitalize="off"
                    spellcheck="false"
                    placeholder="contact@exemple.fr"
                    class="app-input"
                  />
                </label>
                <button
                  type="submit"
                  class="btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="!canSaveEmail || pendingAction !== null"
                >
                  <UIcon
                    v-if="pendingAction === 'save-email'"
                    name="i-lucide-loader-circle"
                    class="h-4 w-4 animate-spin"
                  />
                  Enregistrer
                </button>
              </form>
            </section>

            <section class="space-y-3" aria-label="Autres actions">
              <p v-if="carePlanSummary" class="text-sm leading-relaxed text-[var(--app-ink-soft)]">
                {{ carePlanSummary }}
              </p>
              <div class="flex flex-wrap gap-2">
                <button type="button" class="btn-secondary" @click="openWebsite">
                  <UIcon name="i-lucide-external-link" class="h-4 w-4" />
                  Ouvrir son site
                </button>
                <button
                  type="button"
                  class="btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="pendingAction !== null"
                  @click="recheckSite"
                >
                  <UIcon
                    :name="pendingAction === 'recheck' ? 'i-lucide-loader-circle' : 'i-lucide-refresh-cw'"
                    class="h-4 w-4"
                    :class="{ 'animate-spin': pendingAction === 'recheck' }"
                  />
                  Recontrôler le site
                </button>
                <button
                  v-if="site.care_plan === null"
                  type="button"
                  class="btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="pendingAction !== null || isCarePlanFormOpen"
                  @click="openCarePlanForm"
                >
                  <UIcon name="i-lucide-repeat" class="h-4 w-4" />
                  Passer en suivi mensuel
                </button>
                <button
                  v-else
                  type="button"
                  class="btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="pendingAction !== null"
                  @click="stopCarePlanConfirmModal?.open()"
                >
                  <UIcon
                    v-if="pendingAction === 'stop-care-plan'"
                    name="i-lucide-loader-circle"
                    class="h-4 w-4 animate-spin"
                  />
                  Arrêter le suivi
                </button>
                <button
                  type="button"
                  class="btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="pendingAction !== null"
                  @click="removeConfirmModal?.open()"
                >
                  <UIcon
                    :name="pendingAction === 'remove' ? 'i-lucide-loader-circle' : 'i-lucide-trash-2'"
                    class="h-4 w-4"
                    :class="{ 'animate-spin': pendingAction === 'remove' }"
                  />
                  Retirer de la liste
                </button>
              </div>

              <form
                v-if="isCarePlanFormOpen && site.care_plan === null"
                class="app-card flex flex-wrap items-end gap-2 p-5"
                @submit.prevent="startCarePlan"
              >
                <label class="min-w-0 flex-[1_1_10rem]">
                  <span class="app-label mb-1.5 block">Prix du suivi, en euros par mois</span>
                  <input
                    v-model.number="carePlanMonthlyEuros"
                    type="number"
                    inputmode="numeric"
                    min="1"
                    step="1"
                    class="app-input"
                  />
                </label>
                <button
                  type="submit"
                  class="btn-primary disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="!canStartCarePlan || pendingAction !== null"
                >
                  <UIcon
                    v-if="pendingAction === 'start-care-plan'"
                    name="i-lucide-loader-circle"
                    class="h-4 w-4 animate-spin"
                  />
                  Démarrer le suivi
                </button>
                <button type="button" class="btn-secondary" @click="isCarePlanFormOpen = false">Annuler</button>
              </form>
            </section>

            <section v-if="site.sent_messages.length > 0" class="app-card p-5">
              <h3 class="text-[15px] font-semibold text-[var(--app-ink)]">Messages envoyés</h3>
              <ul class="mt-3 divide-y divide-[var(--app-line)]">
                <li
                  v-for="(sentMessage, sentMessageIndex) in site.sent_messages"
                  :key="sentMessageIndex"
                  class="flex items-start justify-between gap-3 py-3 first:pt-0 last:pb-0"
                >
                  <div class="min-w-0">
                    <p class="text-sm font-medium text-[var(--app-ink)]">{{ sentMessage.kind_label }}</p>
                    <p class="mt-0.5 text-sm text-[var(--app-ink-soft)]">{{ sentMessage.subject }}</p>
                    <p class="mt-1 font-[family-name:var(--app-font-mono)] text-xs text-[var(--app-ink-soft)]">
                      {{ formatShortMonthDayTime(sentMessage.sent_at) }}
                    </p>
                  </div>
                  <span class="app-badge shrink-0 whitespace-nowrap">{{ sentMessage.status_label }}</span>
                </li>
              </ul>
            </section>
          </template>
        </div>
      </div>
    </Transition>

    <UiConfirmModal
      ref="sendConfirmModal"
      title="Envoyer ce message"
      :message="sendConfirmMessage"
      confirm-text="Envoyer"
      cancel-text="Annuler"
      confirm-button-variant="primary"
      @confirm="sendMessage"
    />
    <UiConfirmModal
      ref="stopCarePlanConfirmModal"
      title="Arrêter le suivi"
      :message="stopCarePlanConfirmMessage"
      confirm-text="Arrêter le suivi"
      cancel-text="Annuler"
      @confirm="stopCarePlan"
    />
    <UiConfirmModal
      ref="removeConfirmModal"
      title="Retirer de la liste"
      :message="removeConfirmMessage"
      confirm-text="Retirer"
      cancel-text="Annuler"
      @confirm="removeSite"
    />
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type { UseOpenExternalUrlReturn, UseToastReturn } from '~/types/Composables'
import type { UiConfirmModalHandle } from '~/types/UiConfirmModal'
import type { SiteCareSettings } from '../../types/SiteCareSettings'
import type { SiteCareSiteDetail } from '../../types/SiteCareSite'
import type {
  SiteCareFindingGroup,
  SiteCareProspectSheetAction,
  SiteCareSiteActionOutcome,
  UiSiteCareProspectDrawerEmits,
  UiSiteCareProspectDrawerProps,
} from '../../types/UiSiteCareProspectDrawer'
import { computed, ref, watch } from 'vue'
import { useOpenExternalUrl } from '~/composables/useOpenExternalUrl'
import { useToast } from '~/composables/useToast'
import { formatEuros } from '~/utils/currency'
import { formatLongMonthDate, formatShortMonthDayTime } from '~/utils/date'
import { FieldsValidation } from '~/utils/fieldsValidation'
import { SITE_CARE_TONE_BADGE_CLASSES } from '../../constants/siteCareLabels'
import { SiteCareService } from '../../services/siteCareService'

const props: UiSiteCareProspectDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  siteId: {
    type: Number as PropType<number | null>,
    default: null,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiSiteCareProspectDrawerEmits> = defineEmits<UiSiteCareProspectDrawerEmits>()

const toast: UseToastReturn = useToast()
const { openExternalUrl }: UseOpenExternalUrlReturn = useOpenExternalUrl()

const site: Ref<SiteCareSiteDetail | null> = ref(null)
const isLoadingSite: Ref<boolean> = ref(false)
const pendingAction: Ref<SiteCareProspectSheetAction | null> = ref(null)
const shouldAddPageLink: Ref<boolean> = ref(false)
const sendFailureMessage: Ref<string | null> = ref(null)
const emailDraft: Ref<string> = ref('')
const emailSearchResult: Ref<string | null> = ref(null)
const isCarePlanFormOpen: Ref<boolean> = ref(false)
const carePlanMonthlyEuros: Ref<number | null> = ref(null)
const sendConfirmModal: Ref<UiConfirmModalHandle | null> = ref(null)
const stopCarePlanConfirmModal: Ref<UiConfirmModalHandle | null> = ref(null)
const removeConfirmModal: Ref<UiConfirmModalHandle | null> = ref(null)

const findingGroups: ComputedRef<SiteCareFindingGroup[]> = computed((): SiteCareFindingGroup[] => {
  if (site.value === null) {
    return []
  }
  const groups: SiteCareFindingGroup[] = [
    { title: 'À corriger', tone: 'red', points: site.value.fixes },
    { title: 'À surveiller', tone: 'amber', points: site.value.watches },
  ]
  return groups.filter((group: SiteCareFindingGroup): boolean => group.points.length > 0)
})

const messageParagraphs: ComputedRef<string[]> = computed((): string[] => {
  if (site.value === null || site.value.message === null) {
    return []
  }
  return shouldAddPageLink.value ? site.value.message.paragraphs_with_link : site.value.message.paragraphs
})

const canSaveEmail: ComputedRef<boolean> = computed(
  (): boolean => FieldsValidation.isEmail(emailDraft.value) && emailDraft.value.trim() !== (site.value?.email ?? ''),
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
  return `Suivi mensuel à ${monthlyPrice} par mois, depuis le ${formatLongMonthDate(site.value.care_plan.started_at)}.`
})

const sendConfirmMessage: ComputedRef<string> = computed((): string => {
  const recipient: string = site.value?.email ?? 'ce prospect'
  const pageLinkMention: string = shouldAddPageLink.value ? ' Il contient le lien de la page préparée pour lui.' : ''
  return `Le message part tout de suite à ${recipient}.${pageLinkMention}`
})

const stopCarePlanConfirmMessage: ComputedRef<string> = computed(
  (): string =>
    `Le suivi mensuel de ${site.value?.business_name ?? 'ce client'} s’arrête : son site n’est plus regardé chaque mois.`,
)

const removeConfirmMessage: ComputedRef<string> = computed(
  (): string => `${site.value?.business_name ?? 'Ce prospect'} sort de vos prospects.`,
)

/**
 * Whether a reply still belongs to the sheet on screen: not closed, not switched to another site meanwhile.
 * @param siteId - The site the call was made for.
 * @returns True when the reply may update the sheet.
 */
function isShowing(siteId: number): boolean {
  return props.open && props.siteId === siteId
}

/**
 * Show a site as the API returned it, with its address ready to be corrected.
 * @param shownSite - The site to show.
 */
function showSite(shownSite: SiteCareSiteDetail): void {
  site.value = shownSite
  emailDraft.value = shownSite.email ?? ''
  if (shownSite.page_url === null) {
    shouldAddPageLink.value = false
  }
}

/** Forget everything about the site shown before, so nothing of it lingers on the next one. */
function resetSheet(): void {
  site.value = null
  pendingAction.value = null
  shouldAddPageLink.value = false
  sendFailureMessage.value = null
  emailDraft.value = ''
  emailSearchResult.value = null
  isCarePlanFormOpen.value = false
  carePlanMonthlyEuros.value = null
}

/**
 * Load the sheet of a site.
 * @param siteId - The site to load.
 * @returns A promise resolved once the sheet is shown, or its failure is.
 */
async function loadSite(siteId: number): Promise<void> {
  isLoadingSite.value = true
  try {
    const loadedSite: SiteCareSiteDetail = await SiteCareService.getSite(siteId)
    if (isShowing(siteId)) {
      showSite(loadedSite)
    }
  } catch {
    if (isShowing(siteId)) {
      site.value = null
    }
  } finally {
    if (isShowing(siteId)) {
      isLoadingSite.value = false
    }
  }
}

/**
 * Try again to load the sheet after a failure.
 * @returns A promise resolved once the sheet is shown, or its failure is.
 */
async function reloadSite(): Promise<void> {
  if (props.siteId !== null) {
    await loadSite(props.siteId)
  }
}

/**
 * Run one action on the site shown, then show the site as the API returned it and tell the list behind.
 * @param action - The action, shown as pending meanwhile.
 * @param request - The call to make for the site.
 * @param failureFallback - The sentence to give when the API says nothing readable about a failure.
 * @returns The updated site, or the sentence saying why the action failed; neither when another action is pending.
 */
async function runSiteAction(
  action: SiteCareProspectSheetAction,
  request: (siteId: number) => Promise<SiteCareSiteDetail>,
  failureFallback: string,
): Promise<SiteCareSiteActionOutcome> {
  const siteId: number | null = props.siteId
  if (siteId === null || pendingAction.value !== null) {
    return { updatedSite: null, failureMessage: null }
  }
  pendingAction.value = action
  try {
    const updatedSite: SiteCareSiteDetail = await request(siteId)
    if (isShowing(siteId)) {
      showSite(updatedSite)
    }
    // Broadcast even if the sheet moved on: the list matches the site by id.
    emit('updated', { type: 'updated', site: updatedSite })
    return { updatedSite, failureMessage: null }
  } catch (error: unknown) {
    return { updatedSite: null, failureMessage: SiteCareService.failureMessage(error, failureFallback) }
  } finally {
    pendingAction.value = null
  }
}

/**
 * Send the message to the prospect, once confirmed; a refusal of the API stays written under the button.
 * @returns A promise resolved once the message is sent, or the refusal is shown.
 */
async function sendMessage(): Promise<void> {
  sendFailureMessage.value = null
  const outcome: SiteCareSiteActionOutcome = await runSiteAction(
    'send',
    (siteId: number): Promise<SiteCareSiteDetail> =>
      SiteCareService.sendMessage(siteId, { with_page_link: shouldAddPageLink.value }),
    'Le message n’est pas parti. Réessayez dans un instant.',
  )
  if (outcome.updatedSite !== null) {
    toast.success('Message envoyé.')
  }
  sendFailureMessage.value = outcome.failureMessage
}

/**
 * Look for the prospect's address on its website, then say whether one was found.
 * @returns A promise resolved once the result is shown.
 */
async function findEmail(): Promise<void> {
  emailSearchResult.value = null
  const outcome: SiteCareSiteActionOutcome = await runSiteAction(
    'find-email',
    (siteId: number): Promise<SiteCareSiteDetail> => SiteCareService.findSiteEmail(siteId),
    'La recherche de l’adresse n’a pas abouti. Réessayez dans un instant.',
  )
  if (outcome.updatedSite !== null) {
    emailSearchResult.value =
      outcome.updatedSite.email === null
        ? 'Aucune adresse trouvée sur son site.'
        : `Adresse trouvée : ${outcome.updatedSite.email}`
  } else if (outcome.failureMessage !== null) {
    toast.error(outcome.failureMessage)
  }
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
    (siteId: number): Promise<SiteCareSiteDetail> => SiteCareService.updateSiteEmail(siteId, { email: typedEmail }),
    'L’adresse n’a pas pu être enregistrée.',
  )
  if (outcome.updatedSite !== null) {
    emailSearchResult.value = null
    toast.success('Email enregistré.')
  } else if (outcome.failureMessage !== null) {
    toast.error(outcome.failureMessage)
  }
}

/**
 * Look at the site again from the outside.
 * @returns A promise resolved once the new check is shown, or the failure is.
 */
async function recheckSite(): Promise<void> {
  const outcome: SiteCareSiteActionOutcome = await runSiteAction(
    'recheck',
    (siteId: number): Promise<SiteCareSiteDetail> => SiteCareService.recheckSite(siteId),
    'Le site n’a pas pu être recontrôlé.',
  )
  if (outcome.updatedSite !== null) {
    toast.success('Site recontrôlé.')
  } else if (outcome.failureMessage !== null) {
    toast.error(outcome.failureMessage)
  }
}

/**
 * Open the small form that starts the monthly follow-up, its price prefilled with the one of the settings.
 * @returns A promise resolved once the price is prefilled, or left empty when the settings cannot be read.
 */
async function openCarePlanForm(): Promise<void> {
  isCarePlanFormOpen.value = true
  const siteId: number | null = props.siteId
  if (siteId === null || carePlanMonthlyEuros.value !== null) {
    return
  }
  try {
    const settings: SiteCareSettings = await SiteCareService.getSettings()
    if (isShowing(siteId) && carePlanMonthlyEuros.value === null) {
      carePlanMonthlyEuros.value = settings.monthly_price_cents / 100
    }
  } catch {
    // The field stays empty: the price is typed by hand.
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
    (siteId: number): Promise<SiteCareSiteDetail> =>
      SiteCareService.startCarePlan(siteId, { monthly_price_cents: Math.round(monthlyEuros * 100) }),
    'Le suivi mensuel n’a pas pu démarrer.',
  )
  if (outcome.updatedSite !== null) {
    isCarePlanFormOpen.value = false
    toast.success('Suivi mensuel démarré.')
  } else if (outcome.failureMessage !== null) {
    toast.error(outcome.failureMessage)
  }
}

/**
 * Stop the monthly follow-up of the prospect, once confirmed, then read the sheet again.
 * @returns A promise resolved once the follow-up stopped, or the failure is shown.
 */
async function stopCarePlan(): Promise<void> {
  const carePlanId: number | null = site.value?.care_plan?.id ?? null
  if (carePlanId === null) {
    return
  }
  const outcome: SiteCareSiteActionOutcome = await runSiteAction(
    'stop-care-plan',
    async (siteId: number): Promise<SiteCareSiteDetail> => {
      await SiteCareService.stopCarePlan(carePlanId)
      return SiteCareService.getSite(siteId)
    },
    'L’arrêt du suivi n’a pas pu être confirmé. Rouvrez la fiche pour vérifier.',
  )
  if (outcome.updatedSite !== null) {
    toast.success('Suivi arrêté.')
  } else if (outcome.failureMessage !== null) {
    toast.error(outcome.failureMessage)
  }
}

/**
 * Take the prospect out of the list, once confirmed: its sheet closes with it.
 * @returns A promise resolved once the prospect is removed, or the failure is shown.
 */
async function removeSite(): Promise<void> {
  const siteId: number | null = props.siteId
  if (siteId === null || pendingAction.value !== null) {
    return
  }
  pendingAction.value = 'remove'
  try {
    await SiteCareService.removeSite(siteId)
    toast.success('Prospect retiré de la liste.')
    emit('updated', { type: 'deleted', siteId })
  } catch (error: unknown) {
    toast.error(SiteCareService.failureMessage(error, 'Le prospect n’a pas pu être retiré.'))
  } finally {
    pendingAction.value = null
  }
}

/**
 * Open the page prepared for the prospect in a new tab, marked as an internal visit so it is not counted as his.
 * @returns A promise resolved once the page is opened.
 */
async function openPreparedPage(): Promise<void> {
  const pageUrl: string | null = site.value?.page_url ?? null
  if (pageUrl === null) {
    return
  }
  await openExternalUrl(`${pageUrl}${pageUrl.includes('?') ? '&' : '?'}internal=1`)
}

/**
 * Open the prospect's own website in a new tab.
 * @returns A promise resolved once the website is opened.
 */
async function openWebsite(): Promise<void> {
  if (site.value !== null) {
    await openExternalUrl(site.value.website)
  }
}

watch(
  (): number | null => (props.open ? props.siteId : null),
  (siteId: number | null): void => {
    resetSheet()
    if (siteId === null) {
      isLoadingSite.value = false
      return
    }
    loadSite(siteId)
  },
  { immediate: true },
)
</script>

<style scoped>
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}

@media (prefers-reduced-motion: reduce) {
  .drawer-panel-enter-active,
  .drawer-panel-leave-active {
    transition: none;
  }
}
</style>
