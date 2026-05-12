import { isLoggedIn } from '@/api/user'
import pinia from '@/stores'
import { useUserStore } from '@/stores/user'
import { useUiPreviewStore } from '@/stores/uiPreview'

/** 供路由守卫同步读取：界面预览开启时以预览角色为准；否则已登录以 JWT 对应角色为准 */
export function getEffectiveRoleAtGuard(): 'publisher' | 'reviewer' | '' {
  const p = useUiPreviewStore(pinia)
  if (p.enabled && (p.role === 'publisher' || p.role === 'reviewer')) {
    return p.role
  }
  if (isLoggedIn.value) {
    const u = useUserStore(pinia)
    if (u.role === 'publisher' || u.role === 'reviewer') return u.role
  }
  return ''
}
