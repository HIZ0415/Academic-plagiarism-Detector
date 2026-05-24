/** 与 `request.ts` 一致：未配置 VITE_API_URL 时媒体走 Vite `/media` 代理 */
function mediaOrigin(): string {
  const raw = import.meta.env.VITE_API_URL as string | undefined
  const t = typeof raw === 'string' ? raw.trim() : ''
  if (t && t !== 'undefined' && t !== 'null') return t.replace(/\/$/, '')
  return ''
}

/** 将后端返回的相对媒体路径转为可请求的 URL */
export function resolveBackendMediaUrl(path: string | null | undefined): string {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  const base = mediaOrigin()
  const p = path.startsWith('/') ? path : `/${path}`
  return base ? `${base}${p}` : p
}
