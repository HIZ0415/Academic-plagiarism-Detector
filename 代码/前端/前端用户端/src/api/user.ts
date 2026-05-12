import http from './request'
import { ref } from 'vue'
import {
  fullFrontendMockEnabled,
  MOCK_FULL_SESSION_KEY,
  MOCK_PROFILE_STORAGE_KEY,
} from '@/utils/mockMode'

// 使用ref直接管理登录状态
export const isLoggedIn = ref(localStorage.getItem("2-isLoggedIn") === "true")

function readMockProfile(): Record<string, unknown> {
  try {
    const raw = localStorage.getItem(MOCK_PROFILE_STORAGE_KEY)
    if (!raw) {
      return {
        id: 90001,
        username: 'mock_user',
        email: 'mock@local.dev',
        role: 'publisher',
        profile: '',
        avatar: '',
        organization: 1,
        organization_name: '联调演示组织',
      }
    }
    return JSON.parse(raw) as Record<string, unknown>
  } catch {
    return {
      id: 90001,
      username: 'mock_user',
      email: 'mock@local.dev',
      role: 'publisher',
      profile: '',
      avatar: '',
      organization: 1,
      organization_name: '联调演示组织',
    }
  }
}

function persistMockProfile(p: Record<string, unknown>) {
  localStorage.setItem(MOCK_PROFILE_STORAGE_KEY, JSON.stringify(p))
}

export default {
  login(data: any) {
    if (fullFrontendMockEnabled()) {
      const email = String(data?.email ?? 'mock@local.dev').trim().toLowerCase()
      const role = data?.role === 'reviewer' ? 'reviewer' : 'publisher'
      const username = email.includes('@') ? email.split('@')[0] : 'mock_user'
      localStorage.setItem(MOCK_FULL_SESSION_KEY, '1')
      persistMockProfile({
        id: role === 'reviewer' ? 90002 : 90001,
        username,
        email,
        role,
        profile: '本地全栈 Mock 联调账号（无后端）',
        avatar: '',
        organization: 1,
        organization_name: '联调演示组织',
      })
      return Promise.resolve({
        data: {
          access: 'mock-jwt-access-token',
          refresh: 'mock-jwt-refresh-token',
        },
      }).then((res) => {
        isLoggedIn.value = true
        localStorage.setItem("2-isLoggedIn", "true")
        return res
      })
    }
    return http.post('/login/', data).then(res => {
      localStorage.removeItem(MOCK_FULL_SESSION_KEY)
      localStorage.removeItem(MOCK_PROFILE_STORAGE_KEY)
      isLoggedIn.value = true
      localStorage.setItem("2-isLoggedIn", "true")
      return res
    })
  },
  register(data: any) {
    if (fullFrontendMockEnabled()) {
      return Promise.resolve({
        data: { message: 'Mock：已模拟注册成功', username: data?.username, email: data?.email },
      })
    }
    return http.post('/register/', data)
  },
  logout(data: any) {
    if (fullFrontendMockEnabled()) {
      localStorage.removeItem(MOCK_FULL_SESSION_KEY)
      localStorage.removeItem(MOCK_PROFILE_STORAGE_KEY)
      isLoggedIn.value = false
      return Promise.resolve({ data: {} })
    }
    return http.post('/logout/', data).then(res => {
      isLoggedIn.value = false
      return res
    })
  },
  getUserInfo() {
    if (fullFrontendMockEnabled()) {
      return Promise.resolve({ data: readMockProfile() })
    }
    return http.get('/user/details/');
  },
  updateUserInfo(data: any) {
    if (fullFrontendMockEnabled()) {
      const cur = readMockProfile()
      const next = { ...cur, ...data }
      persistMockProfile(next)
      return Promise.resolve({ data: next })
    }
    return http.put('/user/update/', data)
  },
  updateUserAvatar(data: any) {
    if (fullFrontendMockEnabled()) {
      const cur = readMockProfile()
      const next = { ...cur, avatar: '/media/avatars/default.png' }
      persistMockProfile(next)
      return Promise.resolve({ data: { avatar: next.avatar } })
    }
    return http.put('/user/avatar/', data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

  },
  // 请求重置密码邮件
  requestPasswordReset(email: string) {
    if (fullFrontendMockEnabled()) {
      return Promise.resolve({ data: { message: 'Mock：验证码已生成（任意 6 位数字可通过校验）' } })
    }
    return http.post('/password-reset/', { email })
  },
  // 确认重置密码
  confirmPasswordReset(data: { email: string, reset_code: string, new_password: string }) {
    if (fullFrontendMockEnabled()) {
      return Promise.resolve({ data: { message: 'Mock：密码已重置' } })
    }
    return http.post('/password-reset/confirm/', data)
  },

  createOrganization(data: any) {
    if (fullFrontendMockEnabled()) {
      return Promise.resolve({ data: { message: 'Mock：组织申请已提交', id: 80001 } })
    }
    return http.post('/organization/create/', data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }
}
