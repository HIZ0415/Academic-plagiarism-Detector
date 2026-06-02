/** 与 `request.ts` 一致：未配置时使用相对路径，避免生产包打入本机地址 */
function mediaOrigin(): string {
  const raw = import.meta.env.VITE_API_URL as string | undefined
  const t = typeof raw === 'string' ? raw.trim() : ''
  if (t && t !== 'undefined' && t !== 'null') return t.replace(/\/$/, '')
  return ''
}

/** 将后端返回的相对媒体路径转为可请求的绝对 URL（与 axios 的 `/api` 前缀无关） */
export function resolveBackendMediaUrl(path: string | null | undefined): string {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  const base = mediaOrigin()
  const p = path.startsWith('/') ? path : `/${path}`
  return base ? `${base}${p}` : p
}
