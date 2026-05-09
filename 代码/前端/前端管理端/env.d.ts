/// <reference types="vite/client" />
/// <reference types="unplugin-vue-router/client" />
/// <reference types="vite-plugin-vue-layouts/client" />
interface ImportMetaEnv {
  readonly VITE_API_URL: string    // 你的自定义环境变量
  readonly VITE_WS_URL?: string
  /** 与用户端同 KEY：为 true 时人工审核审批走 shared Mock（须与用户端同 origin 才共享数据） */
  readonly VITE_USE_MOCK_MANUAL_REVIEW_WORKFLOW?: string
  /** 与用户端同 KEY：shared/workflow 中 workflowMockEnabled() 会识别，便于与用户端同源全栈 Mock */
  readonly VITE_USE_FULL_FRONTEND_MOCK?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}