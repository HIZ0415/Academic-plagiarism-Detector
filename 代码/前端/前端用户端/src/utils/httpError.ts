import axios from 'axios'

export type PaperFlowError = Error & {
  stage?: 'upload' | 'submit'
  paper_file_id?: number
  task_id?: number | string
}

export function asPaperFlowError(err: unknown): PaperFlowError | null {
  if (err instanceof Error && ('stage' in err || 'paper_file_id' in err || 'task_id' in err)) {
    return err as PaperFlowError
  }
  return null
}

/** 将 axios / 网络错误转为用户可读中文，避免直接展示 "timeout of 15000ms exceeded" */
export function formatHttpError(err: unknown, context?: string): string {
  const prefix = context ? `${context}：` : ''

  if (axios.isAxiosError(err)) {
    const timeoutMs = err.config?.timeout
    const isTimeout =
      err.code === 'ECONNABORTED' || /timeout.*exceeded/i.test(err.message || '')

    if (isTimeout) {
      const sec = timeoutMs ? Math.round(timeoutMs / 1000) : 15
      return (
        `${prefix}请求超时（已等待约 ${sec} 秒）。` +
        '大体积 PDF 解析或 AI 检测耗时较长，请稍后重试；若持续失败，请确认后端与 AI 服务已启动。'
      )
    }

    if (!err.response) {
      return `${prefix}无法连接后端，请确认 Django 服务已启动且代理/接口地址正确。`
    }

    const data = err.response.data as { detail?: string; message?: string; error_message?: string; task_id?: number | string } | string
    if (typeof data === 'string' && data.trim()) return `${prefix}${data}`
    if (data && typeof data === 'object') {
      const detail = data.detail || data.message || data.error_message
      if (detail) return `${prefix}${detail}`
      if (data.task_id != null) {
        return `${prefix}任务已创建（ID: ${data.task_id}），但后续步骤失败，可在历史中查看或点击「同步状态」。`
      }
    }
    return `${prefix}请求失败（HTTP ${err.response.status}）。`
  }

  if (err instanceof Error && err.message) return `${prefix}${err.message}`
  return `${prefix}操作失败，请稍后重试。`
}

export function throwPaperFlowError(
  err: unknown,
  extra: Pick<PaperFlowError, 'stage' | 'paper_file_id' | 'task_id'>,
): never {
  const base: PaperFlowError =
    err instanceof Error ? (err as PaperFlowError) : (new Error(String(err)) as PaperFlowError)
  base.stage = extra.stage
  if (extra.paper_file_id != null) base.paper_file_id = extra.paper_file_id
  if (extra.task_id != null) base.task_id = extra.task_id
  throw base
}
