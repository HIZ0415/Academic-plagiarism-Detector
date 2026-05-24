/** 论文 PDF 上传 + 服务端预处理（文本提取、段落切分） */
export function paperUploadTimeoutMs(fileSizeBytes: number): number {
  const scaled = Math.ceil(fileSizeBytes / 1024 / 5) * 1000
  return Math.min(900_000, Math.max(120_000, scaled))
}

/**
 * 论文检测提交：resource_check 主要为本地规则；paper_aigc 在后端同步调用 AI 网关。
 * 前端超时应不小于常见 AI_SERVICE_TIMEOUT（默认 1200s），此处上限 20 分钟。
 */
export function paperSubmitTimeoutMs(fileSizeBytes: number, kind: 'aigc' | 'resource'): number {
  if (kind === 'resource') {
    const scaled = Math.ceil(fileSizeBytes / 1024 / 20) * 1000
    return Math.min(300_000, Math.max(120_000, scaled))
  }
  const uploadBased = paperUploadTimeoutMs(fileSizeBytes)
  return Math.min(1_200_000, Math.max(300_000, uploadBased * 2))
}

/** 解压后分页拉取 image_id 列表（每页默认 100 条） */
export function imageExtractListTimeoutMs(): number {
  return 120_000
}

/**
 * 图像/ZIP 批量提交检测（POST /detection/submit/）。
 * 本地 CELERY_TASK_ALWAYS_EAGER 时后端可能同步等待 AI；生产环境通常仅入队。
 */
export function imageSubmitTimeoutMs(imageCount: number): number {
  const perImageMs = 45_000
  const scaled = Math.max(180_000, imageCount * perImageMs)
  return Math.min(1_200_000, scaled)
}
