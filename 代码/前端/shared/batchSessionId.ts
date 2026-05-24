/** 统一检测批次编号：生成与展示 */

export function newBatchSessionId(): string {
  return `batch-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export type BatchSessionLabel = {
  short: string
  full: string
  hasBatch: boolean
}

function formatTimestampLabel(ts: number, suffix: string): string | null {
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return null
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${mm}-${dd} ${hh}:${mi} · ${suffix}`
}

/** 列表/卡片用短标签；完整编号放 tooltip 或详情 */
export function formatBatchSessionLabel(id?: string | null): BatchSessionLabel {
  const full = String(id ?? '').trim()
  if (!full) {
    return { short: '单独任务', full: '', hasBatch: false }
  }

  const standard = full.match(/^batch-(\d{10,})-([a-z0-9]+)$/i)
  if (standard) {
    const label = formatTimestampLabel(Number(standard[1]), standard[2].slice(0, 6))
    if (label) return { short: label, full, hasBatch: true }
  }

  const auto = full.match(/^auto-batch-(\d+)$/i)
  if (auto) {
    const raw = auto[1]
    const ts = raw.length <= 10 ? Number(raw) * 1000 : Number(raw)
    const label = formatTimestampLabel(ts, 'auto')
    if (label) return { short: label, full, hasBatch: true }
  }

  if (full.length > 22) {
    return { short: `${full.slice(0, 10)}…${full.slice(-8)}`, full, hasBatch: true }
  }
  return { short: full, full, hasBatch: true }
}
