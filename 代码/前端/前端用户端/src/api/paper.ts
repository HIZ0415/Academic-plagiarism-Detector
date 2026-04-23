import http from './request'
import type { PaperAigcResult, ResourceCheckResult, TaskStatus } from '@/types/core'

export interface PaperUploadResponse {
  paper_file_id: number
  file_name?: string
  upload_time?: string
}

export interface SubmitTaskPayload {
  paper_file_id: number
  task_name: string
}

export interface SubmitTaskResponse {
  task_id: number | string
  status?: string
}

export interface PaperTaskStatus {
  task_id?: number | string
  status: TaskStatus
  progress?: number
  error_message?: string
}

export interface ResourceIssuePayload {
  reference_index: number
  issue_type: string
  detail: string
  severity?: 'low' | 'medium' | 'high'
}

export default {
  uploadPaper(formData: FormData) {
    return http.post('/paper/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  submitAigcTask(data: SubmitTaskPayload) {
    return http.post('/paper/aigc/submit/', data)
  },

  getTaskStatus(taskId: number | string) {
    return http.get(`/paper/tasks/${taskId}/status/`)
  },

  getAigcResult(taskId: number | string) {
    return http.get<PaperAigcResult>(`/paper/aigc/${taskId}/result/`)
  },

  submitResourceCheck(data: SubmitTaskPayload) {
    return http.post('/paper/resource-check/submit/', data)
  },

  getResourceResult(taskId: number | string) {
    return http.get<ResourceCheckResult>(`/paper/resource-check/${taskId}/result/`)
  },

  async uploadAndSubmitAigcTask(file: File, taskName: string) {
    const formData = new FormData()
    formData.append('file', file)
    const uploadRes = await this.uploadPaper(formData)
    const paperFileId = uploadRes.data.paper_file_id
    return this.submitAigcTask({
      paper_file_id: paperFileId,
      task_name: taskName,
    })
  },

  async uploadAndSubmitResourceTask(file: File, taskName: string) {
    const formData = new FormData()
    formData.append('file', file)
    const uploadRes = await this.uploadPaper(formData)
    const paperFileId = uploadRes.data.paper_file_id
    return this.submitResourceCheck({
      paper_file_id: paperFileId,
      task_name: taskName,
    })
  },
}

