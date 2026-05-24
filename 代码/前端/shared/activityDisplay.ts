/** 个人主页「最近活动」展示文案 */

const TASK_TYPE_LABELS: Record<string, string> = {
  image_detection: '图像检测',
  paper_aigc: '论文 AIGC',
  resource_check: '资源规范性',
  review_detection: 'Review 检测',
}

export function formatDisplayTaskId(id?: string | number | null) {
  const raw = String(id ?? '').trim()
  if (!raw) return ''
  const digits = raw.replace(/\D/g, '')
  if (digits) return `DT-${digits.slice(-6).padStart(6, '0')}`
  return raw
}

/** 去掉批量提交时写入 task_name 的 batch-时间戳-随机串- 前缀 */
export function stripBatchTaskNamePrefix(name: string) {
  const trimmed = name.trim()
  if (!trimmed) return ''
  const matched = trimmed.match(/^batch-\d+-[a-z0-9]+-(.+)$/i)
  return matched ? matched[1] : trimmed
}

export function taskTypeLabel(taskType?: string | null) {
  if (!taskType) return ''
  return TASK_TYPE_LABELS[taskType] || taskType
}

export function formatActivityTitle(raw: Record<string, unknown>, role: 'publisher' | 'reviewer') {
  const taskType = typeof raw.task_type === 'string' ? raw.task_type : ''
  const typeLabel =
    taskTypeLabel(taskType) ||
    (role === 'reviewer' ? '人工审核' : '学术检测')

  const rawName = [raw.task_name, raw.title, raw.operation_type]
    .find((v) => typeof v === 'string' && String(v).trim()) as string | undefined
  const shortName = rawName ? stripBatchTaskNamePrefix(rawName) : ''

  if (shortName && shortName.length >= 2 && shortName !== typeLabel) {
    return `${typeLabel} · ${shortName}`
  }
  return typeLabel
}

export function formatActivitySubtitle(raw: Record<string, unknown>) {
  const taskId = raw.task_id ?? raw.id ?? raw.manual_review_id
  const formatted = formatDisplayTaskId(taskId as string | number | undefined)
  if (formatted) return `任务编号 ${formatted}`
  return ''
}

export function activityStatusLabel(status?: string) {
  switch (status) {
    case 'completed':
      return '已完成'
    case 'pending':
      return '排队中'
    case 'in_progress':
      return '进行中'
    case 'failed':
      return '失败'
    default:
      return '未知'
  }
}
