import { ref, onUnmounted } from 'vue'

/**
 * 连接 /ws/notifications/，在收到推送时触发回调（用于任务列表等与通知相关的刷新）。
 * 与用户端共用同一 NotificationConsumer，使用管理端 JWT（localStorage `1-token`）。
 */
export function useAdminNotifySocket(onEvent: () => void) {
  const connected = ref(false)
  let ws: WebSocket | null = null
  let debounceTimer: number | null = null

  function buildWsUrl(): string | null {
    const base = import.meta.env.VITE_API_URL
    if (!base) return null
    const wsBase = base.replace(/^http/, 'ws').replace(/\/$/, '')
    return `${wsBase}/ws/notifications/`
  }

  function scheduleCb() {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = window.setTimeout(() => {
      debounceTimer = null
      onEvent()
    }, 350)
  }

  function connect() {
    const token = localStorage.getItem('1-token')
    const url = buildWsUrl()
    if (!url || !token) return

    disconnect()

    try {
      ws = new WebSocket(`${url}?token=${encodeURIComponent(token)}`)
      ws.onopen = () => {
        connected.value = true
      }
      ws.onclose = () => {
        connected.value = false
      }
      ws.onmessage = (e) => {
        if (e.data === 'ok') return
        scheduleCb()
      }
      ws.onerror = () => {
        connected.value = false
      }
    } catch {
      connected.value = false
    }
  }

  function disconnect() {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
    connected.value = false
  }

  onUnmounted(disconnect)

  return { connected, connect, disconnect }
}
