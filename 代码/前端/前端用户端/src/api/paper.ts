import http from './request'
import type { PaperAigcResult, ResourceCheckResult, TaskStatus } from '@/types/core'
import { mockAigcFeaturesEnabled } from '@/utils/mockMode'

const mockOk = <T>(data: T) => Promise.resolve({ data, headers: {} } as any)

/** Mock 下模拟异步：提交后若干毫秒内 status 为 in_progress，便于轮询联调 */
const mockPaperTaskStartedAt = new Map<string, number>()
const MOCK_PAPER_WARM_MS = 2800

function registerMockPaperTask(taskId: string | number) {
  if (!mockAigcFeaturesEnabled()) return
  const k = String(taskId)
  if (!mockPaperTaskStartedAt.has(k)) mockPaperTaskStartedAt.set(k, Date.now())
}

function mockPaperTaskStatus(taskId: string | number): { status: TaskStatus; progress: number } {
  const k = String(taskId)
  if (!mockPaperTaskStartedAt.has(k)) {
    return { status: 'completed', progress: 100 }
  }
  const elapsed = Date.now() - mockPaperTaskStartedAt.get(k)!
  if (elapsed < MOCK_PAPER_WARM_MS) {
    return {
      status: 'in_progress',
      progress: Math.min(95, 12 + Math.floor((elapsed / MOCK_PAPER_WARM_MS) * 82)),
    }
  }
  return { status: 'completed', progress: 100 }
}

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

function mockPaperFileId(): number {
  return Math.floor(Date.now() / 1000) % 800000 + 100000
}

export default {
  uploadPaper(formData: FormData) {
    if (mockAigcFeaturesEnabled()) {
      return mockOk({
        paper_file_id: mockPaperFileId(),
        paragraph_count: 42,
        file_name: 'mock-upload.pdf',
        upload_time: new Date().toISOString().slice(0, 19).replace('T', ' '),
      })
    }
    return http.post('/paper/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  submitAigcTask(data: SubmitTaskPayload) {
    if (mockAigcFeaturesEnabled()) {
      const tid = `mock-paper-${Date.now()}`
      registerMockPaperTask(tid)
      return mockOk({ task_id: tid, status: 'pending' as TaskStatus })
    }
    return http.post('/paper/aigc/submit/', data)
  },

  getTaskStatus(taskId: number | string) {
    if (mockAigcFeaturesEnabled()) {
      const st = mockPaperTaskStatus(taskId)
      return mockOk({
        task_id: taskId,
        status: st.status as TaskStatus,
        progress: st.progress,
      })
    }
    return http.get(`/paper/tasks/${taskId}/status/`)
  },

  getAigcResult(taskId: number | string) {
    if (mockAigcFeaturesEnabled()) {
      const body: PaperAigcResult = {
        task_id: taskId,
        overall_risk_level: 'medium',
        ai_contribution_ratio: 0.43,
        summary: 'Mock：中等 AIGC 风险，联调占位数据。',
        paragraphs: [
          { index: 2, risk_score: 0.78, risk_level: 'high', excerpt: 'Mock 高风险段落示例。' },
          { index: 5, risk_score: 0.59, risk_level: 'medium', excerpt: 'Mock 中风险段落示例。' },
        ],
      }
      return mockOk(body)
    }
    return http.get<PaperAigcResult>(`/paper/aigc/${taskId}/result/`)
  },

  submitResourceCheck(data: SubmitTaskPayload) {
    if (mockAigcFeaturesEnabled()) {
      const tid = `mock-res-${Date.now()}`
      registerMockPaperTask(tid)
      return mockOk({ task_id: tid, status: 'pending' as TaskStatus })
    }
    return http.post('/paper/resource-check/submit/', data)
  },

  getResourceResult(taskId: number | string) {
    if (mockAigcFeaturesEnabled()) {
      const body: ResourceCheckResult = {
        task_id: taskId,
        total_references: 40,
        doi_found_count: 35,
        doi_invalid_count: 2,
        suspected_risk_count: 2,
        summary: 'Mock：参考文献规范性抽检占位。',
        issues: [
          {
            reference_index: 3,
            issue_type: 'doi_invalid',
            detail: 'DOI 格式疑似无效。',
            severity: 'high',
          },
          {
            reference_index: 8,
            issue_type: 'citation_incomplete',
            detail: '引用信息不完整。',
            severity: 'medium',
          },
        ],
      }
      return mockOk(body)
    }
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

