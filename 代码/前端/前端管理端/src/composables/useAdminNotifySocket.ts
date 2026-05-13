import { ref, onUnmounted } from 'vue'
import { buildNotificationsWebSocketUrl } from '@shared/notificationsWsUrl'

/**
 * 连接 /ws/notifications/，在收到推送时触发回调（用于任务列表等与通知相关的刷新）。
 * 与用户端共用同一 NotificationConsumer，使用管理端 JWT（localStorage `1-token`）。
 */
export function useAdminNotifySocket(onEvent: () => void) {
  const connected = ref(false)
  const statusText = ref('未连接')
  let ws: WebSocket | null = null
  let debounceTimer: number | null = null
  let reconnectTimer: number | null = null
  let shouldReconnect = true
  let retryCount = 0

  function scheduleCb() {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = window.setTimeout(() => {
      debounceTimer = null
      onEvent()
    }, 350)
  }

  function clearReconnectTimer() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  function scheduleReconnect() {
    if (!shouldReconnect) return
    clearReconnectTimer()
    retryCount += 1
    const delay = Math.min(15000, 1000 * 2 ** Math.min(retryCount - 1, 4))
    statusText.value = `重连中（${Math.round(delay / 1000)}s）`
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null
      connect()
    }, delay)
  }

  function connect() {
    const token = localStorage.getItem('1-token')
    if (!token) {
      connected.value = false
      statusText.value = '缺少登录凭证'
      return
    }

    const url = buildNotificationsWebSocketUrl(token)

    clearReconnectTimer()
    if (ws) {
      ws.onclose = null
      ws.onerror = null
      ws.close()
      ws = null
    }
    connected.value = false
    statusText.value = retryCount > 0 ? '正在重连' : '连接中'

    try {
      ws = new WebSocket(url)
      ws.onopen = () => {
        connected.value = true
        statusText.value = '已连接'
        retryCount = 0
      }
      ws.onclose = () => {
        connected.value = false
        if (shouldReconnect) {
          statusText.value = '连接已断开'
          scheduleReconnect()
        } else {
          statusText.value = '未连接'
        }
      }
      ws.onmessage = (e) => {
        if (e.data === 'ok') return
        scheduleCb()
      }
      ws.onerror = () => {
        connected.value = false
        statusText.value = '连接异常'
      }
    } catch {
      connected.value = false
      statusText.value = '连接失败'
      scheduleReconnect()
    }
  }

  function disconnect() {
    shouldReconnect = false
    clearReconnectTimer()
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
    if (ws) {
      ws.onclose = null
      ws.onerror = null
      ws.close()
      ws = null
    }
    connected.value = false
    statusText.value = '未连接'
  }

  function reconnect() {
    shouldReconnect = true
    retryCount = 0
    connect()
  }

  onUnmounted(() => {
    disconnect()
  })

  return { connected, statusText, connect: reconnect, disconnect, reconnect }
}
