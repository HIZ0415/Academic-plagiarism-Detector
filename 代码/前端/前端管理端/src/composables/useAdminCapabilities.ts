import { computed } from 'vue'
import { useUserStore } from '@/stores/user'

/** 管理端角色能力（对齐概要设计：组织级审批 vs 跨组织治理） */
export function useAdminCapabilities() {
  const userStore = useUserStore()

  const isSoftwareAdmin = computed(() => userStore.admin_type === 'software_admin')
  const isOrganizationAdmin = computed(() => userStore.admin_type === 'organization_admin')
  /** 可对本组织人工审核申请执行通过/拒绝 */
  const canApproveManualReview = computed(() => isOrganizationAdmin.value)
  /** 可进入审批页查看（组织管理员操作；软件管理员只读监督） */
  const canViewManualReviewQueue = computed(
    () => isOrganizationAdmin.value || isSoftwareAdmin.value,
  )

  return {
    isSoftwareAdmin,
    isOrganizationAdmin,
    canApproveManualReview,
    canViewManualReviewQueue,
  }
}
