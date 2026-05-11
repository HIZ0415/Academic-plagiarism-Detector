import http from './request'
import { mockAigcFeaturesEnabled } from '@/utils/mockMode'

const mockReviewTaskStartedAt = new Map<string, number>()
const MOCK_REVIEW_WARM_MS = 2600

function registerMockReviewTask(taskId: string | number) {
  if (!mockAigcFeaturesEnabled()) return
  const k = String(taskId)
  if (!mockReviewTaskStartedAt.has(k)) mockReviewTaskStartedAt.set(k, Date.now())
}

function mockReviewTaskStatus(taskId: string | number): ReviewDetectionStatus {
  const k = String(taskId)
  if (!mockReviewTaskStartedAt.has(k)) {
    return { task_id: taskId, status: 'completed', progress: 100 }
  }
  const elapsed = Date.now() - mockReviewTaskStartedAt.get(k)!
  if (elapsed < MOCK_REVIEW_WARM_MS) {
    return {
      task_id: taskId,
      status: 'in_progress',
      progress: Math.min(95, 10 + Math.floor((elapsed / MOCK_REVIEW_WARM_MS) * 85)),
    }
  }
  return { task_id: taskId, status: 'completed', progress: 100 }
}

export interface ReviewDetectionStatus {
  task_id: number | string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  progress?: number
  error_message?: string
}

export interface ReviewSuspiciousSegment {
  segment_index: number
  issue_type: string
  risk_score: number
  risk_level: 'low' | 'medium' | 'high'
  excerpt: string
  basic_explanation?: string
}

export interface ReviewDetectionResult {
  task_id: number | string
  overall_risk_level?: 'low' | 'medium' | 'high'
  overall_risk_score?: number
  summary?: string
  ai_tendency?: {
    score?: number
    risk_level?: 'low' | 'medium' | 'high'
    suspicious?: boolean
  }
  template_tendency?: {
    score?: number
    risk_level?: 'low' | 'medium' | 'high'
    suspicious?: boolean
  }
  suspicious_segments?: ReviewSuspiciousSegment[]
  basic_explanation?: string[]
}

/** API 文档 §16.2：在线文本或 .txt 文件，二者择一提交 */
export function submitReviewDetection(params: {
  task_name: string
  text?: string
  file?: File
}) {
  const fd = new FormData()
  fd.append('task_name', params.task_name.trim())
  if (params.file) {
    fd.append('file', params.file)
  } else if (params.text != null) {
    fd.append('text', params.text)
  }
  if (mockAigcFeaturesEnabled()) {
    const tid = `mock-rev-${Date.now()}`
    registerMockReviewTask(tid)
    return Promise.resolve({
      data: {
        task_id: tid,
        status: 'pending',
        cleaned_text_length: params.file ? params.file.size : (params.text?.length ?? 0),
        message: 'Mock：未调用真实 /review/submit/',
      },
      headers: {},
    } as any)
  }
  return http.post('/review/submit/', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getReviewDetectionStatus(taskId: number | string) {
  if (mockAigcFeaturesEnabled()) {
    return Promise.resolve({
      data: mockReviewTaskStatus(taskId),
    })
  }
  return http.get<ReviewDetectionStatus>(`/review/tasks/${taskId}/status/`)
}

export function getReviewDetectionResult(taskId: number | string) {
  if (mockAigcFeaturesEnabled()) {
    return Promise.resolve({
      data: {
        task_id: taskId,
        overall_risk_level: 'medium',
        overall_risk_score: 0.55,
        summary: 'Mock：Review 文本存在模板化与生成痕迹的联合风险占位。',
        ai_tendency: { score: 0.52, risk_level: 'medium', suspicious: true },
        template_tendency: { score: 0.48, risk_level: 'medium', suspicious: false },
        suspicious_segments: [
          {
            segment_index: 1,
            issue_type: 'ai_tendency',
            risk_score: 0.71,
            risk_level: 'high',
            excerpt: 'Mock 异常片段：句式高度规整，建议人工复核。',
            basic_explanation: '与相邻段落风格差异较大。',
          },
        ],
        basic_explanation: ['Mock 解释条目一', 'Mock 解释条目二'],
      } as ReviewDetectionResult,
    })
  }
  return http.get<ReviewDetectionResult>(`/review/tasks/${taskId}/result/`)
}
