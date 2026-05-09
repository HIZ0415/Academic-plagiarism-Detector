import http from './request'

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

/** 需求 FR-PLJC-0001 / API 文档 §16.2：在线文本或 .txt 文件，二者择一提交 */
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
  return http.post('/review/submit/', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getReviewDetectionStatus(taskId: number | string) {
  return http.get<ReviewDetectionStatus>(`/review/tasks/${taskId}/status/`)
}

export function getReviewDetectionResult(taskId: number | string) {
  return http.get<ReviewDetectionResult>(`/review/tasks/${taskId}/result/`)
}
