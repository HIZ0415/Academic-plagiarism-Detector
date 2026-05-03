export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed'

export interface UserProfile {
  id: number
  username: string
  role: 'publisher' | 'reviewer' | 'admin' | string
  organization_id?: number | null
  avatar?: string
}

export interface AcademicResourceFile {
  paper_file_id: number
  file_name: string
  file_type: string
  file_size: number
  upload_time: string
}

export interface DetectionTask {
  task_id: number | string
  task_name: string
  task_type: 'paper_aigc' | 'resource_check' | 'image_detection' | string
  status: TaskStatus
  upload_time?: string
  completion_time?: string | null
  error_message?: string
}

export interface AigcParagraphResult {
  index: number
  risk_score: number
  risk_level: 'low' | 'medium' | 'high'
  excerpt: string
}

export interface PaperAigcResult {
  task_id: number | string
  overall_risk_level?: 'low' | 'medium' | 'high'
  ai_contribution_ratio: number
  summary: string
  paragraphs: AigcParagraphResult[]
}

export interface ResourceIssue {
  reference_index: number
  issue_type: string
  detail: string
  severity?: 'low' | 'medium' | 'high'
}

export interface ResourceCheckResult {
  task_id: number | string
  total_references: number
  doi_found_count: number
  doi_invalid_count: number
  suspected_risk_count: number
  summary: string
  issues: ResourceIssue[]
}

export interface ManualReviewTask {
  manual_review_id: number
  task_id?: number | string
  status: 'undo' | 'completed' | string
  publisher_username?: string
  image_count?: number
  manual_review_time?: string
}

export interface NotificationItem {
  notification_id: number
  title: string
  content: string
  is_read: boolean
  created_at: string
}

export interface ActivityLogItem {
  id: number
  action: string
  created_at: string
  operator_id?: number
}
