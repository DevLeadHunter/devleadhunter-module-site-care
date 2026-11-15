<template>
  <div>
    <div class="flex items-center gap-0.5">
      <span class="text-[13px] font-medium text-[var(--app-ink-soft)]">Son adresse</span>
      <button
        v-if="isEmailShown"
        type="button"
        class="-my-3 inline-flex h-11 w-11 cursor-pointer items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
        aria-label="Corriger son adresse"
        title="Corriger son adresse"
        @click="emit('open-form')"
      >
        <UIcon name="i-lucide-pencil" class="h-4 w-4" />
      </button>
    </div>
    <template v-if="isEmailShown">
      <p class="mt-1 text-base font-medium break-all text-[#2563eb] dark:text-[#8fb4ff]">{{ props.email }}</p>
      <p v-if="props.emailSourceLabel" class="mt-1 text-sm text-[var(--app-ink-soft)]">
        {{ props.emailSourceLabel }}
      </p>
    </template>
    <p v-else-if="props.email === null" class="mt-1 text-[15px] text-[var(--app-ink)]">
      Pas encore trouvée sur son site.
    </p>
    <p v-if="props.emailSearchResult" class="mt-2 text-sm text-[var(--app-ink-soft)]" role="status">
      {{ props.emailSearchResult }}
    </p>
    <form v-if="props.isFormOpen" class="mt-3 flex flex-wrap gap-2" @submit.prevent="emit('save')">
      <input
        v-model="emailDraft"
        type="email"
        inputmode="email"
        autocomplete="off"
        autocapitalize="off"
        spellcheck="false"
        placeholder="contact@exemple.fr"
        aria-label="Son adresse e-mail"
        class="app-input h-12 min-w-0 flex-[999_1_12rem] rounded-full px-4 text-[15px]"
      />
      <SiteCareButton
        type="submit"
        class="flex-[1_1_auto]"
        :is-disabled="!props.canSave || props.isActionPending"
        :is-loading="props.isSaving"
      >
        Enregistrer
      </SiteCareButton>
    </form>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, ModelRef, PropType } from 'vue'
import type { SiteCareProspectEmailEmits, SiteCareProspectEmailProps } from '../../types/SiteCareProspectEmail'
import { computed } from 'vue'

const emailDraft: ModelRef<string> = defineModel<string>('emailDraft', { required: true })

const props: SiteCareProspectEmailProps = defineProps({
  email: {
    type: String as PropType<string | null>,
    default: null,
  },
  emailSourceLabel: {
    type: String as PropType<string | null>,
    default: null,
  },
  emailSearchResult: {
    type: String as PropType<string | null>,
    default: null,
  },
  isFormOpen: {
    type: Boolean,
    default: false,
  },
  canSave: {
    type: Boolean,
    default: false,
  },
  isSaving: {
    type: Boolean,
    default: false,
  },
  isActionPending: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<SiteCareProspectEmailEmits> = defineEmits<SiteCareProspectEmailEmits>()

const isEmailShown: ComputedRef<boolean> = computed((): boolean => props.email !== null && !props.isFormOpen)
</script>
