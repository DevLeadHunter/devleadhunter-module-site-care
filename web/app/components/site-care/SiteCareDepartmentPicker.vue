<template>
  <div class="flex flex-col gap-4">
    <div
      v-if="selectedDepartments.length > 0"
      class="flex flex-wrap gap-2"
      role="group"
      aria-label="Départements choisis"
    >
      <SiteCareChoiceChip
        v-for="department in selectedDepartments"
        :key="department.key"
        is-selected
        :aria-label="`Retirer ${department.label}`"
        @click="toggleDepartment(department.key)"
      >
        {{ department.label }}
      </SiteCareChoiceChip>
    </div>

    <input
      v-model="searchText"
      type="search"
      autocomplete="off"
      placeholder="Chercher un département, par son nom ou son numéro"
      aria-label="Chercher un département"
      class="app-input h-12 max-w-md rounded-full px-4 text-[15px]"
    />

    <div v-if="matchingDepartments.length > 0" class="flex flex-wrap gap-2" role="group" aria-label="Départements">
      <SiteCareChoiceChip
        v-for="department in matchingDepartments"
        :key="department.key"
        :is-selected="false"
        :is-disabled="!canAddDepartment"
        @click="toggleDepartment(department.key)"
      >
        {{ department.label }}
      </SiteCareChoiceChip>
    </div>
    <p v-else-if="hasSearchText" class="text-sm text-[var(--app-ink-soft)]">Aucun département ne correspond.</p>

    <p class="text-sm text-[var(--app-ink-soft)]">
      {{ selectedDepartments.length }} sur {{ props.maximumCount }} au plus. Comptez 20 à 40 minutes de lecture par
      département.
    </p>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, ModelRef, PropType, Ref } from 'vue'
import type { SiteCareDepartmentPickerProps } from '../../types/SiteCareDepartmentPicker'
import type { SiteCareSearchLabelledChoice } from '../../types/SiteCareSearch'
import { computed, ref } from 'vue'
import { ProspectSearches } from '~/utils/prospectSearches'

const selectedDepartmentCodes: ModelRef<string[]> = defineModel<string[]>({ required: true })

const props: SiteCareDepartmentPickerProps = defineProps({
  departments: {
    type: Array as PropType<SiteCareSearchLabelledChoice[]>,
    required: true,
  },
  maximumCount: {
    type: Number,
    required: true,
  },
})

const MAXIMUM_SHOWN_MATCH_COUNT: number = 12

const searchText: Ref<string> = ref('')

const selectedDepartments: ComputedRef<SiteCareSearchLabelledChoice[]> = computed((): SiteCareSearchLabelledChoice[] =>
  selectedDepartmentCodes.value.flatMap((departmentCode: string): SiteCareSearchLabelledChoice[] =>
    props.departments.filter((department: SiteCareSearchLabelledChoice): boolean => department.key === departmentCode),
  ),
)

const hasSearchText: ComputedRef<boolean> = computed((): boolean => searchText.value.trim() !== '')

const matchingDepartments: ComputedRef<SiteCareSearchLabelledChoice[]> = computed(
  (): SiteCareSearchLabelledChoice[] => {
    const searchedText: string = ProspectSearches.foldLabel(searchText.value)
    if (searchedText === '') {
      return []
    }
    return props.departments
      .filter(
        (department: SiteCareSearchLabelledChoice): boolean =>
          !selectedDepartmentCodes.value.includes(department.key) &&
          (ProspectSearches.foldLabel(department.key).startsWith(searchedText) ||
            ProspectSearches.foldLabel(department.label).includes(searchedText)),
      )
      .slice(0, MAXIMUM_SHOWN_MATCH_COUNT)
  },
)

const canAddDepartment: ComputedRef<boolean> = computed(
  (): boolean => selectedDepartmentCodes.value.length < props.maximumCount,
)

/**
 * Pick a département, or take it out of the selection; a département is added only while the selection has room.
 * @param departmentCode - The code of the département clicked.
 */
function toggleDepartment(departmentCode: string): void {
  if (selectedDepartmentCodes.value.includes(departmentCode)) {
    selectedDepartmentCodes.value = selectedDepartmentCodes.value.filter(
      (selectedCode: string): boolean => selectedCode !== departmentCode,
    )
    return
  }

  if (canAddDepartment.value) {
    selectedDepartmentCodes.value = [...selectedDepartmentCodes.value, departmentCode]
    searchText.value = ''
  }
}
</script>
