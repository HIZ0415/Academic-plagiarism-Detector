/**
 * router/index.ts
 *
 * Automatic routes for `./src/pages/*.vue`
 */

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
import { getEffectiveRoleAtGuard } from '@/utils/effectiveRole'

const PUBLISHER_PATHS = [
  '/upload',
  '/history',
  '/annual',
  '/detect',
  '/manual-review-result',
  '/image-review',
  '/community-feedback',
  '/comprehensive-report',
  '/detection-settings',
]
const REVIEWER_PATHS = ['/review', '/manual-review']

function isUnder(path: string, roots: string[]) {
  return roots.some((r) => path === r || path.startsWith(`${r}/`))
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: setupLayouts(routes),
})

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
    _from: RouteLocationNormalizedLoaded,
    next: NavigationGuardNext,
  ) => {
    if (!isLoggedIn.value) {
      if (to.path === '/login') {
        next()
      } else {
        next('/login')
      }
      return
    }

    if (to.path === '/login') {
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

    if (to.path === '/detect/image') {
      next({ path: '/upload', replace: true })
      return
    }

    if (to.path === '/detect/paper') {
      const { tab, ...rest } = to.query
      const paperTab = tab === 'resource' ? 'resource' : 'aigc'
      next({
        path: '/upload',
        query: { ...rest, section: 'paper', paper_tab: paperTab },
        replace: true,
      })
      return
    }

    if (to.path === '/detect/review') {
      next({
        path: '/upload',
        query: { ...to.query, section: 'review' },
        replace: true,
      })
      return
    }

    if (to.path === '/multimodal-fusion') {
      next({
        path: '/comprehensive-report',
        query: { ...to.query },
        replace: true,
      })
      return
    }

    const legacyManualDetail = to.path.match(/^\/task\/detail\/(\d+)$/)
    if (legacyManualDetail) {
      next({
        path: `/manual-review/${legacyManualDetail[1]}`,
        query: to.query,
        replace: true,
      })
      return
    }

    const legacyImageReview = to.path.match(/^\/task\/(\d+)$/)
    if (legacyImageReview) {
      next({
        path: `/image-review/${legacyImageReview[1]}`,
        query: to.query,
        replace: true,
      })
      return
    }

    const legacyStep = to.path.match(/^\/step\/(\d+)$/)
    if (legacyStep) {
      next({
        path: '/history',
        query: { ...to.query, detail_id: legacyStep[1] },
        replace: true,
      })
      return
    }

    next()
  },
)

export default router
