/**
 * 人工审核全流程 · 前端 Mock（localStorage）
 * 用户端与管理端通过 Vite alias `@workflow-mock` 共用本文件。
 * 注意：不同 dev 端口 origin 不同，localStorage 不共享；无后端全链路演示请在用户端 /annual 使用「模拟管理端审批」。
 */

export type WorkflowTaskType =
  | 'image_detection'
  | 'paper_aigc'
  | 'resource_check'
  | 'review_detection'
  | string

export interface CreateManualReviewPayload {
  detection_task_id: string
  task_type: WorkflowTaskType
  reason: string
  priority?: 'normal' | 'urgent'
  batch_session_id?: string
  /** 当前登录用户名（展示用） */
  publisher_username?: string
}

export interface WorkflowRecord {
  review_request_id: number
  detection_task_id: string
  task_type: WorkflowTaskType
  reason: string
  priority: 'normal' | 'urgent'
  batch_session_id?: string
  created_at: string
  publisher_username: string
  admin_state: 'pending' | 'refused' | 'accepted'
  admin_reject_reason?: string
  manual_review_id?: number
  manual_review_status: 'undo' | 'completed'
  manual_review_time?: string
}

interface Store {
  records: WorkflowRecord[]
  nextReviewRequestId: number
  nextManualReviewId: number
}

const STORAGE_KEY = 'apd_manual_review_workflow_v1'

export function workflowMockEnabled(): boolean {
  return (
    import.meta.env.VITE_USE_MOCK_MANUAL_REVIEW_WORKFLOW === 'true' ||
    import.meta.env.VITE_USE_FULL_FRONTEND_MOCK === 'true'
  )
}

function load(): Store {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { records: [], nextReviewRequestId: 10001, nextManualReviewId: 50001 }
    const p = JSON.parse(raw) as Store
    return {
      records: Array.isArray(p.records) ? p.records : [],
      nextReviewRequestId: Number(p.nextReviewRequestId) || 10001,
      nextManualReviewId: Number(p.nextManualReviewId) || 50001,
    }
  } catch {
    return { records: [], nextReviewRequestId: 10001, nextManualReviewId: 50001 }
  }
}

function save(st: Store) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(st))
}

function findByReviewRequestId(st: Store, id: number) {
  return st.records.find((r) => r.review_request_id === id)
}

function findByManualReviewId(st: Store, id: number) {
  return st.records.find((r) => r.manual_review_id === id)
}

export function mockCreate(payload: CreateManualReviewPayload) {
  const st = load()
  const id = st.nextReviewRequestId++
  const rec: WorkflowRecord = {
    review_request_id: id,
    detection_task_id: String(payload.detection_task_id).trim(),
    task_type: payload.task_type,
    reason: String(payload.reason).trim(),
    priority: payload.priority === 'urgent' ? 'urgent' : 'normal',
    batch_session_id: payload.batch_session_id?.trim() || undefined,
    created_at: new Date().toISOString(),
    publisher_username: payload.publisher_username?.trim() || 'publisher',
    admin_state: 'pending',
    manual_review_status: 'undo',
  }
  st.records.unshift(rec)
  save(st)
  return {
    review_request_id: id,
    status: 'pending_admin',
    message: '已提交人工审核申请，等待管理端审批',
  }
}

export function mockSimulateAdminApprove(review_request_id: number) {
  const st = load()
  const r = findByReviewRequestId(st, review_request_id)
  if (!r || r.admin_state !== 'pending') return { ok: false as const, error: '记录不存在或已处理' }
  r.admin_state = 'accepted'
  r.manual_review_id = st.nextManualReviewId++
  save(st)
  return { ok: true as const, manual_review_id: r.manual_review_id }
}

export function mockSimulateAdminReject(review_request_id: number, reason: string) {
  const st = load()
  const r = findByReviewRequestId(st, review_request_id)
  if (!r || r.admin_state !== 'pending') return { ok: false as const, error: '记录不存在或已处理' }
  r.admin_state = 'refused'
  r.admin_reject_reason = reason
  save(st)
  return { ok: true as const }
}

/** 管理端 handle_reviewRequest：choice 1=通过 0=拒绝 */
export function mockAdminHandle(review_request_id: number, choice: number, reason: string) {
  if (choice === 1) return mockSimulateAdminApprove(review_request_id)
  return mockSimulateAdminReject(review_request_id, reason || '未填写理由')
}

export function mockSubmitExpert(manual_review_id: number) {
  const st = load()
  const r = findByManualReviewId(st, manual_review_id)
  if (!r) return { ok: false as const, error: '任务不存在' }
  r.manual_review_status = 'completed'
  r.manual_review_time = new Date().toISOString().slice(0, 19).replace('T', ' ')
  save(st)
  return { ok: true as const }
}

export function mockListPublisher(params: {
  page?: number
  page_size?: number
  status?: string
}) {
  const st = load()
  let rows = [...st.records]
  const statusFilter = params.status
  if (statusFilter === 'pending') rows = rows.filter((r) => r.admin_state === 'pending')
  else if (statusFilter === 'in_progress')
    rows = rows.filter((r) => r.admin_state === 'accepted' && r.manual_review_status === 'undo')
  else if (statusFilter === 'completed')
    rows = rows.filter((r) => r.admin_state === 'accepted' && r.manual_review_status === 'completed')
  else if (statusFilter === 'failed') rows = rows.filter((r) => r.admin_state === 'refused')

  const page = Math.max(1, Number(params.page) || 1)
  const pageSize = Math.max(1, Number(params.page_size) || 10)
  const total = rows.length
  const total_pages = Math.max(1, Math.ceil(total / pageSize))
  const slice = rows.slice((page - 1) * pageSize, page * pageSize)

  const tasks = slice.map((r) => {
    let status = 'pending'
    let progress = '0/1'
    if (r.admin_state === 'refused') {
      status = 'failed'
      progress = '0/1'
    } else if (r.admin_state === 'pending') {
      status = 'pending'
      progress = '0/1'
    } else if (r.manual_review_status === 'completed') {
      status = 'completed'
      progress = '1/1'
    } else {
      status = 'in_progress'
      progress = '0/1'
    }
    return {
      review_request_id: r.review_request_id,
      request_time: r.created_at.slice(0, 19).replace('T', ' '),
      status,
      progress,
      detection_task_id: r.detection_task_id,
      task_type: r.task_type,
      admin_state: r.admin_state,
      manual_review_status: r.manual_review_status,
    }
  })

  return {
    tasks,
    current_page: page,
    total_pages,
    total_count: total,
  }
}

function normTaskKind(t: WorkflowTaskType): string {
  const s = String(t)
  if (s.includes('paper')) return 'paper'
  if (s.includes('review')) return 'review'
  return 'image'
}

export function mockReviewerTaskList(params: Record<string, string | number>) {
  const st = load()
  let rows = st.records.filter((r) => r.admin_state === 'accepted' && r.manual_review_id != null)

  const q = String(params.query || '').trim().toLowerCase()
  if (q) rows = rows.filter((r) => r.publisher_username.toLowerCase().includes(q))

  const page = Math.max(1, Number(params.page) || 1)
  const pageSize = Math.max(1, Number(params.page_size) || 10)
  const total = rows.length
  const total_pages = Math.max(1, Math.ceil(total / pageSize))
  const slice = rows.slice((page - 1) * pageSize, page * pageSize)

  const results = slice.map((r) => ({
    manual_review_id: r.manual_review_id!,
    manual_review_time: r.manual_review_time || r.created_at.slice(0, 19).replace('T', ' '),
    publisher_username: r.publisher_username,
    publisher_avatar: null as string | null,
    image_count: normTaskKind(r.task_type) === 'image' ? 3 : normTaskKind(r.task_type) === 'paper' ? 12 : 1,
    status: r.manual_review_status,
    review_request_id: r.review_request_id,
    review_request_status:
      r.admin_state === 'accepted'
        ? r.manual_review_status === 'completed'
          ? 'done'
          : 'assigned'
        : 'pending',
    admin_gate_status: r.admin_state === 'accepted' ? 'passed' : r.admin_state === 'refused' ? 'rejected' : 'pending',
    task_kind: normTaskKind(r.task_type),
    paper_unit_count: normTaskKind(r.task_type) === 'paper' ? 12 : undefined,
    review_text_units: normTaskKind(r.task_type) === 'review' ? 800 : undefined,
  }))

  return {
    results,
    current_page: page,
    total_pages,
    total_count: total,
  }
}

export function mockGetReviewDetail(manual_review_id: number) {
  const st = load()
  const r = findByManualReviewId(st, manual_review_id)
  if (!r) throw new Error('NOT_FOUND')
  const kind = normTaskKind(r.task_type)
  const base: Record<string, unknown> = {
    task_kind: kind === 'paper' ? 'paper' : kind === 'review' ? 'review' : 'image',
    manual_review_status: r.manual_review_status,
    review_request: {
      id: r.review_request_id,
      detection_task_id: r.detection_task_id,
      reason: r.reason,
      priority: r.priority,
    },
    ai_detection_result: {
      overall_fake_probability: 0.62,
      summary: 'Mock：用于本地联调的 AI 摘要占位。',
    },
  }
  if (kind === 'image') {
    const rid = r.manual_review_id ?? manual_review_id
    base.imgs = [
      { id: rid * 10 + 1, url: `https://picsum.photos/seed/apd${rid}a/640/480` },
      { id: rid * 10 + 2, url: `https://picsum.photos/seed/apd${rid}b/640/480` },
    ]
  } else if (kind === 'paper') {
    base.segments = [
      { id: 's1', title: '摘要', content: 'Mock 论文片段：请在联调时替换为后端结构化段落。' },
      { id: 's2', title: '引言', content: 'Mock 论文片段二。' },
    ]
    base.text_units = base.segments
  } else {
    base.text_units = [
      { id: 'u1', title: 'Review 正文', content: 'Mock 评审文本：请在联调时替换为后端正文。' },
    ]
  }
  return base
}

export function mockGetByDetectionTask(detection_task_id: string) {
  const st = load()
  const id = String(detection_task_id).trim()
  const r = st.records.find((x) => x.detection_task_id === id)
  if (!r) {
    return {
      found: false as const,
      detection_task_id: id,
    }
  }
  return {
    found: true as const,
    review_request_id: r.review_request_id,
    detection_task_id: r.detection_task_id,
    task_type: r.task_type,
    admin_state: r.admin_state,
    manual_review_id: r.manual_review_id,
    manual_review_status: r.manual_review_status,
    admin_reject_reason: r.admin_reject_reason,
    created_at: r.created_at,
  }
}

export function mockPublisherResultSummary(review_request_id: number) {
  const st = load()
  const r = findByReviewRequestId(st, review_request_id)
  if (!r) throw new Error('NOT_FOUND')
  return {
    review_request_id: r.review_request_id,
    detection_task_id: r.detection_task_id,
    task_type: r.task_type,
    admin_state: r.admin_state,
    manual_review_status: r.manual_review_status,
    manual_review_id: r.manual_review_id,
    summary: {
      reviewerCount: r.manual_review_status === 'completed' ? 1 : 0,
      suspiciousImageCount: normTaskKind(r.task_type) === 'image' ? 1 : 0,
      finalDecision:
        r.admin_state === 'refused'
          ? '管理端已拒绝申请'
          : r.manual_review_status !== 'completed'
            ? '专家审核未完成'
            : 'Mock：已完成人工复核（演示数据）',
    },
    reviewerRows:
      r.manual_review_status === 'completed'
        ? [
            {
              reviewer: '审稿人（Mock）',
              decision: '已出具结论',
              confidence: 85,
              comment: '本地 Mock：后端接入后将替换为真实汇总。',
            },
          ]
        : [],
    imageRows:
      normTaskKind(r.task_type) === 'image'
        ? [
            { imageId: 'IMG-01', aiResult: '疑似异常', manualResult: '已复核', riskLevel: '中', note: 'Mock 行' },
          ]
        : [],
  }
}

/** 管理端列表行（兼容 reviews.vue） */
export function mockAdminReviewRequestList(params: Record<string, unknown>) {
  const st = load()
  let rows = [...st.records]
  const status = String(params.status || '')
  if (status === 'pending') rows = rows.filter((r) => r.admin_state === 'pending')
  else if (status === 'refused') rows = rows.filter((r) => r.admin_state === 'refused')
  else if (status === 'accepted') rows = rows.filter((r) => r.admin_state === 'accepted')

  const page = Math.max(1, Number(params.page) || 1)
  const pageSize = Math.max(1, Number(params.page_size) || 10)
  const total = rows.length
  const total_pages = Math.max(1, Math.ceil(total / pageSize))
  const slice = rows.slice((page - 1) * pageSize, page * pageSize)

  const requests = slice.map((r) => ({
    id: r.review_request_id,
    username: r.publisher_username,
    avatar: '',
    state: r.admin_state === 'pending' ? 'pending' : r.admin_state === 'refused' ? 'refused' : 'accepted',
    file_type: r.task_type,
    time: r.created_at.slice(0, 19).replace('T', ' '),
    detection_task_id: r.detection_task_id,
    task_type: r.task_type,
    reason: r.reason,
    priority: r.priority,
  }))

  return {
    requests,
    current_page: page,
    total_pages,
    total_requests: total,
  }
}

export function mockAdminReviewRequestDetail(id: number) {
  const st = load()
  const r = findByReviewRequestId(st, id)
  if (!r) throw new Error('NOT_FOUND')
  const imgs =
    normTaskKind(r.task_type) === 'image'
      ? [
          { id: 1, url: `https://picsum.photos/seed/adreq${id}/400/300` },
        ]
      : []
  return {
    imgs,
    persons: [{ id: 9001, username: '待分配专家（Mock）', avatar: '' }],
    reason: r.reason,
    detection_task_id: r.detection_task_id,
    task_type: r.task_type,
    priority: r.priority,
  }
}

/** annual 页展示待审批列表 */
export function mockListPendingAdminForPublisher() {
  const st = load()
  return st.records.filter((r) => r.admin_state === 'pending')
}
