import { computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { resolveEffectiveRole } from '@/utils/effectiveRole'

export function useEffectiveRole() {
  const userStore = useUserStore()

  const effectiveRole = computed<'publisher' | 'reviewer' | ''>(() => resolveEffectiveRole())

  const roleLabel = computed(() => {
    const r = effectiveRole.value
    if (r === 'publisher') return '编辑'
    if (r === 'reviewer') return '专家'
    return ''
  })

  const drawerSubtitle = computed(() => userStore.role || '')

  return {
    effectiveRole,
    roleLabel,
    drawerSubtitle,
  }
}
