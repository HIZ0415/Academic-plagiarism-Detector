export type AdminType = 'software_admin' | 'organization_admin'

export interface AdminUserInfo {
  id: number
  username: string
  email: string
  role: string
  admin_type?: AdminType
  organization?: number
  organization_name?: string
  avatar?: string
}

export interface UserListItem {
  id: number
  username: string
  email: string
  role: string
  permission: string
  date_joined: string
  avatar?: string
  admin_type?: AdminType
  organization?: string
}

export interface UserListResponse {
  users: UserListItem[]
  current_page: number
  total_pages: number
  total_users: number
}

export interface ManagedFileItem {
  id: number
  username: string
  organization?: string
  tag: string
  upload_time: string
  file_url?: string
  ai_checked?: boolean
  manually_checked?: boolean
  result?: boolean | null
}

export interface ManagedFileListResponse {
  files: ManagedFileItem[]
  current_page: number
  total_pages: number
  total_files: number
}

export interface DashboardPoint {
  date: string
  value: number
}

export interface ActionLogItem {
  id: number
  user: string
  organization?: string
  operation_type: string
  related_model: string
  related_id: number
  operation_time: string
}

export interface ActionLogListResponse {
  logs: ActionLogItem[]
  current_page: number
  total_pages: number
  total_logs: number
}

/** 与后端 DetectionTask.task_type 对齐 */
export type AdminTaskType =
  | 'image_detection'
  | 'paper_aigc'
  | 'resource_check'
  | 'review_detection'

/** 后端未升级时可能缺少 task_type / username 等字段，见 `文档/前后端对接-管理端.md` §2.1 */
export interface AdminTaskItem {
  task_id: number
  task_name: string
  task_type?: AdminTaskType | string
  status: string
  upload_time: string
  completion_time: string | null
  organization: string | null
  user_id?: number
  username?: string | null
  error_message?: string
}

export interface AdminTaskListResponse {
  tasks: AdminTaskItem[]
}

/** GET /api/get_detection_task_status/:id/ */
export interface AdminTaskStatusDetail {
  task_id: number
  task_name: string
  status: string
  upload_time: string
  completion_time: string | null
  organization: string | null
  detection_results?: Array<{
    image_id: number
    status: string
    is_fake: boolean
    confidence_score: number | null
    detection_time: string | null
  }>
}

export interface AdminDashboardTaskStats {
  total_tasks: number
  completed_tasks: number
  pending_tasks: number
  in_progress_tasks: number
}

export interface AdminDashboardResponse {
  users: Array<{ id: number; username: string; email: string; role: string; date_joined: string }>
  task_stats: AdminDashboardTaskStats
}

