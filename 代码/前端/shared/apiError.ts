/** 从 axios / fetch 错误中提取可读说明，供用户端与管理端共用 */

type AxiosLikeError = {
  code?: string
  message?: string
  response?: {
    status?: number
    data?: Record<string, unknown>
  }
}

function readResponseMessage(data: Record<string, unknown> | undefined): string | null {
  if (!data || typeof data !== 'object') return null
  const detail = data.detail
  const message = data.message
  const errorMessage = data.error_message
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && typeof detail[0] === 'string') return detail[0]
  if (typeof message === 'string' && message.trim()) return message
  if (typeof errorMessage === 'string' && errorMessage.trim()) return errorMessage
  return null
}

/** 将检测配额类英文后端提示转为中文（submit_detection2 等） */
export function humanizeDetectionQuotaMessage(message: string): string {
  const trimmed = message.trim()
  if (!trimmed) return message

  const nonLlm = trimmed.match(
    /non-LLM method usage limit.*?only submit (\d+) more images/i,
  )
  if (nonLlm) {
    return `本周标准检测（非 LLM）配额不足：本组织还可提交 ${nonLlm[1]} 张图。请减少 ZIP/批量中的图片数量、分批提交，或联系组织管理员充值。`
  }

  const llm = trimmed.match(/LLM method usage limit.*?only submit (\d+) more images/i)
  if (llm) {
    return `本周精准检测（LLM）配额不足：本组织还可提交 ${llm[1]} 张图。请减少图片数量、改用标准模式，或联系组织管理员充值。`
  }

  return message
}

export function formatImageQuotaExceeded(
  mode: 'fast' | 'precise',
  remaining: number,
  requested: number,
): string {
  const modeLabel = mode === 'precise' ? '精准模式（LLM）' : '标准模式'
  return (
    `${modeLabel}配额不足：本组织本周还可检测 ${remaining} 张图，` +
    `本次解压/选中 ${requested} 张。请减少 ZIP 内图片或 PDF 页图、分批提交，或联系组织管理员充值。`
  )
}

export function extractApiError(err: unknown, fallback = '请求失败，请稍后重试'): string {
  const ax = err as AxiosLikeError
  const fromBody = readResponseMessage(ax.response?.data)
  if (fromBody) return humanizeDetectionQuotaMessage(fromBody)

  const status = ax.response?.status
  if (status === 403) {
    return '无权限：请确认账号已加入组织且具备上传/提交检测权限。'
  }
  if (status === 401) {
    return '登录已失效，请重新登录后再试。'
  }
  if (status != null && status >= 500) {
    return `服务器错误（HTTP ${status}），请查看 Django 日志或稍后重试。`
  }
  if (status != null) {
    return `请求被拒绝（HTTP ${status}）。`
  }

  if (ax.code === 'ECONNABORTED') {
    return (
      '请求超时：上传解压、图像提交或 PDF/AI 检测耗时较长，请稍后重试。' +
      '图像/ZIP 批量提交需 AI 服务（8010）；论文 AIGC 亦需 Django（8000）与 AI 均已启动。'
    )
  }
  if (ax.code === 'ERR_NETWORK' || ax.message === 'Network Error') {
    return '无法连接后端：请确认 Django 已启动（http://127.0.0.1:8000）；论文 AIGC 检测还需 AI 服务（http://127.0.0.1:8010）。查看 `.local-dev/logs/django.stderr.log` 排查崩溃。'
  }

  if (typeof ax.message === 'string' && ax.message.trim()) {
    return ax.message
  }
  return fallback
}
