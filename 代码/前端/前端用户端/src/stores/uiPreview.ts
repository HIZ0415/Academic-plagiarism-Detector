import { defineStore } from 'pinia'

export type PreviewRole = 'publisher' | 'reviewer'

/** 无后端联调时：仅本地 UI 预览，不发送真实登录请求 */
export const useUiPreviewStore = defineStore('uiPreview', {
  state: () => ({
    enabled: typeof localStorage !== 'undefined' && localStorage.getItem('2-ui-preview') === '1',
    role: ((typeof localStorage !== 'undefined' && localStorage.getItem('2-preview-role')) ||
      'publisher') as PreviewRole,
  }),
  actions: {
    enable(role: PreviewRole) {
      this.enabled = true
      this.role = role
      localStorage.setItem('2-ui-preview', '1')
      localStorage.setItem('2-preview-role', role)
    },
    disable() {
      this.enabled = false
      localStorage.removeItem('2-ui-preview')
      localStorage.removeItem('2-preview-role')
    },
    setRole(role: PreviewRole) {
      this.role = role
      if (this.enabled) localStorage.setItem('2-preview-role', role)
    },
  },
})
