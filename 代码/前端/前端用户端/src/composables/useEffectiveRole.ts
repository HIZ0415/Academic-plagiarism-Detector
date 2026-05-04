import { computed } from 'vue'
import { isLoggedIn } from '@/api/user'
import { useUserStore } from '@/stores/user'
import { useUiPreviewStore } from '@/stores/uiPreview'

/** 登录态与界面预览下的统一角色（编辑=publisher，专家=reviewer） */
export function useEffectiveRole() {
  const userStore = useUserStore()
  const preview = useUiPreviewStore()

  const isPreviewMode = computed(() => preview.enabled && !isLoggedIn.value)

  const effectiveRole = computed<'publisher' | 'reviewer' | ''>(() => {
    if (preview.enabled && (preview.role === 'publisher' || preview.role === 'reviewer')) {
      return preview.role
    }
    if (isLoggedIn.value && userStore.role) {
      if (userStore.role === 'publisher' || userStore.role === 'reviewer') return userStore.role
    }
    return ''
  })

  const roleLabel = computed(() => {
    const r = effectiveRole.value
    if (r === 'publisher') return '编辑'
    if (r === 'reviewer') return '专家'
    return ''
  })

  const drawerSubtitle = computed(() => {
    if (isPreviewMode.value) return `预览 · ${roleLabel.value || '未选择'}`
    return userStore.role || ''
  })

  return {
    effectiveRole,
    isPreviewMode,
    roleLabel,
    drawerSubtitle,
    previewStore: preview,
    setPreviewRole: (r: 'publisher' | 'reviewer') => preview.setRole(r),
  }
}
