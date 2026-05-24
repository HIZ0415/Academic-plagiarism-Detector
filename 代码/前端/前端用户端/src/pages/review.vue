<template>
  <div class="review-page pb-12">
    <v-row class="mb-4" align="center">
      <v-col cols="12" md="8">
        <h1 class="text-h4 font-weight-bold mb-0">人工审核任务池</h1>
      </v-col>
    </v-row>

    <v-alert type="info" variant="tonal" density="compact" class="mb-4 text-body-2">
      <strong>流程：</strong>发布者提交「人工审核申请」→ 组织管理员审批通过 → 本页待办 →
      进入审核页填写结论 → 发布者在「人工审核申请」或「检测历史」中查看汇总结果。
    </v-alert>

    <v-row class="mb-4">
      <v-col cols="6" sm="4">
        <v-card variant="tonal" color="primary">
          <v-card-text class="text-center py-4">
            <div class="text-h5 font-weight-bold">{{ stats.received }}</div>
            <div class="text-caption">已分配任务</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="4">
        <v-card variant="tonal" color="success">
          <v-card-text class="text-center py-4">
            <div class="text-h5 font-weight-bold">{{ stats.completed }}</div>
            <div class="text-caption">已完成</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="4">
        <v-card variant="tonal" color="warning">
          <v-card-text class="text-center py-4">
            <div class="text-h5 font-weight-bold">{{ stats.pending }}</div>
            <div class="text-caption">待处理</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mb-4" align="center">
      <v-col cols="12" sm="8" md="5">
        <v-text-field
          v-model="searchQuery"
          label="搜索发布者用户名"
          append-inner-icon="mdi-magnify"
          clearable
          density="compact"
          hide-details
          placeholder="前缀匹配"
          @keyup.enter="handleSearch"
          @click:append-inner="handleSearch"
          @click:clear="handleSearch"
        />
      </v-col>
      <v-col cols="12" sm="4" md="7" class="d-flex justify-end flex-wrap ga-2">
        <v-btn color="primary" class="text-none" prepend-icon="mdi-filter-variant" @click="showFilterDialog = true">
          筛选
        </v-btn>
        <v-btn class="text-none" prepend-icon="mdi-refresh" :loading="loading" @click="reloadList">刷新</v-btn>
      </v-col>
    </v-row>

    <v-card border>
      <v-data-table
        :headers="headers"
        :items="tasks"
        :loading="loading"
        class="elevation-0"
        hide-default-footer
        hover
        :items-per-page="pageSize"
      >
        <template #top>
          <div class="d-flex align-center justify-space-between flex-wrap pa-4 ga-2">
            <span class="text-caption text-medium-emphasis">共 {{ totalCount }} 条（仅显示管理端已通过的任务）</span>
            <v-chip v-if="stats.pending > 0" color="warning" size="small" variant="tonal">
              待处理 {{ stats.pending }}
            </v-chip>
          </div>
        </template>

        <template #[`item.publisher`]="{ item }">
          <div class="d-flex align-center ga-2 py-1">
            <v-avatar size="36">
              <v-img :src="item.publisher_avatar || defaultAvatar" :alt="item.publisher_username" />
            </v-avatar>
            <span>{{ item.publisher_username }}</span>
          </div>
        </template>

        <template #[`item.task_kind`]="{ item }">
          <v-chip size="small" :color="taskKindColor(item.task_kind)" variant="tonal">
            {{ taskKindLabel(item.task_kind) }}
          </v-chip>
        </template>

        <template #[`item.material`]="{ item }">
          <span class="text-body-2">{{ materialSummary(item) }}</span>
        </template>

        <template #[`item.status`]="{ item }">
          <v-chip size="small" :color="statusColor(item.status)" variant="flat">
            {{ statusLabel(item.status) }}
          </v-chip>
        </template>

        <template #[`item.admin_gate_status`]="{ item }">
          <v-chip size="small" :color="item.admin_gate_status === 'accepted' ? 'success' : 'grey'" variant="tonal">
            {{ adminGateLabel(item.admin_gate_status) }}
          </v-chip>
        </template>

        <template #[`item.actions`]="{ item }">
          <v-btn
            color="primary"
            variant="flat"
            size="small"
            class="text-none"
            prepend-icon="mdi-clipboard-check-outline"
            @click="goDetail(item)"
          >
            {{ item.status === 'completed' ? '查看' : '进入审核' }}
          </v-btn>
        </template>

        <template #no-data>
          <div class="text-center pa-8 text-medium-emphasis">
            <v-icon size="48" class="mb-2">mdi-clipboard-text-off-outline</v-icon>
            <div class="text-body-1">暂无人工审核任务</div>
            <div class="text-body-2 mt-2">
              请确认：① 已用<strong>专家</strong>账号登录；② 组织管理员已<strong>通过</strong>申请；③ 后端服务已正常启动。
            </div>
          </div>
        </template>
      </v-data-table>

      <div class="d-flex align-center justify-center flex-wrap pa-4 ga-4">
        <div class="d-flex align-center">
          <span class="text-caption mr-2">每页</span>
          <v-select
            v-model="pageSize"
            :items="[5, 10, 20, 50]"
            density="compact"
            variant="outlined"
            hide-details
            style="width: 90px"
            @update:model-value="onPageSizeChange"
          />
        </div>
        <v-pagination
          v-model="currentPage"
          :length="totalPages"
          :total-visible="7"
          @update:model-value="onPageChange"
        />
      </div>
    </v-card>

    <v-dialog v-model="showFilterDialog" max-width="480">
      <v-card>
        <v-card-title class="text-h6">筛选条件</v-card-title>
        <v-card-text class="d-flex flex-column ga-4">
          <v-select
            v-model="filters.expertStatus"
            :items="expertStatusOptions"
            label="我的审核状态"
            clearable
            hide-details
          />
          <v-select
            v-model="filters.requestStatus"
            :items="requestStatusOptions"
            label="申请流转状态"
            clearable
            hide-details
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="resetFilters">重置</v-btn>
          <v-btn color="primary" variant="flat" @click="applyFilters">应用</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import reviewerApi from '@/api/reviewer'
import { useSnackbarStore } from '@/stores/snackbar'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const snackbar = useSnackbarStore()
const userStore = useUserStore()

const API_BASE = import.meta.env.VITE_API_URL || ''
const defaultAvatar = 'https://api.dicebear.com/7.x/avataaars/svg?seed=reviewer'

interface ReviewerTaskRow {
  manual_review_id: number
  manual_review_time: string
  publisher_username: string
  publisher_avatar: string | null
  image_count: number
  status: string
  review_request_id: number
  review_request_status: string
  admin_gate_status: string
  task_kind: string
  detection_task_id?: number | string | null
  task_type?: string | null
  reason?: string
  organization?: string | null
}

const headers = [
  { title: '发布者', key: 'publisher', align: 'start' as const, sortable: false },
  { title: '检测任务 ID', key: 'detection_task_id', align: 'center' as const },
  { title: '类型', key: 'task_kind', align: 'center' as const },
  { title: '材料规模', key: 'material', align: 'center' as const, sortable: false },
  { title: '申请理由', key: 'reason', align: 'start' as const, minWidth: 140 },
  { title: '管理端', key: 'admin_gate_status', align: 'center' as const },
  { title: '我的进度', key: 'status', align: 'center' as const },
  { title: '分配时间', key: 'manual_review_time', align: 'center' as const },
  { title: '操作', key: 'actions', align: 'center' as const, sortable: false },
]

const tasks = ref<ReviewerTaskRow[]>([])
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const totalCount = ref(0)
const totalPages = ref(1)
const showFilterDialog = ref(false)

const filters = ref({
  expertStatus: null as string | null,
  requestStatus: null as string | null,
})

const expertStatusOptions = [
  { title: '待处理', value: 'undo' },
  { title: '已完成', value: 'completed' },
]

const requestStatusOptions = [
  { title: '待管理员', value: 'pending' },
  { title: '审核中', value: 'in_progress' },
  { title: '已完成', value: 'completed' },
]

const stats = ref({ received: 0, completed: 0, pending: 0 })

async function loadStats() {
  try {
    const res = await reviewerApi.getTaskCount()
    const d = res.data as {
      total_received_tasks?: number
      total_completed_tasks?: number
      total_pending_tasks?: number
    }
    stats.value.received = Number(d.total_received_tasks ?? 0)
    stats.value.completed = Number(d.total_completed_tasks ?? 0)
    stats.value.pending =
      d.total_pending_tasks != null
        ? Number(d.total_pending_tasks)
        : Math.max(0, stats.value.received - stats.value.completed)
  } catch {
    stats.value = {
      received: totalCount.value,
      completed: tasks.value.filter((t) => t.status === 'completed').length,
      pending: tasks.value.filter((t) => t.status === 'undo').length,
    }
  }
}

function taskKindLabel(kind: string) {
  const k = (kind || 'image').toLowerCase()
  if (k.includes('paper')) return '论文'
  if (k.includes('review')) return 'Review'
  return '图像'
}

function taskKindColor(kind: string) {
  const k = (kind || 'image').toLowerCase()
  if (k.includes('paper')) return 'indigo'
  if (k.includes('review')) return 'deep-purple'
  return 'teal'
}

function statusLabel(status: string) {
  if (status === 'completed') return '已提交'
  if (status === 'undo') return '待处理'
  return status
}

function statusColor(status: string) {
  if (status === 'completed') return 'success'
  if (status === 'undo') return 'warning'
  return 'grey'
}

function adminGateLabel(state: string) {
  if (state === 'accepted') return '已通过'
  if (state === 'refused') return '已拒绝'
  if (state === 'pending') return '待审批'
  return state
}

function materialSummary(item: ReviewerTaskRow) {
  const k = (item.task_kind || '').toLowerCase()
  if (k.includes('paper')) return '全文/段落'
  if (k.includes('review')) return 'Review 文本'
  const n = item.image_count || 0
  return n ? `${n} 张图` : '—'
}

function formatLoadError(e: unknown): string {
  const ax = e as {
    response?: { status?: number; data?: { error?: string; message?: string; detail?: string } }
    message?: string
  }
  const status = ax.response?.status
  const d = ax.response?.data
  const serverMsg =
    (typeof d?.error === 'string' && d.error) ||
    (typeof d?.message === 'string' && d.message) ||
    (typeof d?.detail === 'string' && d.detail) ||
    ''
  if (status === 403) {
    return (
      serverMsg ||
      '当前账号不是专家。请退出后使用专家账号登录（reviewer_test@example.com / Reviewer123!），登录页选择「专家」。'
    )
  }
  if (status === 401) return serverMsg || '登录已过期，请重新登录'
  if (status === 400) return serverMsg || '请求参数无效'
  if (serverMsg) return serverMsg
  return ax.message || '无法连接服务器，请确认网络与后端服务正常'
}

function mapRow(raw: Record<string, unknown>): ReviewerTaskRow {
  const avatar = raw.publisher_avatar
  return {
    manual_review_id: Number(raw.manual_review_id),
    manual_review_time: String(raw.manual_review_time ?? ''),
    publisher_username: String(raw.publisher_username ?? ''),
    publisher_avatar: avatar ? (String(avatar).startsWith('http') ? String(avatar) : API_BASE + avatar) : null,
    image_count: Number(raw.image_count ?? 0),
    status: String(raw.status ?? 'undo'),
    review_request_id: Number(raw.review_request_id),
    review_request_status: String(raw.review_request_status ?? ''),
    admin_gate_status: String(raw.admin_gate_status ?? ''),
    task_kind: String(raw.task_kind ?? raw.task_type ?? 'image'),
    detection_task_id: raw.detection_task_id ?? null,
    task_type: raw.task_type != null ? String(raw.task_type) : null,
    reason:
      raw.reason != null
        ? String(raw.reason).length > 56
          ? `${String(raw.reason).slice(0, 56)}…`
          : String(raw.reason)
        : '—',
    organization: raw.organization != null ? String(raw.organization) : null,
  }
}

async function fetchTasks(page = currentPage.value, size = pageSize.value) {
  if (!userStore.isLoaded) {
    await userStore.fetchUserInfo()
  }
  if (userStore.role !== 'reviewer') {
    snackbar.showMessage(
      `当前登录角色为「${userStore.role || '未知'}」，专家任务池需使用专家账号。请退出后用 reviewer_test@example.com 登录并选择「专家」。`,
      'warning',
    )
    tasks.value = []
    totalCount.value = 0
    totalPages.value = 1
    return
  }
  loading.value = true
  try {
    const params: Record<string, string | number> = {
      page,
      page_size: size,
      query: searchQuery.value.trim(),
    }
    if (filters.value.expertStatus) params.status = filters.value.expertStatus
    if (filters.value.requestStatus) params.review_request_status = filters.value.requestStatus

    const res = await reviewerApi.getReviewerTasks(params)
    const data = res.data as {
      results?: Record<string, unknown>[]
      current_page?: number
      total_pages?: number
      total_count?: number
    }
    const list = Array.isArray(data.results) ? data.results : []
    tasks.value = list.map(mapRow)
    currentPage.value = data.current_page ?? page
    totalPages.value = Math.max(1, data.total_pages ?? 1)
    totalCount.value = data.total_count ?? list.length
  } catch (e) {
    console.error(e)
    snackbar.showMessage(formatLoadError(e), 'error')
    tasks.value = []
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchTasks(1, pageSize.value)
}

function reloadList() {
  fetchTasks(currentPage.value, pageSize.value).then(() => loadStats())
}

function onPageChange(page: number) {
  fetchTasks(page, pageSize.value)
}

function onPageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  fetchTasks(1, size)
}

function resetFilters() {
  filters.value = { expertStatus: null, requestStatus: null }
  showFilterDialog.value = false
  currentPage.value = 1
  fetchTasks(1, pageSize.value)
}

function applyFilters() {
  showFilterDialog.value = false
  currentPage.value = 1
  fetchTasks(1, pageSize.value)
}

function goDetail(item: ReviewerTaskRow) {
  router.push(`/manual-review/${item.manual_review_id}`)
}

onMounted(() => {
  fetchTasks().then(() => loadStats())
})
</script>

<style scoped>
.review-page :deep(.v-data-table) {
  border-radius: 8px;
}
</style>
