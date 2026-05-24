//引入axios
import axios from 'axios'
import router from '@/router'

/** 未配置或无效时使用相对路径 `/api`，走 Vite 代理到本机 Django */
function getApiOrigin(): string {
  const raw = import.meta.env.VITE_API_URL as string | undefined
  const t = typeof raw === 'string' ? raw.trim() : ''
  if (!t || t === 'undefined' || t === 'null') return ''
  return t.replace(/\/$/, '')
}

const apiOrigin = getApiOrigin()
const baseApiUrl = apiOrigin ? `${apiOrigin}/api` : '/api'

/** 这些路径绝不能附带旧 JWT，否则 JWTAuthentication 会先 401，登录体根本执行不到 */
const NO_AUTH_HEADER_PATHS = [
  '/login/',
  '/register/',
  '/admin-login/',
  '/password-reset/',
  '/password-reset/confirm/',
  '/token/refresh/',
  '/logout/',
]

function isNoAuthHeaderPath(url: string | undefined): boolean {
  if (!url) return false
  return NO_AUTH_HEADER_PATHS.some((p) => url.includes(p))
}

// 创建axios实例
const instance = axios.create({
    baseURL: baseApiUrl,
    timeout: 5000,
    headers: {},
})
 
//请求拦截处理 
instance.interceptors.request.use(config=>{
    const path = config.url || ''
    if (isNoAuthHeaderPath(path)) {
        delete config.headers.Authorization
    } else {
        const token = localStorage.getItem('1-token')
        if (token) {
            config.headers['Authorization'] = 'Bearer ' + token
        }
    }
    return config
},
    error=>{
        return Promise.reject(error)
    }
)
 
//相应拦截处理：登录/登出/注册等返回的 401 不得走刷新令牌，否则会误刷新并整页跳转
instance.interceptors.response.use(response=>{
    return response
},
 error=>{
    const status = error.response?.status
    const cfg = error.config as { url?: string; headers?: Record<string, string>; _retry?: boolean } | undefined
    const path = cfg?.url || ''

    if (!cfg || status !== 401 || isNoAuthHeaderPath(path) || cfg._retry) {
        return Promise.reject(error)
    }

    return refreshToken().then(newToken => {
        cfg._retry = true
        cfg.headers = cfg.headers || {}
        cfg.headers['Authorization'] = 'Bearer ' + newToken
        return instance(cfg)
    }).catch(err => {
        localStorage.removeItem('1-token')
        localStorage.removeItem('1-refresh')
        localStorage.setItem('1-isLoggedIn', 'false')
        router.push('/login')
        return Promise.reject(err)
    })
  }
)

// 刷新token的函数
const refreshToken = async () => {
    const refresh = localStorage.getItem('1-refresh')
    if (!refresh) {
        return Promise.reject(new Error('No refresh token available'))
    }
    
    const refreshUrl = apiOrigin ? `${apiOrigin}/api/token/refresh/` : '/api/token/refresh/'
    const response = await axios.post(refreshUrl, { refresh })
        
    if (response.data?.access) {
        localStorage.setItem('1-token', response.data.access)
        return response.data.access
    }
    return Promise.reject(new Error('Invalid response format'))
}
 
//导出axios
export default instance
