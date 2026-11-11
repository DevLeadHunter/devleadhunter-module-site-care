<template>
  <div class="space-y-4">
    <UiRemovableChipList
      v-if="selectedDepartmentLabels.length > 0"
      :labels="selectedDepartmentLabels"
      @remove="removeDepartment"
    />
    <div v-if="canAddDepartment" class="@2xl:max-w-md">
      <UiSelectField
        :key="selectedDepartmentCodes.length"
        model-value=""
        :options="remainingDepartmentOptions"
        placeholder="Ajouter un département"
        @update:model-value="addDepartment"
      />
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, ModelRef, PropType } from 'vue'
import type { SelectFieldOption } from '~/types/SelectField'
import type { SiteCareDepartmentPickerProps } from '../../types/SiteCareDepartmentPicker'
import type { SiteCareSearchLabelledChoice } from '../../types/SiteCareSearch'
import { computed } from 'vue'

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

const selectedDepartments: ComputedRef<SiteCareSearchLabelledChoice[]> = computed((): SiteCareSearchLabelledChoice[] =>
  selectedDepartmentCodes.value.flatMap((departmentCode: string): SiteCareSearchLabelledChoice[] =>
    props.departments.filter((department: SiteCareSearchLabelledChoice): boolean => department.key === departmentCode),
  ),
)

const selectedDepartmentLabels: ComputedRef<string[]> = computed((): string[] =>
  selectedDepartments.value.map((department: SiteCareSearchLabelledChoice): string => department.label),
)

const remainingDepartmentOptions: ComputedRef<SelectFieldOption[]> = computed((): SelectFieldOption[] =>
  props.departments
    .filter(
      (department: SiteCareSearchLabelledChoice): boolean => !selectedDepartmentCodes.value.includes(department.key),
    )
    .map(
      (department: SiteCareSearchLabelledChoice): SelectFieldOption => ({
        value: department.key,
        label: department.label,
      }),
    ),
)

const canAddDepartment: ComputedRef<boolean> = computed(
  (): boolean => selectedDepartmentCodes.value.length < props.maximumCount,
)

/**
 * Add a département to the selection, once, while the selection has room for it.
 * @param departmentCode - The code of the département picked.
 */
function addDepartment(departmentCode: string): void {
  if (canAddDepartment.value && !selectedDepartmentCodes.value.includes(departmentCode)) {
    selectedDepartmentCodes.value = [...selectedDepartmentCodes.value, departmentCode]
  }
}

/**
 * Take a département out of the selection.
 * @param departmentLabel - The label of its chip.
 */
function removeDepartment(departmentLabel: string): void {
  const removedDepartment: SiteCareSearchLabelledChoice | undefined = selectedDepartments.value.find(
    (department: SiteCareSearchLabelledChoice): boolean => department.label === departmentLabel,
  )
  selectedDepartmentCodes.value = selectedDepartmentCodes.value.filter(
    (departmentCode: string): boolean => departmentCode !== removedDepartment?.key,
  )
}
</script>
