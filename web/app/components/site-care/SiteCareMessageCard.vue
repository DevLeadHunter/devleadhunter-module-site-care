<template>
  <SiteCareCard title="Votre message" title-id="site-care-message-title">
    <dl class="grid grid-cols-[auto_minmax(0,1fr)] items-baseline gap-x-4 gap-y-3 text-base">
      <dt class="text-[var(--app-ink-soft)]">À</dt>
      <dd class="flex min-w-0 flex-wrap items-baseline gap-x-3.5 gap-y-0.5">
        <span class="font-semibold text-[var(--app-ink)]">{{ props.businessName }}</span>
        <span class="font-medium break-all text-[#2563eb] dark:text-[#8fb4ff]">{{ props.email }}</span>
      </dd>
      <dt class="text-[var(--app-ink-soft)]">Objet</dt>
      <dd class="min-w-0 font-semibold text-[var(--app-ink)]">{{ props.message.subject }}</dd>
    </dl>
    <div class="flex flex-col gap-2">
      <div class="flex items-center gap-0.5">
        <span class="text-[13px] font-medium text-[var(--app-ink-soft)]">Texte</span>
        <SiteCareInfoTip
          accessible-label="À propos du message"
          info-text="Le message est écrit à partir de ce qui a été vu sur son site. Votre signature s’ajoute en bas, et rien ne part tant que vous n’avez pas appuyé sur « Envoyer par email »."
        />
      </div>
      <div class="flex flex-col gap-3.5 rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] px-6 py-5">
        <p
          v-for="(paragraph, paragraphIndex) in messageParagraphs"
          :key="paragraphIndex"
          class="text-base leading-relaxed break-words whitespace-pre-line text-[var(--app-ink)]"
        >
          {{ paragraph }}
        </p>
      </div>
    </div>
    <div v-if="props.hasPreparedPage" class="flex items-center gap-4 border-t border-[var(--app-line)] pt-5">
      <div class="min-w-0 flex-1">
        <label for="site-care-page-link" class="block font-semibold text-[var(--app-ink)]">
          Ajouter le lien de la page préparée pour lui
        </label>
        <span class="block text-sm text-[var(--app-ink-soft)]">Sans ce lien, tout est dit dans le message.</span>
      </div>
      <UiSwitch id="site-care-page-link" v-model="hasPageLink" />
    </div>
  </SiteCareCard>
</template>

<script lang="ts" setup>
import type { ComputedRef, ModelRef, PropType } from 'vue'
import type { SiteCareMessageCardProps } from '../../types/SiteCareMessageCard'
import type { SiteCareMessage } from '../../types/SiteCareSite'
import { computed } from 'vue'

const hasPageLink: ModelRef<boolean> = defineModel<boolean>('hasPageLink', { required: true })

const props: SiteCareMessageCardProps = defineProps({
  businessName: {
    type: String,
    required: true,
  },
  email: {
    type: String as PropType<string | null>,
    default: null,
  },
  message: {
    type: Object as PropType<SiteCareMessage>,
    required: true,
  },
  hasPreparedPage: {
    type: Boolean,
    default: false,
  },
})

const messageParagraphs: ComputedRef<string[]> = computed((): string[] =>
  hasPageLink.value ? props.message.paragraphs_with_link : props.message.paragraphs,
)
</script>
