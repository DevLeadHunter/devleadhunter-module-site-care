<template>
  <div class="flex min-h-full flex-col gap-8">
    <SiteCarePageHeader
      title="Clients en suivi"
      :description="carePlanList?.summary_line ?? null"
      info-text="Le site de chaque client est regardé chaque mois, les mises à jour sont faites pour lui, et il reçoit un rapport. Le suivi se propose, et s’arrête, depuis la page de son site."
    />

    <UiLoader v-if="carePlanList === null && isLoadingCarePlans" label="Chargement des clients…" />

    <UiEmptyState
      v-else-if="carePlanList === null"
      title="Chargement impossible"
      description="Les clients en suivi n’ont pas pu être chargés. Vérifiez votre connexion et réessayez."
    >
      <template #action>
        <button type="button" class="app-btn-secondary" @click="loadCarePlans">
          <UIcon name="i-lucide-refresh-cw" class="h-4 w-4" />
          Réessayer
        </button>
      </template>
    </UiEmptyState>

    <UiEmptyState
      v-else-if="carePlanList.plans.length === 0"
      title="Personne n’est encore en suivi"
      description="Le suivi mensuel se propose depuis la page d’un site, une fois le premier message parti."
    />

    <template v-else>
      <SiteCareTodoCard
        v-if="planToReport !== null"
        eyebrow="À faire · le rapport du mois"
        :title="planToReport.business_name"
        :description="planToReport.last_check_summary"
        aria-label="Rapport à envoyer"
      >
        <template #tile>{{ SiteCareBusinessLabels.initialsOf(planToReport.business_name) }}</template>
        <p class="mt-1 text-sm text-[var(--app-ink-soft)]">{{ planToReport.report_detail }}</p>
        <template #actions>
          <SiteCareButton
            class="w-full"
            leading-icon="i-lucide-send"
            :is-loading="isSendingReport"
            @click="reportConfirmModal?.open()"
          >
            Envoyer le rapport
          </SiteCareButton>
          <SiteCareButton :to="`${SITE_CARE_SITES_PATH}/${planToReport.site_id}`" variant="secondary" class="w-full">
            Voir son site
          </SiteCareButton>
        </template>
        <template v-if="reportFailureMessage" #footer>
          <p class="w-full text-sm leading-relaxed text-[var(--app-red)]" role="alert">{{ reportFailureMessage }}</p>
        </template>
      </SiteCareTodoCard>

      <SiteCareTodoCard
        v-else
        eyebrow="À faire"
        title="Vous êtes à jour"
        description="Aucun rapport n’attend d’être envoyé."
        aria-label="Rien à faire"
      />

      <div class="grid gap-5 @3xl:grid-cols-2 @6xl:grid-cols-3">
        <SiteCareLinkCard
          v-for="carePlan in carePlanList.plans"
          :key="carePlan.id"
          :to="`${SITE_CARE_SITES_PATH}/${carePlan.site_id}`"
        >
          <div class="mb-3">
            <span
              class="inline-flex items-center rounded-full px-3 py-1 text-[13px] font-medium whitespace-nowrap"
              :class="SITE_CARE_TONE_CLASSES[REPORT_STATE_TONES[carePlan.report_state]]"
            >
              {{ carePlan.report_label }}
            </span>
          </div>
          <h2 class="text-lg leading-snug font-semibold tracking-[-0.01em] text-[var(--app-ink)]">
            {{ carePlan.business_name }}
          </h2>
          <span class="mt-0.5 block text-sm text-[var(--app-ink-soft)]">
            {{ SiteCareBusinessLabels.placeOf(carePlan.trade_label, carePlan.city) }}
          </span>
          <span class="block text-sm text-[var(--app-ink-soft)]">{{ carePlan.since_label }}</span>
          <div class="mt-auto pt-4">
            <div class="flex items-end gap-4 border-t border-[var(--app-line)] pt-4">
              <span class="min-w-0 flex-1">
                <span class="block text-[13px] font-medium text-[var(--app-ink-soft)]">
                  {{ carePlan.last_checked_label }}
                </span>
                <span class="block text-[15px] text-[var(--app-ink)]">{{ carePlan.last_check_summary }}</span>
              </span>
              <span class="shrink-0 text-right text-[15px] font-semibold text-[var(--app-ink)]">
                {{ carePlan.monthly_label }}
              </span>
            </div>
          </div>
        </SiteCareLinkCard>
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
import type { SiteCareTone } from '../../../types/SiteCareSite'
import { computed, onMounted, ref } from 'vue'
import { useToast } from '~/composables/useToast'
import { SITE_CARE_TONE_CLASSES } from '../../../constants/siteCareLabels'
import { SITE_CARE_SITES_PATH } from '../../../constants/siteCareModule'
import { SiteCareService } from '../../../services/siteCareService'
import { SiteCareBusinessLabels } from '../../../utils/siteCareBusinessLabels'

definePageMeta({ layout: 'dashboard', middleware: ['auth', 'site-care-module'] })

useSeoMeta({ title: 'Clients en suivi · DevLeadHunter' })

const toast: UseToastReturn = useToast()

const REPORT_STATE_TONES: Record<SiteCareCarePlanReportState, SiteCareTone> = {
  due: 'amber',
  sent: 'green',
}

const carePlanList: Ref<SiteCareCarePlanListResponse | null> = ref(null)
const isLoadingCarePlans: Ref<boolean> = ref(true)
const isSendingReport: Ref<boolean> = ref(false)
const reportFailureMessage: Ref<string | null> = ref(null)
const reportConfirmModal: Ref<UiConfirmModalHandle | null> = ref(null)

const planToReport: ComputedRef<SiteCareCarePlan | null> = computed(
  (): SiteCareCarePlan | null =>
    carePlanList.value?.plans.find((carePlan: SiteCareCarePlan): boolean => carePlan.can_send_report) ?? null,
)

const reportConfirmMessage: ComputedRef<string> = computed(
  (): string => `Le rapport du mois part tout de suite à ${planToReport.value?.business_name ?? 'ce client'}.`,
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
      toast.error('Les clients en suivi n’ont pas pu être relus.')
    }
  } finally {
    isLoadingCarePlans.value = false
  }
}

/**
 * Send the report of the month, once confirmed, then read the clients again; a refusal stays written in the card.
 * @returns A promise resolved once the report is sent, or the refusal is shown.
 */
async function sendReport(): Promise<void> {
  const carePlan: SiteCareCarePlan | null = planToReport.value
  if (carePlan === null || isSendingReport.value) {
    return
  }
  isSendingReport.value = true
  reportFailureMessage.value = null
  try {
    await SiteCareService.sendCarePlanReport(carePlan.id)
    toast.success(`Rapport envoyé à ${carePlan.business_name}.`)
    await loadCarePlans()
  } catch (error: unknown) {
    reportFailureMessage.value = SiteCareService.failureMessage(
      error,
      'Le rapport n’est pas parti. Réessayez dans un instant.',
    )
  } finally {
    isSendingReport.value = false
  }
}

onMounted(async (): Promise<void> => {
  await loadCarePlans()
})
</script>
