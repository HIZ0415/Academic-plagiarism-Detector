import http from './request'
import { fullFrontendMockEnabled } from '@/utils/mockMode'

const mockUnread = () => Promise.resolve({ data: { not_read: 0 } })
const mockList = () =>
  Promise.resolve({
    data: {
      notifications: [
        {
          id: 1,
          user_id: '0',
          user_name: '系统',
          category: 'SYSTEM',
          title: '全栈 Mock 模式',
          content: '当前为 **VITE_USE_FULL_FRONTEND_MOCK**，通知走本地桩数据。',
          status: 'read',
          url: '',
          notified_at: new Date().toISOString().slice(0, 19).replace('T', ' '),
          expanded: false,
        },
      ],
    },
  })

export default {
  getUnRead() {
    if (fullFrontendMockEnabled()) return mockUnread()
    return http.get('/notification/notify/')
  },

  setReadAll() {
    if (fullFrontendMockEnabled()) return Promise.resolve({ data: { ok: true } })
    return http.post('/notification/set_as_read/')
  },

  setSingleRead(data: any) {
    if (fullFrontendMockEnabled()) return Promise.resolve({ data: { ok: true } })
    return http.post(`/notification/set_as_read/${data.notification_id}/`)
  },

  getAllNotifications() {
    if (fullFrontendMockEnabled()) return mockList()
    return http.get('/notification/get/')
  },
}
