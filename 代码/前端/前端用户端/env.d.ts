/// <reference types="vite/client" />
/// <reference types="unplugin-vue-router/client" />
/// <reference types="vite-plugin-vue-layouts/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  /** 可选：通知 WebSocket 完整地址（默认由 VITE_API_URL 推导，或通过 Vite 代理 /ws） */
  readonly VITE_WS_URL?: string
  readonly VITE_USE_MOCK_AIGC?: string
  /** 为 true 时使用 shared/manualReviewWorkflowMock（无后端联调人工审核全流程） */
  readonly VITE_USE_MOCK_MANUAL_REVIEW_WORKFLOW?: string
  /**
   * 为 true 时启用用户端「全栈 Mock」：本地假登录 JWT、通知/上传/检测等接口走前端桩，
   * 并等价开启人工审核 workflow Mock（与 VITE_USE_MOCK_MANUAL_REVIEW_WORKFLOW 叠加效果一致）。
   */
  readonly VITE_USE_FULL_FRONTEND_MOCK?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}