<template>
  <div>
    <span class="block text-[13px] font-medium text-[var(--app-ink-soft)]">Suivi mensuel</span>
    <p v-if="props.carePlanSummary" class="mt-1 text-[15px] text-[var(--app-ink)]">{{ props.carePlanSummary }}</p>
    <form v-else-if="props.isFormOpen" class="mt-2 flex flex-wrap items-center gap-2" @submit.prevent="emit('start')">
      <label class="flex items-center gap-2 text-sm text-[var(--app-ink-soft)]">
        <input
          v-model.number="monthlyEuros"
          type="number"
          inputmode="numeric"
          min="1"
          step="1"
          aria-label="Prix du suivi, en euros par mois"
          class="app-input h-12 w-24 rounded-xl text-right text-[15px] font-semibold"
        />
        € par mois
      </label>
      <SiteCareButton
        type="submit"
        :is-disabled="!props.canStart || props.isActionPending"
        :is-loading="props.isStarting"
      >
        Démarrer le suivi
      </SiteCareButton>
    </form>
    <p v-else class="mt-1 text-[15px] text-[var(--app-ink-soft)]">Pas de suivi pour l’instant.</p>
  </div>
</template>

<script lang="ts" setup>
import type { EmitFn, ModelRef, PropType } from 'vue'
import type { SiteCareCarePlanDetailsEmits, SiteCareCarePlanDetailsProps } from '../../types/SiteCareCarePlanDetails'

const monthlyEuros: ModelRef<number | null> = defineModel<number | null>('monthlyEuros', { required: true })

const props: SiteCareCarePlanDetailsProps = defineProps({
  carePlanSummary: {
    type: String as PropType<string | null>,
    default: null,
  },
  isFormOpen: {
    type: Boolean,
    default: false,
  },
  canStart: {
    type: Boolean,
    default: false,
  },
  isStarting: {
    type: Boolean,
    default: false,
  },
  isActionPending: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<SiteCareCarePlanDetailsEmits> = defineEmits<SiteCareCarePlanDetailsEmits>()
</script>
