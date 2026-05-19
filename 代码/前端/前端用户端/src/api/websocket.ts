import { useMessageStore } from '@/stores/message'
import { buildNotificationsWebSocketUrl } from '@shared/notificationsWsUrl.ts'

let ws: WebSocket | null = null
let reconnectTimer: number | null = null
let shouldReconnect = true
let reconnectAttempts = 0
const MAX_RECONNECT_ATTEMPTS = 5
let wsDisabledHintLogged = false

interface WebSocketMessage {
  [key: string]: unknown
}

function logWsUnavailableOnce() {
  if (wsDisabledHintLogged) return
  wsDisabledHintLogged = true
  console.info(
    '[通知] WebSocket 暂不可用（常见原因：未安装 daphne 或未重启 Django）。' +
      '未读通知仍可通过 HTTP 轮询获取；本地联调可在后端目录执行：pip install daphne 后重启 runserver。',
  )
}

const websocket = {
  Init(): void {
    if (!('WebSocket' in window)) {
      console.log('您的浏览器不支持 WebSocket')
      return
    }

    shouldReconnect = true
    if (ws) {
      try {
        ws.close()
      } catch {
        /* ignore */
      }
      ws = null
    }

    const token = localStorage.getItem('2-token')
    const url = buildNotificationsWebSocketUrl(token)
    ws = new WebSocket(url)

    ws.onopen = () => {
      reconnectAttempts = 0
      wsDisabledHintLogged = false
      console.log('✅ WebSocket 连接成功')
    }

    ws.onerror = () => {
      // 详细错误由 onclose 统一处理，避免刷屏
    }

    ws.onclose = (e) => {
      if (e.code === 1000 && shouldReconnect === false) return
      scheduleReconnect()
    }

    ws.onmessage = function (e) {
      const raw = e.data
      if (raw === 'ok') return
      try {
        const msg = JSON.parse(raw) as { message?: string }
        if (msg.message) useMessageStore().addNotification(msg.message)
      } catch (err) {
        console.error('WebSocket 消息解析失败:', err)
      }
    }
  },

  Close(): Promise<void> {
    return new Promise((resolve) => {
      shouldReconnect = false
      reconnectAttempts = MAX_RECONNECT_ATTEMPTS
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
      if (ws) {
        ws.close()
      }
      resolve()
    })
  },

  Send(data: WebSocketMessage): void {
    const message = JSON.stringify(data)
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(message)
    }
  },

  getWebSocket(): WebSocket | null {
    return ws
  },
}

function scheduleReconnect() {
  if (!shouldReconnect) return
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    logWsUnavailableOnce()
    return
  }
  reconnectAttempts += 1
  if (reconnectTimer) clearTimeout(reconnectTimer)
  reconnectTimer = window.setTimeout(() => {
    websocket.Init()
  }, 4000)
}

const entries = performance.getEntriesByType('navigation')
if (
  entries.length > 0 &&
  (entries[0] as PerformanceNavigationTiming).type === 'reload' &&
  window.location.pathname !== '/login'
) {
  websocket.Init()
}

export default websocket
