/**
 * 通知 WebSocket 与 Django Channels 路由 `ws/notifications/` 对齐（见 `fake_image_detector/routings.py`）。
 * 用户端与管理端共用。
 */
export function buildNotificationsWebSocketUrl(token: string | null): string {
  const explicit = (import.meta.env.VITE_WS_URL as string | undefined)?.trim()
  if (explicit && explicit !== 'undefined' && explicit !== 'null') {
    let u = explicit.replace(/\/$/, '')
    if (token) {
      u += `${u.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`
    }
    return u
  }

  const raw = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
  if (raw && raw !== 'undefined' && raw !== 'null') {
    try {
      const u = new URL(raw.startsWith('http') ? raw : `http://${raw}`)
      const wsProto = u.protocol === 'https:' ? 'wss:' : 'ws:'
      const tq = token ? `?token=${encodeURIComponent(token)}` : ''
      return `${wsProto}//${u.host}/ws/notifications/${tq}`
    } catch {
      /* fallthrough */
    }
  }

  if (typeof window !== 'undefined' && window.location?.host) {
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const tq = token ? `?token=${encodeURIComponent(token)}` : ''
    return `${wsProto}//${window.location.host}/ws/notifications/${tq}`
  }

  const tq = token ? `?token=${encodeURIComponent(token)}` : ''
  return `ws://127.0.0.1:8000/ws/notifications/${tq}`
}
