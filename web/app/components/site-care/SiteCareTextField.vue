<template>
  <label class="flex flex-col gap-2">
    <span class="text-[13px] font-medium text-[var(--app-ink-soft)]">{{ props.fieldLabel }}</span>
    <input
      v-model="fieldValue"
      type="text"
      autocomplete="off"
      :placeholder="props.placeholder"
      class="app-input h-12 rounded-xl px-4 text-[15px]"
    />
  </label>
</template>

<script lang="ts" setup>
import type { ModelRef } from 'vue'
import type { SiteCareTextFieldProps } from '../../types/SiteCareTextField'

const fieldValue: ModelRef<string> = defineModel<string>({ required: true })

const props: SiteCareTextFieldProps = defineProps({
  fieldLabel: {
    type: String,
    required: true,
  },
  placeholder: {
    type: String,
    default: '',
  },
})
</script>
