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
