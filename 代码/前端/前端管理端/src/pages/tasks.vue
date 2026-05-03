<template>
  <v-container>
    <v-row class="mb-4 align-center">
      <v-col cols="12" md="6">
        <h1 class="text-h4 font-weight-bold">检测任务</h1>
        <p class="text-body-2 text-medium-emphasis mb-0">
          展示权限范围内的统一检测任务；开启自动刷新后对进行中任务轮询，并尝试通过 WebSocket 接收通知以刷新列表。
        </p>
      </v-col>
      <v-col cols="12" md="6" class="d-flex flex-wrap justify-end gap-2">
        <v-chip v-if="useSocket" :color="wsConnected ? 'success' : 'warning'" size="small" variant="tonal">
          WebSocket {{ wsConnected ? '已连接' : '未连接' }}
        </v-chip>
        <v-switch
          v-model="autoRefresh"
          hide-details
          color="primary"
          density="compact"
          label="自动刷新"
        ></v-switch>
        <v-btn color="primary" prepend-icon="mdi-refresh" class="text-none" :loading="loading" @click="loadTasks">
          刷新
        </v-btn>
      </v-col>
    </v-row>

    <v-row class="mb-4">
      <v-col cols="12" sm="6" md="3">
        <v-select
          v-model="filterType"
          label="任务类型"
          :items="taskTypeItems"
          clearable
          hide-details
          density="compact"
          variant="outlined"
        ></v-select>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-select
          v-model="filterStatus"
          label="状态"
          :items="statusItems"
          clearable
          hide-details
          density="compact"
          variant="outlined"
        ></v-select>
      </v-col>
      <v-col cols="12" sm="6" md="4">
        <v-text-field
          v-model="filterKeyword"
          label="搜索任务名 / 用户名"
          prepend-inner-icon="mdi-magnify"
          clearable
          hide-details
          density="compact"
          variant="outlined"
        ></v-text-field>
      </v-col>
      <v-col v-if="isSoftwareAdmin" cols="12" sm="6" md="2">
        <v-text-field
          v-model="organizationFilter"
          label="组织 ID（可选）"
          type="number"
          hide-details
          density="compact"
          variant="outlined"
          @blur="loadTasks"
        ></v-text-field>
      </v-col>
    </v-row>

    <v-card>
      <v-data-table
        :headers="headers"
        :items="filteredTasks"
        :loading="loading"
        hover
        class="elevation-0"
      >
        <template #item.task_name="{ item }">
          <div>{{ item.task_name }}</div>
          <div
            v-if="item.status === 'failed' && item.error_message"
            class="text-caption text-error text-truncate"
            :title="item.error_message"
          >
            {{ item.error_message }}
          </div>
        </template>
        <template #item.task_type="{ item }">
          <v-chip size="small" variant="tonal">{{ formatTaskType(item.task_type) }}</v-chip>
        </template>
        <template #item.username="{ item }">
          {{ item.username ?? '—' }}
        </template>
        <template #item.status="{ item }">
          <v-chip :color="statusColor(item.status)" size="small">{{ formatStatus(item.status) }}</v-chip>
        </template>
        <template #item.upload_time="{ item }">
          {{ formatTime(item.upload_time) }}
        </template>
        <template #item.completion_time="{ item }">
          {{ item.completion_time ? formatTime(item.completion_time) : '—' }}
        </template>
        <template #item.actions="{ item }">
          <v-btn size="small" variant="text" color="primary" class="text-none" @click="openDetail(item)">
            详情
          </v-btn>
        </template>
      </v-data-table>
    </v-card>

    <v-dialog v-model="detailOpen" max-width="960" scrollable>
      <v-card v-if="detailTask">
        <v-card-title class="d-flex align-center flex-wrap">
          <span>任务 #{{ detailTask.task_id }}</span>
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="text" @click="detailOpen = false"></v-btn>
        </v-card-title>
        <v-divider></v-divider>
        <v-card-text>
          <v-progress-linear v-if="detailLoading" indeterminate class="mb-4"></v-progress-linear>
          <template v-if="detailData">
            <v-row dense>
              <v-col cols="12" sm="6"><strong>名称</strong>：{{ detailData.task_name }}</v-col>
              <v-col cols="12" sm="6"><strong>状态</strong>：{{ formatStatus(detailData.status) }}</v-col>
              <v-col cols="12" sm="6"><strong>组织</strong>：{{ detailData.organization || '—' }}</v-col>
              <v-col cols="12" sm="6"><strong>上传时间</strong>：{{ formatTime(detailData.upload_time) }}</v-col>
              <v-col cols="12" sm="6">
                <strong>完成时间</strong>：{{ detailData.completion_time ? formatTime(detailData.completion_time) : '—' }}
              </v-col>
            </v-row>
            <div v-if="detailData.detection_results?.length" class="mt-4">
              <div class="text-subtitle-2 mb-2">图像检测结果（图像类任务）</div>
              <v-table density="compact">
                <thead>
                  <tr>
                    <th>图像 ID</th>
                    <th>状态</th>
                    <th>可疑</th>
                    <th>置信度</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in detailData.detection_results" :key="idx">
                    <td>{{ row.image_id }}</td>
                    <td>{{ row.status }}</td>
                    <td>{{ row.is_fake ? '是' : '否' }}</td>
                    <td>{{ row.confidence_score ?? '—' }}</td>
                  </tr>
                </tbody>
              </v-table>
            </div>
            <div v-else class="text-body-2 text-medium-emphasis mt-4">
              当前详情接口主要返回图像检测子结果；论文 / Review 类任务请以列表中的类型与状态为准，或前往用户端统一详情查看。
            </div>
          </template>
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import taskApi from '@/api/task'
import userApi from '@/api/user'
import type { AdminTaskItem, AdminTaskStatusDetail } from '@/types/core'
import { useAdminNotifySocket } from '@/composables/useAdminNotifySocket'
import { useSnackbarStore } from '@/stores/snackbar'

const snackbar = useSnackbarStore()

const loading = ref(false)
const tasks = ref<AdminTaskItem[]>([])
const isSoftwareAdmin = ref(false)

const filterType = ref<string | null>(null)
const filterStatus = ref<string | null>(null)
const filterKeyword = ref('')
const organizationFilter = ref<string>('')

const autoRefresh = ref(true)
const useSocket = ref(true)
const pollMs = 8000

let pollTimer: number | null = null

const taskTypeItems = [
  { title: '图像检测', value: 'image_detection' },
  { title: '论文 AIGC', value: 'paper_aigc' },
  { title: '学术资源检测', value: 'resource_check' },
  { title: 'Review 检测', value: 'review_detection' },
]

const statusItems = [
  { title: '待处理', value: 'pending' },
  { title: '进行中', value: 'in_progress' },
  { title: '已完成', value: 'completed' },
  { title: '失败', value: 'failed' },
]

const headers = [
  { title: '任务 ID', key: 'task_id', width: '88px' },
  { title: '任务名称', key: 'task_name' },
  { title: '类型', key: 'task_type', width: '140px' },
  { title: '状态', key: 'status', width: '120px' },
  { title: '用户', key: 'username', width: '120px' },
  { title: '组织', key: 'organization', width: '140px' },
  { title: '上传时间', key: 'upload_time', width: '180px' },
  { title: '完成时间', key: 'completion_time', width: '180px' },
  { title: '操作', key: 'actions', sortable: false, width: '100px' },
]

function formatTaskType(t: string | undefined) {
  if (!t) return '—'
  const map: Record<string, string> = {
    image_detection: '图像检测',
    paper_aigc: '论文 AIGC',
    resource_check: '学术资源',
    review_detection: 'Review',
  }
  return map[t] || t
}

function formatStatus(s: string) {
  const map: Record<string, string> = {
    pending: '待处理',
    in_progress: '进行中',
    completed: '已完成',
    failed: '失败',
  }
  return map[s] || s
}

function statusColor(s: string) {
  if (s === 'completed') return 'success'
  if (s === 'failed') return 'error'
  if (s === 'in_progress') return 'warning'
  return 'default'
}

function formatTime(iso: string) {
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleString()
  } catch {
    return iso
  }
}

const filteredTasks = computed(() => {
  let list = tasks.value
  if (filterType.value) {
    list = list.filter((t) => (t.task_type ?? '') === filterType.value)
  }
  if (filterStatus.value) {
    list = list.filter((t) => t.status === filterStatus.value)
  }
  const q = filterKeyword.value.trim().toLowerCase()
  if (q) {
    list = list.filter(
      (t) =>
        (t.task_name && t.task_name.toLowerCase().includes(q)) ||
        (t.username && t.username.toLowerCase().includes(q)),
    )
  }
  return list
})

function listQueryParams() {
  const p: { organization?: string } = {}
  if (isSoftwareAdmin.value && organizationFilter.value) {
    const id = organizationFilter.value.trim()
    if (id) p.organization = id
  }
  return p
}

async function loadTasks() {
  loading.value = true
  try {
    const res = await taskApi.getAllTasks(listQueryParams())
    tasks.value = res.data.tasks || []
  } catch (e) {
    console.error(e)
    snackbar.showMessage('加载任务列表失败', 'error')
  } finally {
    loading.value = false
  }
}

function hasActiveJobs(list: AdminTaskItem[]) {
  return list.some((t) => t.status === 'pending' || t.status === 'in_progress')
}

function restartPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  if (!autoRefresh.value) return
  pollTimer = window.setInterval(() => {
    if (hasActiveJobs(tasks.value)) {
      loadTasks()
    }
  }, pollMs)
}

const { connected: wsConnected, connect: connectWs, disconnect: disconnectWs } = useAdminNotifySocket(() => {
  loadTasks()
})

watch(autoRefresh, (on) => {
  if (on) restartPolling()
  else if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})

watch(tasks, () => {
  if (autoRefresh.value) restartPolling()
})

const detailOpen = ref(false)
const detailTask = ref<AdminTaskItem | null>(null)
const detailData = ref<AdminTaskStatusDetail | null>(null)
const detailLoading = ref(false)

async function openDetail(row: AdminTaskItem) {
  detailTask.value = row
  detailData.value = null
  detailOpen.value = true
  detailLoading.value = true
  try {
    const res = await taskApi.getDetectionTaskStatus(row.task_id, listQueryParams())
    detailData.value = res.data
  } catch {
    snackbar.showMessage('加载任务详情失败', 'error')
  } finally {
    detailLoading.value = false
  }
}

onMounted(async () => {
  try {
    const me = await userApi.getUserInfo()
    isSoftwareAdmin.value = me.data.admin_type === 'software_admin'
  } catch {
    /* ignore */
  }
  await loadTasks()
  restartPolling()
  if (useSocket.value) {
    connectWs()
  }
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  disconnectWs()
})
</script>
