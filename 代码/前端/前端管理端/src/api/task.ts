import http from './request'
import type { AdminTaskListResponse, AdminTaskStatusDetail } from '@/types/core'

export default {
  getAllTasks(params?: { organization?: string }) {
    return http.get<AdminTaskListResponse>('/get_all_user_tasks/', { params })
  },

  getDetectionTaskStatus(taskId: number, params?: { organization?: string }) {
    return http.get<AdminTaskStatusDetail>(`/get_detection_task_status/${taskId}/`, { params })
  },
}
