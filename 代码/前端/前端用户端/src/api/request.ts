//引入axios
import axios from 'axios'
import { fullFrontendMockEnabled, MOCK_FULL_SESSION_KEY } from '@/utils/mockMode'

/** 未配置或无效时使用相对路径 `/api`，走 Vite 代理到本机 Django */
function getApiOrigin(): string {
  const raw = import.meta.env.VITE_API_URL as string | undefined
  const t = typeof raw === 'string' ? raw.trim() : ''
  if (!t || t === 'undefined' || t === 'null') return ''
  return t.replace(/\/$/, '')
}

const apiOrigin = getApiOrigin()
export const API_BASE_URL = apiOrigin ? `${apiOrigin}/api` : '/api'

/** 这些路径绝不能附带旧 JWT，否则 JWTAuthentication 会先 401，登录体根本执行不到 */
const NO_AUTH_HEADER_PATHS = [
  '/login/',
  '/register/',
  '/admin-login/',
  '/password-reset/',
  '/password-reset/confirm/',
  '/token/refresh/',
]

function isNoAuthHeaderPath(url: string | undefined): boolean {
  if (!url) return false
  return NO_AUTH_HEADER_PATHS.some((p) => url.includes(p))
}

// 创建axios实例
const instance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {},
})

//请求拦截处理
instance.interceptors.request.use(
  (config) => {
    const path = config.url || ''
    if (isNoAuthHeaderPath(path)) {
      delete config.headers.Authorization
    } else {
      const token = localStorage.getItem('2-token')
      if (token) {
        config.headers['Authorization'] = 'Bearer ' + token
      }
    }
    return config
  },
  (error) => Promise.reject(error),
)

//相应拦截处理：登录/注册等返回的 401 不得走刷新令牌，否则会误刷新并整页跳转，看不到错误提示
instance.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const cfg = error.config as { url?: string; headers?: Record<string, string>; _retry?: boolean } | undefined
    const path = cfg?.url || ''

    if (!cfg || status !== 401 || isNoAuthHeaderPath(path) || cfg._retry) {
      return Promise.reject(error)
    }

    // 全栈 Mock 会话不使用远端刷新令牌，避免误清登录态
    try {
      if (fullFrontendMockEnabled() && localStorage.getItem(MOCK_FULL_SESSION_KEY) === '1') {
        return Promise.reject(error)
      }
    } catch {
      /* ignore */
    }

    return refreshToken()
      .then((newToken) => {
        cfg._retry = true
        cfg.headers = cfg.headers || {}
        cfg.headers['Authorization'] = 'Bearer ' + newToken
        return instance(cfg)
      })
      .catch((err) => {
        localStorage.removeItem('2-token')
        localStorage.removeItem('2-refresh')
        localStorage.setItem('2-isLoggedIn', 'false')
        // 界面预览（无登录盲改）时不得整页跳回登录，否则专家预览无法停留 /review
        if (typeof window !== 'undefined' && localStorage.getItem('2-ui-preview') !== '1') {
          window.location.assign('/login')
        }
        return Promise.reject(err)
      })
  },
)

const refreshToken = async () => {
  const refresh = localStorage.getItem('2-refresh')
  if (!refresh) {
    return Promise.reject(new Error('No refresh token available'))
  }

  const refreshUrl = apiOrigin ? `${apiOrigin}/api/token/refresh/` : '/api/token/refresh/'
  const response = await axios.post(refreshUrl, { refresh })

  if (response.data?.access) {
    localStorage.setItem('2-token', response.data.access)
    return response.data.access
  }
  return Promise.reject(new Error('Invalid response format'))
}

export default instance
