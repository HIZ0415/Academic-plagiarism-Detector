<template>
  <v-container class="py-4 detection-hub">
    <v-row class="mb-2" align="center">
      <v-col cols="12" md="8">
        <div class="text-h4 font-weight-bold mb-1">学术检测</div>
        <div class="text-body-2 text-medium-emphasis">
          图像、论文 PDF、Review 文本等检测均在本页完成：通过下方标签切换<strong>批量提交</strong>、<strong>论文工作台</strong>与 <strong>Review 结果</strong>。
        </div>
      </v-col>
      <v-col cols="12" md="4" class="d-flex justify-end">
        <v-chip :color="USE_MOCK ? 'warning' : 'success'" variant="tonal">
          {{ USE_MOCK ? 'Mock 模式' : '后端模式' }}
        </v-chip>
      </v-col>
    </v-row>

    <v-tabs v-model="section" color="primary" class="mb-4" density="comfortable">
      <v-tab value="submit" class="text-none">批量提交</v-tab>
      <v-tab value="paper" class="text-none">论文检测</v-tab>
      <v-tab value="review" class="text-none">Review 检测</v-tab>
    </v-tabs>

    <v-window v-model="section" class="detection-hub-window">
      <v-window-item value="submit">
    <v-alert v-if="route.query.task_id" type="info" variant="tonal" density="compact" class="mb-4 text-body-2">
      正在基于历史任务（编号 {{ route.query.task_id }}）发起再次检测。旧任务结果请回到检测历史点击「查看报告」；本页只用于重新选择文件或粘贴 Review 后创建新检测。
    </v-alert>

    <v-alert type="info" variant="tonal" density="compact" class="mb-4 text-body-2">
      <strong>格式说明：</strong>论文检测仅 <strong>.pdf</strong>（不支持 DOCX）；Review 为下方文本框或 <strong>.txt</strong>；<strong>ZIP/RAR</strong> 将自动解压并抽取图像送检。
    </v-alert>

    <v-card class="pa-4" variant="outlined">
      <v-row class="mb-2">
        <v-col cols="12">
          <div class="text-subtitle-2 font-weight-medium mb-2">本批检测模式</div>
          <v-btn-toggle v-model="detectionMode" mandatory divided color="primary" density="comfortable" :disabled="running">
            <v-btn value="fast" class="text-none">标准模式</v-btn>
            <v-btn value="precise" class="text-none">精准模式</v-btn>
          </v-btn-toggle>
          <p class="text-caption text-medium-emphasis mt-2 mb-0">
            <strong>标准模式</strong>：常规检测，速度更快、配额占用较低；
            <strong>精准模式</strong>：启用更强推理（含 LLM 辅助，图像检测尤甚）。个人主页可设置默认模式。
          </p>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">
          <v-file-input
            v-model="files"
            multiple
            show-size
            counter
            prepend-icon="mdi-paperclip"
            label="选择文件（图像、PDF 论文、TXT Review、ZIP/RAR 等，可与下方 Review 文本同批）"
            accept="image/*,.pdf,.txt,.zip,.rar"
            :disabled="running"
          />
        </v-col>
      </v-row>

      <v-row class="mt-2">
        <v-col cols="12">
          <div class="text-subtitle-2 font-weight-medium mb-2">Review（可选，与文件同批）</div>
          <v-textarea
            v-model="reviewPasteText"
            label="在线粘贴 Review 文本（与 .txt 二选一即可；若同时上传 .txt，则二者都会作为独立子任务进入队列）"
            rows="4"
            variant="outlined"
            density="comfortable"
            hide-details="auto"
            :disabled="running"
            class="text-body-2"
          />
        </v-col>
      </v-row>

      <v-row class="mt-2">
        <v-col cols="12" class="d-flex flex-wrap gap-3">
          <v-btn
            color="primary"
            prepend-icon="mdi-play"
            :loading="running"
            :disabled="!files.length && !reviewPasteText.trim()"
            @click="start"
          >
            开始本批检测
          </v-btn>
          <v-btn variant="outlined" prepend-icon="mdi-refresh" :disabled="running" @click="reset">
            重置表单
          </v-btn>
          <v-btn
            v-if="batchSessionId && rows.length"
            color="secondary"
            variant="tonal"
            prepend-icon="mdi-history"
            :to="{ path: '/history', query: { batch_session_id: batchSessionId } }"
          >
            在检测历史中查看本批次
          </v-btn>
          <v-btn
            v-if="batchSessionId && rows.length"
            color="secondary"
            variant="tonal"
            prepend-icon="mdi-clipboard-text-outline"
            :to="{ path: '/comprehensive-report', query: { batch_session_id: batchSessionId } }"
          >
            查看鉴伪报告
          </v-btn>
        </v-col>
      </v-row>
    </v-card>

    <v-card v-if="batchSummary" class="mt-6" variant="tonal" color="primary">
      <v-card-title class="text-subtitle-1 font-weight-bold">本批次综合摘要</v-card-title>
      <v-card-text class="text-body-2">
        <div class="mb-2">
          <strong>批次编号：</strong>{{ batchSummary.id }}
        </div>
        <div class="mb-2">
          本批共 <strong>{{ batchSummary.total }}</strong> 个子任务：图像 {{ batchSummary.counts.image }}，
          论文 PDF {{ batchSummary.counts.paper }}，Review {{ batchSummary.counts.review }}，
          其他 {{ batchSummary.counts.unknown }}。
        </div>
        <div class="text-medium-emphasis">
          同一批次编号会关联本批各子任务，便于在检测历史、鉴伪报告中按批查看，以及发起人工审核时引用整批上下文。
        </div>
      </v-card-text>
    </v-card>

    <v-card v-if="rows.length" class="mt-6" variant="outlined">
      <v-card-title class="text-subtitle-1 font-weight-bold">任务队列（本批）</v-card-title>
      <v-divider />
      <v-card-text>
        <v-data-table :headers="headers" :items="rows" item-key="id" hide-default-footer>
          <template #item.batchSessionId="{ item }">
            <span class="text-caption font-mono">{{ shortBatch(item.batchSessionId) }}</span>
          </template>

          <template #item.type="{ item }">
            <v-chip size="small" variant="tonal" :color="typeColor(item.type)">
              {{ typeLabel(item.type) }}
            </v-chip>
          </template>

          <template #item.progress="{ item }">
            <v-progress-linear :model-value="item.progress" height="18" rounded>
              <template #default>
                <span class="text-caption">{{ item.progress }}%</span>
              </template>
            </v-progress-linear>
          </template>

          <template #item.status="{ item }">
            <v-chip size="small" variant="tonal" :color="statusColor(item.status)">
              {{ statusLabel(item.status) }}
            </v-chip>
          </template>

          <template #item.errorHint="{ item }">
            <span v-if="item.error" class="text-caption text-error">{{ item.error }}</span>
            <span v-else class="text-caption text-medium-emphasis">—</span>
          </template>

          <template #item.actions="{ item }">
            <v-btn
              v-if="item.taskId"
              size="small"
              variant="text"
              color="primary"
              @click="openResult(item)"
            >
              查看
            </v-btn>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>
      </v-window-item>

      <v-window-item value="paper">
        <PaperDetectWorkbench v-if="section === 'paper'" embedded />
      </v-window-item>

      <v-window-item value="review">
        <ReviewDetectWorkbench v-if="section === 'review'" embedded />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import PaperDetectWorkbench from '@/pages/detect/paper.vue'
import ReviewDetectWorkbench from '@/pages/detect/review.vue'
import { useRoute, useRouter } from 'vue-router'
import { useSnackbarStore } from '@/stores/snackbar'
import paperApi from '@/api/paper'
import publisherApi from '@/api/publisher'
import uploadApi from '@/api/upload'
import { submitReviewDetection } from '@/api/reviewDetection'
import { mockAigcFeaturesEnabled } from '@/utils/mockMode'
import { useDetectionMode } from '@/composables/useDetectionMode'

type ResourceType = 'image' | 'paper' | 'review' | 'archive' | 'docx' | 'unknown'
type RowStatus = 'pending' | 'running' | 'completed' | 'failed'

type QueueRow = {
  id: string
  file: File
  name: string
  size: number
  type: ResourceType
  status: RowStatus
  progress: number
  batchSessionId: string
  taskId?: string
  error?: string
  /** 与 file 二选一语义：粘贴文本走 /review/submit/ 的 text 字段 */
  pastedReviewText?: string
}

type LocalTaskRecord = {
  task_id: string
  task_type: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  progress: number
  upload_time: string
  completion_time: string
  source: 'local'
  batch_session_id?: string
}

const USE_MOCK = mockAigcFeaturesEnabled()
const { mode: detectionMode, modePayload: detectionModePayload, imageSubmitMode } = useDetectionMode()

type HubSection = 'submit' | 'paper' | 'review'

const route = useRoute()
const router = useRouter()

const section = ref<HubSection>('submit')

function parseSection(raw: unknown): HubSection {
  const s = (Array.isArray(raw) ? raw[0] : raw)?.toString()
  if (s === 'paper' || s === 'review' || s === 'submit') return s
  return 'submit'
}

watch(
  () => route.query.section,
  (s) => {
    section.value = parseSection(s)
  },
  { immediate: true },
)

watch(section, (s) => {
  if (parseSection(route.query.section) === s) return
  const query: Record<string, string | string[] | undefined> = { ...route.query }
  if (s === 'submit') {
    delete query.section
    delete query.paper_tab
  } else {
    query.section = s
    if (s !== 'paper') delete query.paper_tab
  }
  router.replace({ path: '/upload', query })
})
const snackbar = useSnackbarStore()

const files = ref<File[]>([])
const reviewPasteText = ref('')
const running = ref(false)
const batchSessionId = ref('')

const headers = [
  { title: '批次', key: 'batchSessionId', align: 'center' as const, width: 120 },
  { title: '文件名', key: 'name', align: 'start' as const },
  { title: '类型', key: 'type', align: 'center' as const, width: 120 },
  { title: '进度', key: 'progress', align: 'center' as const, width: 220 },
  { title: '状态', key: 'status', align: 'center' as const, width: 140 },
  { title: '失败原因', key: 'errorHint', align: 'start' as const, minWidth: '200px' },
  { title: '操作', key: 'actions', align: 'center' as const, sortable: false, width: 100 },
] as const

/** 从 axios / 后端响应取出可读说明，便于编辑模式下自助排查 */
function axiosDetail(err: unknown): string {
  const ax = err as {
    response?: { data?: Record<string, unknown>; status?: number }
    message?: string
  }
  const d = ax.response?.data
  if (d && typeof d === 'object') {
    const detail = d.detail
    const message = d.message
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && typeof detail[0] === 'string') return detail[0]
    if (typeof message === 'string') return message
  }
  if (ax.response?.status === 403) {
    return '无提交权限：请确认账号已加入组织且具备检测提交权限。'
  }
  return typeof ax.message === 'string' ? ax.message : '请求失败，请打开 F12 → Network 查看接口返回'
}

const rows = ref<QueueRow[]>([])

const batchSummary = computed(() => {
  const id = batchSessionId.value
  if (!id || !rows.value.length) return null
  const counts = { image: 0, paper: 0, review: 0, unknown: 0 }
  for (const r of rows.value) {
    counts[r.type]++
  }
  return { id, counts, total: rows.value.length }
})

function shortBatch(id: string) {
  if (!id) return '—'
  return id.length > 14 ? `${id.slice(0, 8)}…${id.slice(-6)}` : id
}

function detectType(file: File): ResourceType {
  const name = file.name.toLowerCase()
  if (file.type.startsWith('image/')) return 'image'
  if (name.endsWith('.txt')) return 'review'
  if (name.endsWith('.pdf')) return 'paper'
  if (name.endsWith('.docx')) return 'docx'
  if (name.endsWith('.zip') || name.endsWith('.rar')) return 'archive'
  return 'unknown'
}

function typeLabel(t: ResourceType) {
  switch (t) {
    case 'image':
      return '图像'
    case 'paper':
      return '论文 PDF'
    case 'review':
      return 'Review'
    case 'archive':
      return '压缩包（抽图）'
    case 'docx':
      return 'DOCX（需转 PDF）'
    default:
      return '未知'
  }
}

function typeColor(t: ResourceType) {
  switch (t) {
    case 'image':
      return 'indigo'
    case 'paper':
      return 'teal'
    case 'review':
      return 'deep-purple'
    case 'archive':
      return 'orange'
    case 'docx':
      return 'amber'
    default:
      return 'grey'
  }
}

function statusLabel(s: RowStatus) {
  switch (s) {
    case 'pending':
      return '待开始'
    case 'running':
      return '进行中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
  }
}

function statusColor(s: RowStatus) {
  switch (s) {
    case 'pending':
      return 'grey'
    case 'running':
      return 'info'
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
  }
}

function reset() {
  files.value = []
  reviewPasteText.value = ''
  rows.value = []
  running.value = false
  batchSessionId.value = ''
}

function toTaskType(t: ResourceType) {
  if (t === 'paper') return 'paper_aigc'
  if (t === 'image' || t === 'archive') return 'image_detection'
  if (t === 'review') return 'review_detection'
  return 'unknown'
}

function nowString() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  const s = String(d.getSeconds()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${mi}:${s}`
}

function newBatchId() {
  return `batch-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function saveLocalTasks(rowsToSave: QueueRow[]) {
  try {
    const key = 'local_detection_tasks'
    const existing = JSON.parse(localStorage.getItem(key) || '[]') as LocalTaskRecord[]
    const mapped: LocalTaskRecord[] = rowsToSave
      .filter((r) => !!r.taskId)
      .map((r) => ({
        task_id: String(r.taskId),
        task_type: toTaskType(r.type),
        status: r.status === 'running' ? 'in_progress' : r.status,
        progress: r.progress,
        upload_time: nowString(),
        completion_time: r.status === 'completed' ? nowString() : '',
        source: 'local',
        batch_session_id: r.batchSessionId,
      }))
    localStorage.setItem(key, JSON.stringify([...mapped, ...existing].slice(0, 200)))
  } catch {
    // ignore
  }
}

async function mockRun(row: QueueRow) {
  row.status = 'running'
  row.progress = 0

  const steps = [15, 35, 60, 85, 100]
  const stepMs = 300
  for (const p of steps) {
    await new Promise((r) => setTimeout(r, stepMs))
    row.progress = p
  }
  row.status = 'completed'
  row.taskId = String(Math.floor(Math.random() * 90000) + 10000)
}

async function backendRun(row: QueueRow) {
  row.status = 'running'
  row.progress = 10

  if (row.type === 'docx') {
    row.error = '论文检测仅支持 PDF，请将 DOCX 转为 PDF 后上传。'
    throw new Error(row.error)
  }

  if (row.type === 'image' || row.type === 'archive') {
    if (!row.file.type.startsWith('image/')) {
      row.error = '图像检测仅支持图片文件。'
      throw new Error(row.error)
    }

    const formData = new FormData()
    formData.append('file', row.file)
    const uploadRes = await uploadApi.uploadFile(formData)
    row.progress = 45

    const fileId = (uploadRes.data as { file_id?: string | number; id?: string | number }).file_id
      ?? (uploadRes.data as { id?: string | number }).id
    if (!fileId) {
      row.error = '图片上传成功，但后端未返回 file_id。'
      throw new Error(row.error)
    }

    const imagesRes = await uploadApi.getExtractedImages({
      file_id: fileId,
      page_number: 1,
      page_size: 100,
    })
    const images = ((imagesRes.data as { images?: Array<{ image_id?: string | number }> }).images || [])
      .map((item) => item.image_id)
      .filter((id): id is string | number => id !== undefined && id !== null)
    if (!images.length) {
      row.error = '图片已上传，但后端未生成可检测的 image_id。'
      throw new Error(row.error)
    }

    row.progress = 70
    const taskName = `${row.batchSessionId.slice(0, 24)}-${row.name}`
    const mode = detectionModePayload()
    const submitRes = await publisherApi.submitDetection({
      image_ids: images,
      task_name: taskName,
      batch_session_id: row.batchSessionId,
      detection_mode: mode,
      mode: imageSubmitMode(),
    })
    row.taskId = String((submitRes.data as { task_id?: string | number }).task_id ?? '')
    row.progress = 100
    row.status = 'completed'
    return
  }

  if (row.type === 'paper') {
    if (!row.file.name.toLowerCase().endsWith('.pdf')) {
      row.error = '论文检测仅支持 PDF。'
      throw new Error(row.error)
    }
    const taskName = `${row.batchSessionId.slice(0, 24)}-${row.name}`
    const submitRes = await paperApi.uploadAndSubmitAigcTask(row.file, taskName, {
      batch_session_id: row.batchSessionId,
      detection_mode: detectionModePayload(),
    })
    const payload = submitRes.data as { task_id?: string | number; status?: string; error_message?: string }
    row.taskId = String(payload.task_id ?? '')
    if (payload.status === 'failed') {
      row.error =
        payload.error_message ||
        '论文 AIGC 检测失败（常见原因：AI 服务未启动、PDF 无法解析或网络异常）'
      throw new Error(row.error)
    }
    row.progress = 100
    row.status = 'completed'
    return
  }

  if (row.type === 'review') {
    const baseName = row.name.replace(/\.[^.]+$/, '') || 'review'
    const taskName = `${row.batchSessionId.slice(0, 24)}-${baseName}`
    if (row.pastedReviewText != null && row.pastedReviewText.length > 0) {
      const submitRes = await submitReviewDetection({
        task_name: taskName,
        text: row.pastedReviewText,
        batch_session_id: row.batchSessionId,
        detection_mode: detectionModePayload(),
      })
      row.taskId = String((submitRes.data as { task_id?: string | number }).task_id ?? '')
      row.progress = 100
      row.status = 'completed'
      return
    }
    if (!row.file.name.toLowerCase().endsWith('.txt')) {
      row.error = 'Review 检测需 .txt 或使用上方粘贴文本。'
      throw new Error(row.error)
    }
    const submitRes = await submitReviewDetection({
      task_name: taskName,
      file: row.file,
      batch_session_id: row.batchSessionId,
      detection_mode: detectionModePayload(),
    })
    row.taskId = String((submitRes.data as { task_id?: string | number }).task_id ?? '')
    row.progress = 100
    row.status = 'completed'
    return
  }

  if (!row.taskId) {
    row.taskId = `local-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
  }
  row.progress = 100
  row.status = 'failed'
  row.error = '该类型暂未接入后端接口（可先开启 Mock 模式演示流程）。'
  throw new Error(row.error)
}

async function start() {
  if (!files.value.length && !reviewPasteText.value.trim()) return

  const batchId = newBatchId()
  batchSessionId.value = batchId

  running.value = true
  const built: QueueRow[] = files.value.map((f) => ({
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    file: f,
    name: f.name,
    size: f.size,
    type: detectType(f),
    status: 'pending' as const,
    progress: 0,
    batchSessionId: batchId,
  }))

  const pasted = reviewPasteText.value.trim()
  if (pasted) {
    built.push({
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      file: new File([pasted], 'pasted-review.txt', { type: 'text/plain' }),
      name: '粘贴的 Review 文本',
      size: new Blob([pasted]).size,
      type: 'review',
      status: 'pending',
      progress: 0,
      batchSessionId: batchId,
      pastedReviewText: pasted,
    })
  }

  rows.value = built

  for (const row of rows.value) {
    try {
      if (USE_MOCK) {
        await mockRun(row)
      } else {
        await backendRun(row)
      }
    } catch (e: unknown) {
      row.status = row.status === 'completed' ? 'completed' : 'failed'
      if (!row.error) {
        row.error = axiosDetail(e)
      }
    }
  }

  running.value = false

  const okCount = rows.value.filter((r) => r.status === 'completed').length
  const failCount = rows.value.length - okCount
  const firstFail = rows.value.find((r) => r.status === 'failed' && r.error)
  const hint = firstFail?.error ? `（首条：${firstFail.error.slice(0, 100)}${firstFail.error.length > 100 ? '…' : ''}）` : ''
  snackbar.showMessage(`本批检测结束：成功 ${okCount}，失败 ${failCount} ${hint}`, failCount ? 'warning' : 'success')
  saveLocalTasks(rows.value)
  if (okCount > 0 && batchSessionId.value) {
    router.push({ path: '/history', query: { batch_session_id: batchSessionId.value } })
  }
}

function openResult(row: QueueRow) {
  if (!row.taskId) {
    row.taskId = `local-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
  }
  if (row.type === 'paper') {
    router.push({ path: '/upload', query: { section: 'paper', paper_tab: 'aigc', task_id: row.taskId } })
    return
  }
  if (row.type === 'review') {
    router.push({ path: '/upload', query: { section: 'review', task_id: row.taskId } })
    return
  }
  const taskType = toTaskType(row.type)
  router.push({
    path: '/history',
    query: {
      detail_id: row.taskId,
      task_type: taskType,
      status: row.status === 'running' ? 'in_progress' : row.status,
      progress: String(row.progress),
      upload_time: nowString(),
      completion_time: row.status === 'completed' ? nowString() : '',
      source: 'upload',
      batch_session_id: row.batchSessionId,
    },
  })
}
</script>

<style scoped>
.gap-3 {
  gap: 12px;
}

.font-mono {
  font-family: ui-monospace, monospace;
}

.detection-hub :deep(.paper-workbench),
.detection-hub :deep(.review-detect-page) {
  box-shadow: none;
}
</style>
