<template>
  <div>
    <span class="block text-[13px] font-medium text-[var(--app-ink-soft)]">Messages envoyés</span>
    <ul class="mt-1">
      <li
        v-for="(sentMessage, sentMessageIndex) in props.sentMessages"
        :key="sentMessageIndex"
        class="flex items-start justify-between gap-3 border-t border-[var(--app-line)] py-3 first:border-t-0"
      >
        <span class="min-w-0">
          <span class="block text-[15px] font-medium text-[var(--app-ink)]">{{ sentMessage.subject }}</span>
          <span class="block text-sm text-[var(--app-ink-soft)]">
            {{ sentMessage.kind_label }} · {{ formatShortMonthDayTime(sentMessage.sent_at) }}
          </span>
        </span>
        <span
          class="inline-flex shrink-0 items-center rounded-full bg-[var(--app-surface-2)] px-3 py-1 text-[13px] font-medium whitespace-nowrap text-[var(--app-ink-soft)]"
        >
          {{ sentMessage.status_label }}
        </span>
      </li>
    </ul>
  </div>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { SiteCareSentMessageListProps } from '../../types/SiteCareSentMessageList'
import type { SiteCareSentMessage } from '../../types/SiteCareSite'
import { formatShortMonthDayTime } from '~/utils/date'

const props: SiteCareSentMessageListProps = defineProps({
  sentMessages: {
    type: Array as PropType<SiteCareSentMessage[]>,
    required: true,
  },
})
</script>
