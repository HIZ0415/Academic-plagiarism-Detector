/**
 * router/index.ts
 *
 * Automatic routes for `./src/pages/*.vue`
 */

// Composables（createRouter 从 vue-router 引入，避免解析到空的 vue-router-auto.d.ts 报「不是模块」）
import {
  createRouter,
  createWebHistory,
  type NavigationGuardNext,
  type RouteLocationNormalized,
  type RouteLocationNormalizedLoaded,
} from 'vue-router'
import { setupLayouts } from 'virtual:generated-layouts'
import { routes } from 'vue-router/auto-routes'
import { isLoggedIn } from '@/api/user'
import pinia from '@/stores'
import { useUiPreviewStore } from '@/stores/uiPreview'
import { getEffectiveRoleAtGuard } from '@/utils/effectiveRole'

const PUBLISHER_PATHS = ['/upload', '/history', '/annual', '/detect', '/manual-review-result', '/step']
const REVIEWER_PATHS = ['/review', '/task']

function isUnder(path: string, roots: string[]) {
  return roots.some((r) => path === r || path.startsWith(`${r}/`))
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: setupLayouts(routes),
})

// Workaround for https://github.com/vitejs/vite/issues/11804
router.onError((err: unknown, to: RouteLocationNormalized) => {
  const errMsg = err instanceof Error ? err.message : String(err)
  if (errMsg.includes('Failed to fetch dynamically imported module')) {
    if (!localStorage.getItem('vuetify:dynamic-reload')) {
      console.log('Reloading page to fix dynamic import error')
      localStorage.setItem('vuetify:dynamic-reload', 'true')
      location.assign(to.fullPath)
    } else {
      console.error('Dynamic import error, reloading page did not fix it', err)
    }
  } else {
    console.error(err)
  }
})

router.isReady().then(() => {
  localStorage.removeItem('vuetify:dynamic-reload')
})

router.beforeEach(
  (
    to: RouteLocationNormalized,
    from: RouteLocationNormalizedLoaded,
    next: NavigationGuardNext,
  ) => {
  const preview = useUiPreviewStore(pinia)
  const allowUnauth = isLoggedIn.value || preview.enabled

  if (!allowUnauth) {
    if (to.path === '/login') {
      next()
    } else {
      next('/login')
    }
    return
  }

  if (isLoggedIn.value && to.path === '/login') {
    next('/')
    return
  }

  const role = getEffectiveRoleAtGuard()
  if (role === 'reviewer' && isUnder(to.path, PUBLISHER_PATHS)) {
    next({ path: '/review', replace: true })
    return
  }
  if (role === 'publisher' && isUnder(to.path, REVIEWER_PATHS)) {
    next({ path: '/upload', replace: true })
    return
  }

  // 检测提交统一入口为 /upload；专项页仅保留带 task_id 的结果深链（历史「进入专项详情」）
  if (allowUnauth && (to.path === '/detect/paper' || to.path === '/detect/review') && !String(to.query.task_id || '').trim()) {
    next({ path: '/upload', replace: true })
    return
  }

  next()
  },
)

export default router
