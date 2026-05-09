/**
 * 纯前端联调总开关（见文档《前后端对接-总览》§3.5、§6）。
 * 开启后：认证走本地假 JWT；AIGC/图像/通知等与 VITE_USE_MOCK_AIGC 等价能力一并启用；
 * 人工审核仍由 shared 中 workflowMockEnabled()（含本开关）控制。
 */
export function fullFrontendMockEnabled(): boolean {
  return import.meta.env.VITE_USE_FULL_FRONTEND_MOCK === 'true'
}

/** 论文 Mock、统一上传页 Mock、历史列表兜底等与 VITE_USE_MOCK_AIGC 合并判断 */
export function mockAigcFeaturesEnabled(): boolean {
  return import.meta.env.VITE_USE_MOCK_AIGC === 'true' || fullFrontendMockEnabled()
}

export const MOCK_FULL_SESSION_KEY = '2-mock-full'
export const MOCK_PROFILE_STORAGE_KEY = '2-mock-profile'
