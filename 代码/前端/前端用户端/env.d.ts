/// <reference types="vite/client" />
/// <reference types="unplugin-vue-router/client" />
/// <reference types="vite-plugin-vue-layouts/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_USE_MOCK_AIGC?: string
  /** 为 true 时使用 shared/manualReviewWorkflowMock（无后端联调人工审核全流程） */
  readonly VITE_USE_MOCK_MANUAL_REVIEW_WORKFLOW?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}