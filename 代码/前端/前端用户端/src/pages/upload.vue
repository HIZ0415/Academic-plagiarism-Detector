<template>
  <div class="upload-page">
    <v-row class="mb-6" align="center">
      <v-col cols="12" md="8">
        <div class="text-h4 font-weight-bold mb-1">学术检测</div>
        <div class="text-body-2 text-medium-emphasis">
          统一入口：支持图像 / 论文(PDF/DOCX/TXT) / Review 文本的上传与批量检测（可用 Mock 模式演示流程）。
        </div>
      </v-col>
      <v-col cols="12" md="4" class="d-flex justify-end">
        <v-chip :color="USE_MOCK ? 'warning' : 'success'" variant="tonal">
          {{ USE_MOCK ? 'Mock 模式' : '后端模式' }}
        </v-chip>
      </v-col>
    </v-row>

    <v-card class="pa-4" variant="outlined">
      <v-row>
        <v-col cols="12" md="8">
          <v-file-input
            v-model="files"
            multiple
            show-size
            counter
            prepend-icon="mdi-paperclip"
            label="选择文件（支持：图片、PDF、DOCX、TXT、ZIP、RAR）"
            accept="image/*,.pdf,.docx,.txt,.zip,.rar"
            :disabled="running"
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-select
            v-model="mode"
            :items="modeItems"
            label="检测模式"
            prepend-icon="mdi-tune"
            :disabled="running"
          />
        </v-col>
      </v-row>

      <v-row class="mt-2">
        <v-col cols="12" class="d-flex gap-3">
          <v-btn color="primary" prepend-icon="mdi-play" :loading="running" :disabled="!files.length" @click="start">
            开始批量检测
          </v-btn>
          <v-btn variant="outlined" prepend-icon="mdi-refresh" :disabled="running" @click="reset">
            重置表单
          </v-btn>
        </v-col>
      </v-row>
    </v-card>

    <v-card v-if="rows.length" class="mt-6" variant="outlined">
      <v-card-title class="text-subtitle-1 font-weight-bold">任务队列</v-card-title>
      <v-divider />
      <v-card-text>
        <v-data-table :headers="headers" :items="rows" item-key="id" hide-default-footer>
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

          <template #item.actions="{ item }">
            <v-btn
              v-if="item.taskId && item.type !== 'image'"
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
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSnackbarStore } from '@/stores/snackbar'
import paperApi from '@/api/paper'

type DetectMode = 'fast' | 'accurate'
type ResourceType = 'image' | 'paper' | 'review' | 'unknown'
type RowStatus = 'pending' | 'running' | 'completed' | 'failed'

type QueueRow = {
  id: string
  file: File
  name: string
  size: number
  type: ResourceType
  status: RowStatus
  progress: number
  taskId?: string
  error?: string
}

type LocalTaskRecord = {
  task_id: string
  task_type: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  progress: number
  upload_time: string
  completion_time: string
  source: 'local'
}

const USE_MOCK = import.meta.env.VITE_USE_MOCK_AIGC === 'true'
const router = useRouter()
const snackbar = useSnackbarStore()

const files = ref<File[]>([])
const mode = ref<DetectMode>('fast')
const running = ref(false)

const modeItems = computed(() => ([
  { title: '快速', value: 'fast' as const },
  { title: '精准', value: 'accurate' as const },
]))

const headers = [
  { title: '文件名', key: 'name', align: 'start' as const },
  { title: '类型', key: 'type', align: 'center' as const, width: 120 },
  { title: '进度', key: 'progress', align: 'center' as const, width: 220 },
  { title: '状态', key: 'status', align: 'center' as const, width: 140 },
  { title: '操作', key: 'actions', align: 'center' as const, sortable: false, width: 100 },
] as const

const rows = ref<QueueRow[]>([])

function detectType(file: File): ResourceType {
  const name = file.name.toLowerCase()
  if (file.type.startsWith('image/')) return 'image'
  if (name.includes('review') || name.includes('rebuttal') || name.includes('评审')) return 'review'
  if (name.endsWith('.pdf') || name.endsWith('.docx') || name.endsWith('.txt')) return 'paper'
  if (name.endsWith('.zip') || name.endsWith('.rar')) return 'unknown'
  return 'unknown'
}

function typeLabel(t: ResourceType) {
  switch (t) {
    case 'image':
      return '图像'
    case 'paper':
      return '论文/文本'
    case 'review':
      return 'Review'
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
  rows.value = []
  running.value = false
}

function toTaskType(t: ResourceType) {
  if (t === 'paper') return 'paper_aigc'
  if (t === 'image') return 'image_detection'
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
  for (const p of steps) {
    await new Promise((r) => setTimeout(r, mode.value === 'fast' ? 250 : 450))
    row.progress = p
  }
  row.status = 'completed'
  row.taskId = String(Math.floor(Math.random() * 90000) + 10000)
}

async function backendRun(row: QueueRow) {
  row.status = 'running'
  row.progress = 10

  if (row.type === 'paper') {
    // 论文/文本：复用 `paper.vue` 的上传+提交逻辑（AIGC tab）
    const taskName = `${mode.value}-${row.name}`
    const submitRes = await paperApi.uploadAndSubmitAigcTask(row.file, taskName)
    row.taskId = String(submitRes.data.task_id)
    row.progress = 100
    row.status = 'completed'
    return
  }

  // 图像与 Review：目前用户端现有 API 未提供统一上传接口，这里先提示不阻塞演示
  if (!row.taskId) {
    row.taskId = `local-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
  }
  row.progress = 100
  row.status = 'failed'
  row.error = '该类型暂未接入后端接口（可先开启 Mock 模式演示流程）。'
  throw new Error(row.error)
}

async function start() {
  if (!files.value.length) return

  running.value = true
  rows.value = files.value.map((f) => ({
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    file: f,
    name: f.name,
    size: f.size,
    type: detectType(f),
    status: 'pending',
    progress: 0,
  }))

  for (const row of rows.value) {
    try {
      if (USE_MOCK) {
        await mockRun(row)
      } else {
        await backendRun(row)
      }
    } catch (e) {
      row.status = row.status === 'completed' ? 'completed' : 'failed'
    }
  }

  running.value = false

  const okCount = rows.value.filter((r) => r.status === 'completed').length
  const failCount = rows.value.length - okCount
  snackbar.showMessage(`批量检测完成：成功 ${okCount}，失败 ${failCount}`, failCount ? 'warning' : 'success')
  saveLocalTasks(rows.value)

  // 无论成功/失败，都统一进入结果页，保证不依赖后端也能看到本次检测详情
  const row = rows.value.find((r) => r.status === 'completed' && !!r.taskId) || rows.value[0]
  if (row) {
    if (!row.taskId) {
      row.taskId = `local-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
    }
    router.push({
      path: '/history',
      query: {
        detail_id: row.taskId,
        task_type: toTaskType(row.type),
        status: row.status === 'running' ? 'in_progress' : row.status,
        progress: String(row.progress),
        upload_time: nowString(),
        completion_time: row.status === 'completed' ? nowString() : '',
        error_message: row.error || '',
        source: 'upload',
      },
    })
    return
  }
  router.push('/history')
}

function openResult(row: QueueRow) {
  if (!row.taskId) {
    row.taskId = `local-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
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
    },
  })
}
</script>

<style scoped>
.gap-3 {
  gap: 12px;
}
</style>
