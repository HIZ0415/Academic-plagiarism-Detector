import { isLoggedIn } from '@/api/user'
import pinia from '@/stores'
import { useUserStore } from '@/stores/user'

export function resolveEffectiveRole(): 'publisher' | 'reviewer' | '' {
  if (!isLoggedIn.value) return ''
  const u = useUserStore(pinia)
  if (u.role === 'publisher' || u.role === 'reviewer') return u.role
  return ''
}

export function getEffectiveRoleAtGuard(): 'publisher' | 'reviewer' | '' {
  return resolveEffectiveRole()
}
