<template>
  <div class="flex min-h-full flex-col gap-6">
    <UiPageHeader
      eyebrow="Entretien de sites"
      :has-eyebrow-mark="false"
      title="Suivis"
      description="Les clients qui ont pris le suivi mensuel. Leur site est regardé chaque mois, les mises à jour sont faites pour eux, et ils reçoivent un rapport."
    />

    <UiLoader v-if="carePlanList === null && isLoadingCarePlans" label="Chargement des suivis…" />

    <UiEmptyState
      v-else-if="carePlanList === null"
      title="Chargement impossible"
      description="Les suivis n’ont pas pu être chargés. Vérifiez votre connexion et réessayez."
    >
      <template #action>
        <button type="button" class="btn-secondary" @click="loadCarePlans">
          <UIcon name="i-lucide-refresh-cw" class="h-4 w-4" />
          Réessayer
        </button>
      </template>
    </UiEmptyState>

    <template v-else>
      <section class="grid grid-cols-2 gap-4 @3xl:grid-cols-3" aria-label="Chiffres des suivis">
        <UiStatCard label="Clients en suivi" :value="carePlanList.stats.client_count" icon="i-lucide-users" />
        <UiStatCard
          label="Revenu par mois"
          :value="carePlanList.stats.monthly_revenue_label"
          icon="i-lucide-banknote"
        />
        <UiStatCard
          label="Rapports à envoyer"
          :value="carePlanList.stats.reports_due_count"
          icon="i-lucide-file-text"
          class="col-span-2 @3xl:col-span-1"
        />
      </section>

      <UiEmptyState
        v-if="carePlanList.plans.length === 0"
        title="Personne n’est encore en suivi"
        description="Le suivi mensuel se propose depuis la fiche d’un prospect."
      />

      <div v-else class="app-card overflow-hidden">
        <div
          class="hidden gap-5 bg-[var(--app-surface-2)] px-5 py-3 @2xl:grid @2xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1.5fr)_minmax(0,1.2fr)_8.125rem] @2xl:items-center"
        >
          <span class="app-label">Client</span>
          <span class="app-label">Dernier contrôle</span>
          <span class="app-label">Rapport du mois</span>
          <span class="app-label text-right">Suivi</span>
        </div>

        <ul>
          <li
            v-for="carePlan in carePlanList.plans"
            :key="carePlan.id"
            class="border-t border-[var(--app-line)] p-5 first:border-t-0 @2xl:first:border-t"
          >
            <div
              class="grid gap-2.5 @2xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1.5fr)_minmax(0,1.2fr)_8.125rem] @2xl:items-start @2xl:gap-5"
            >
              <div class="min-w-0">
                <p class="text-[15px] font-semibold text-[var(--app-ink)]">{{ carePlan.business_name }}</p>
                <p class="mt-0.5 text-[13px] text-[var(--app-ink-soft)]">
                  {{ carePlan.trade_label }} · {{ carePlan.city }}
                </p>
                <p class="font-[family-name:var(--app-font-mono)] text-xs break-all text-[var(--app-ink-soft)]">
                  {{ carePlan.domain }}
                </p>
              </div>

              <div class="min-w-0">
                <p class="text-[15px] leading-snug text-[var(--app-ink)]">{{ carePlan.last_check_summary }}</p>
                <p class="mt-0.5 text-[13px] text-[var(--app-ink-soft)]">{{ carePlan.last_checked_label }}</p>
              </div>

              <div class="min-w-0">
                <span class="app-badge whitespace-nowrap" :class="REPORT_STATE_BADGE_CLASSES[carePlan.report_state]">
                  {{ carePlan.report_label }}
                </span>
                <p class="mt-1.5 text-[13px] text-[var(--app-ink-soft)]">{{ carePlan.report_detail }}</p>
              </div>

              <div class="min-w-0 @2xl:text-right">
                <p class="text-[15px] font-semibold text-[var(--app-ink)]">{{ carePlan.monthly_label }}</p>
                <p class="mt-0.5 text-[13px] text-[var(--app-ink-soft)]">{{ carePlan.since_label }}</p>
              </div>
            </div>

            <div class="mt-4 flex flex-wrap gap-2">
              <button
                v-if="carePlan.can_send_report"
                type="button"
                class="btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="pendingAction !== null"
                @click="askToSendReport(carePlan)"
              >
                <UIcon
                  :name="isActionPending(carePlan, 'send-report') ? 'i-lucide-loader-circle' : 'i-lucide-send'"
                  class="h-4 w-4"
                  :class="{ 'animate-spin': isActionPending(carePlan, 'send-report') }"
                />
                Envoyer le rapport
              </button>
              <button
                type="button"
                class="btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="pendingAction !== null"
                @click="askToStopCarePlan(carePlan)"
              >
                <UIcon
                  v-if="isActionPending(carePlan, 'stop')"
                  name="i-lucide-loader-circle"
                  class="h-4 w-4 animate-spin"
                />
                Arrêter le suivi
              </button>
            </div>

            <p
              v-if="actionFailure && actionFailure.carePlanId === carePlan.id"
              class="mt-3 text-sm leading-relaxed text-[var(--app-red)]"
              role="alert"
            >
              {{ actionFailure.message }}
            </p>
          </li>
        </ul>
      </div>
    </template>

    <UiConfirmModal
      ref="reportConfirmModal"
      title="Envoyer le rapport"
      :message="reportConfirmMessage"
      confirm-text="Envoyer"
      cancel-text="Annuler"
      confirm-button-variant="primary"
      @confirm="sendReport"
    />
    <UiConfirmModal
      ref="stopConfirmModal"
      title="Arrêter le suivi"
      :message="stopConfirmMessage"
      confirm-text="Arrêter le suivi"
      cancel-text="Annuler"
      @confirm="stopCarePlan"
    />
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { UseToastReturn } from '~/types/Composables'
import type { UiConfirmModalHandle } from '~/types/UiConfirmModal'
import type {
  SiteCareCarePlan,
  SiteCareCarePlanListResponse,
  SiteCareCarePlanReportState,
} from '../../../types/SiteCareCarePlan'
import type {
  SiteCareCarePlanAction,
  SiteCareCarePlanActionFailure,
  SiteCareCarePlanPendingAction,
} from '../../../types/SiteCareCarePlansPage'
import { computed, onMounted, ref } from 'vue'
import { useToast } from '~/composables/useToast'
import { SiteCareService } from '../../../services/siteCareService'

definePageMeta({ layout: 'dashboard', middleware: ['auth', 'site-care-module'] })

useSeoMeta({ title: 'Suivis · DevLeadHunter' })

const toast: UseToastReturn = useToast()

const REPORT_STATE_BADGE_CLASSES: Record<SiteCareCarePlanReportState, string> = {
  due: 'app-badge--strong',
  sent: 'app-badge--success',
}

const carePlanList: Ref<SiteCareCarePlanListResponse | null> = ref(null)
const isLoadingCarePlans: Ref<boolean> = ref(true)
const carePlanToConfirm: Ref<SiteCareCarePlan | null> = ref(null)
const pendingAction: Ref<SiteCareCarePlanPendingAction | null> = ref(null)
const actionFailure: Ref<SiteCareCarePlanActionFailure | null> = ref(null)
const reportConfirmModal: Ref<UiConfirmModalHandle | null> = ref(null)
const stopConfirmModal: Ref<UiConfirmModalHandle | null> = ref(null)

const reportConfirmMessage: ComputedRef<string> = computed(
  (): string => `Le rapport du mois part tout de suite à ${carePlanToConfirm.value?.business_name ?? 'ce client'}.`,
)

const stopConfirmMessage: ComputedRef<string> = computed(
  (): string =>
    `Le suivi mensuel de ${carePlanToConfirm.value?.business_name ?? 'ce client'} s’arrête : son site n’est plus regardé chaque mois.`,
)

/**
 * Read the follow-ups and their figures; the ones on screen stay while they are read again.
 * @returns A promise resolved once they are shown; a failure keeps what was on screen.
 */
async function loadCarePlans(): Promise<void> {
  isLoadingCarePlans.value = true
  try {
    carePlanList.value = await SiteCareService.listCarePlans()
  } catch {
    if (carePlanList.value !== null) {
      toast.error('Les suivis n’ont pas pu être relus.')
    }
  } finally {
    isLoadingCarePlans.value = false
  }
}

/**
 * Whether an action is running on a follow-up, to show it on its button.
 * @param carePlan - The follow-up of the row.
 * @param action - The action of the button.
 * @returns True while that action runs on that follow-up.
 */
function isActionPending(carePlan: SiteCareCarePlan, action: SiteCareCarePlanAction): boolean {
  return pendingAction.value?.carePlanId === carePlan.id && pendingAction.value.action === action
}

/**
 * Ask before the report of the month leaves: an email is really sent.
 * @param carePlan - The follow-up whose report to send.
 */
function askToSendReport(carePlan: SiteCareCarePlan): void {
  carePlanToConfirm.value = carePlan
  reportConfirmModal.value?.open()
}

/**
 * Ask before a follow-up stops.
 * @param carePlan - The follow-up to stop.
 */
function askToStopCarePlan(carePlan: SiteCareCarePlan): void {
  carePlanToConfirm.value = carePlan
  stopConfirmModal.value?.open()
}

/**
 * Run a confirmed action on its follow-up, then read the list again; a refusal of the API shows under the row.
 * @param action - The action, shown as running on its button meanwhile.
 * @param request - The call to make for the follow-up.
 * @param successMessage - The sentence to show once done.
 * @param failureFallback - The sentence to give when the API says nothing readable about a failure.
 * @returns A promise resolved once the list is up to date, or the failure is shown.
 */
async function runConfirmedAction(
  action: SiteCareCarePlanAction,
  request: (carePlanId: number) => Promise<unknown>,
  successMessage: string,
  failureFallback: string,
): Promise<void> {
  const carePlan: SiteCareCarePlan | null = carePlanToConfirm.value
  if (carePlan === null || pendingAction.value !== null) {
    return
  }
  pendingAction.value = { carePlanId: carePlan.id, action }
  actionFailure.value = null
  try {
    await request(carePlan.id)
    toast.success(successMessage)
    await loadCarePlans()
  } catch (error: unknown) {
    actionFailure.value = { carePlanId: carePlan.id, message: SiteCareService.failureMessage(error, failureFallback) }
  } finally {
    pendingAction.value = null
  }
}

/**
 * Send the report of the month, once confirmed.
 * @returns A promise resolved once the report is sent, or the refusal is shown.
 */
async function sendReport(): Promise<void> {
  await runConfirmedAction(
    'send-report',
    (carePlanId: number): Promise<unknown> => SiteCareService.sendCarePlanReport(carePlanId),
    'Rapport envoyé.',
    'Le rapport n’est pas parti. Réessayez dans un instant.',
  )
}

/**
 * Stop the follow-up, once confirmed.
 * @returns A promise resolved once the follow-up is stopped, or the failure is shown.
 */
async function stopCarePlan(): Promise<void> {
  await runConfirmedAction(
    'stop',
    (carePlanId: number): Promise<unknown> => SiteCareService.stopCarePlan(carePlanId),
    'Suivi arrêté.',
    'Le suivi n’a pas pu être arrêté.',
  )
}

onMounted(async (): Promise<void> => {
  await loadCarePlans()
})
</script>
