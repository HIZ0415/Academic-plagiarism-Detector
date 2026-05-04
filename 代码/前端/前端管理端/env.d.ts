/// <reference types="vite/client" />
/// <reference types="unplugin-vue-router/client" />
/// <reference types="vite-plugin-vue-layouts/client" />
interface ImportMetaEnv {
  readonly VITE_API_URL: string    // 你的自定义环境变量
  /** 与用户端同 KEY：为 true 时人工审核审批走 shared Mock（须与用户端同 origin 才共享数据） */
  readonly VITE_USE_MOCK_MANUAL_REVIEW_WORKFLOW?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}