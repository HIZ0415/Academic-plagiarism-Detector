<template>
  <div class="review-page pb-12">
    <v-row class="mb-4" align="center">
      <v-col cols="12" md="8">
        <h1 class="text-h4 font-weight-bold mb-2">人工审核任务池</h1>
        <p class="text-body-2 text-medium-emphasis mb-0">
          路由 <code>/review</code>：<strong>审稿人人工复核</strong>（FR-YHSH-0001 任务池、FR-YHSH-0002 鉴定）。任务材料可含图像 / 论文 / Review 等，以 <code>task_kind</code> 区分；与发布者侧 Review 文本<strong>自动检测</strong>（统一入口 <code>/upload</code>，FR-PLJC）不是同一功能。
        </p>
      </v-col>
    </v-row>

    <v-alert type="info" variant="tonal" density="compact" class="mb-4 review-intro-alert text-body-2">
      <div v-if="isPreviewMode" class="d-flex flex-column flex-sm-row flex-wrap align-sm-center ga-3">
        <span><strong>预览：</strong>未调接口时列表可能为空；可打开占位详情。</span>
        <v-btn
          color="primary"
          variant="flat"
          size="small"
          class="text-none"
          prepend-icon="mdi-open-in-new"
          @click="router.push('/task/detail/0')"
        >
          审核详情（图像）
        </v-btn>
        <v-btn size="small" variant="tonal" class="text-none" @click="router.push('/task/detail/0?preview_kind=paper')">
          论文工作台
        </v-btn>
        <v-btn size="small" variant="tonal" class="text-none" @click="router.push('/task/detail/0?preview_kind=review')">
          Review 工作台
        </v-btn>
      </div>
      <div v-else>
        <strong>流程：</strong>发布者「人工审核申请」→ 管理端 <code>admin_gate_status</code> → 分配至本页 → 进入详情提交结论。
      </div>
    </v-alert>

    <v-row class="mb-4" align="center">
      <v-col cols="12" sm="8" md="5">
        <v-text-field
          v-model="searchQuery"
          label="搜索发布者用户名"
          append-inner-icon="mdi-magnify"
          clearable
          density="compact"
          hide-details
          class="search-input"
          placeholder="支持前缀匹配"
          @keyup.enter="handleSearch"
          @click:append-inner="handleSearch"
          @click:clear="handleSearch"
        />
      </v-col>
      <v-col cols="12" sm="4" md="7" class="d-flex justify-end flex-wrap ga-2">
        <v-btn color="primary" class="text-none" prepend-icon="mdi-filter-variant" @click="showFilterDialog = true">
          筛选
        </v-btn>
      </v-col>
    </v-row>

    <v-card class="elevation-2">
      <v-data-table
        :headers="headers"
        :items="tasks"
        class="elevation-0 review-task-table"
        :items-per-page="pageSize"
        hover
        :loading="loading"
        hide-default-footer
      >
        <template #top>
          <div class="d-flex align-center pa-4">
            <span class="text-caption text-medium-emphasis">共 {{ totalTasks }} 条审核任务（分页按 ReviewRequest；类型含图像 / 论文 / Review 等）</span>
          </div>
        </template>

        <template #item.task_kind="{ item }">
          <v-chip size="small" variant="tonal" color="teal">{{ taskKindLabel(item.task_kind) }}</v-chip>
        </template>

        <template #item.publisher_avatar="{ item }">
          <v-avatar size="40">
            <v-img :src="avatarSrc(item.publisher_avatar)" :alt="item.publisher_username" />
          </v-avatar>
        </template>

        <template #item.image_count="{ item }">
          <span class="text-body-2 text-no-wrap">{{ materialScaleText(item) }}</span>
        </template>

        <template #item.review_request_status="{ item }">
          <v-chip size="small" variant="tonal" :color="requestStatusColor(item.review_request_status)">
            {{ requestStatusLabel(item.review_request_status) }}
          </v-chip>
        </template>

        <template #item.admin_gate_status="{ item }">
          <v-chip size="small" variant="tonal" :color="adminGateColor(item.admin_gate_status)">
            {{ adminGateLabel(item.admin_gate_status) }}
          </v-chip>
        </template>

        <template #item.status="{ item }">
          <v-chip size="small" variant="tonal" :color="getStatusColor(item.status)">
            {{ getStatusName(item.status) }}
          </v-chip>
        </template>

        <template #item.manual_review_time="{ item }">
          {{ item.manual_review_time }}
        </template>

        <template #item.actions="{ item }">
          <v-btn icon variant="text" size="small" color="primary" @click="goToTaskDetail(item)">
            <v-icon>mdi-arrow-right-circle</v-icon>
          </v-btn>
        </template>
      </v-data-table>

      <div class="d-flex align-center justify-center pa-4 flex-wrap">
        <div class="d-flex align-center">
          <span class="text-caption mr-2">每页显示</span>
          <v-select
            v-model="pageSize"
            :items="[5, 10, 20, 50, 100]"
            density="compact"
            variant="outlined"
            hide-details
            style="width: 100px"
            @update:model-value="handlePageSizeChange"
          />
          <span class="text-caption ml-2">条</span>
        </div>
        <v-pagination
          v-model="currentPage"
          :length="totalPages"
          :total-visible="7"
          class="ml-4"
          @update:model-value="handlePageChange"
        />
      </div>
    </v-card>

    <v-dialog v-model="showFilterDialog" max-width="520">
      <v-card>
        <v-card-title class="text-h6 font-weight-bold">筛选条件</v-card-title>
        <v-card-text>
          <div class="d-flex flex-column ga-4">
            <v-select
              v-model="filters.taskKind"
              :items="taskKindOptions"
              label="任务类型（图像 / 论文 / Review）"
              hide-details
            />
            <v-select
              v-model="filters.status"
              :items="statusOptions"
              label="我的审核进度"
              clearable
              hide-details
            />
            <v-select
              v-model="filters.reviewRequestStatus"
              :items="reviewRequestStatusOptions"
              label="整条审核流程状态（发布者视角）"
              clearable
              hide-details
            />
            <v-select
              v-model="filters.adminGateStatus"
              :items="adminGateOptions"
              label="管理端审批门闸"
              clearable
              hide-details
            />
            <v-select
              v-model="filters.timeRange"
              :items="timeRangeOptions"
              label="快速时间范围（按申请时间）"
              clearable
              hide-details
              @update:model-value="handleTimeRangeChange"
            />
            <div class="d-flex align-center ga-4 flex-wrap">
              <v-text-field
                v-model="filters.startDate"
                label="开始时间"
                type="datetime-local"
                hide-details
                density="compact"
                :error-messages="timeError"
                @update:model-value="handleCustomTimeChange"
              />
              <v-text-field
                v-model="filters.endDate"
                label="结束时间"
                type="datetime-local"
                hide-details
                density="compact"
                :error-messages="timeError"
                @update:model-value="handleCustomTimeChange"
              />
            </div>
            <v-alert type="warning" variant="tonal" density="compact" class="text-caption">
              需求中的学科分类、紧急程度、风险等级等维度需后端在 <code>get_reviewer_tasks</code> 中扩展字段后方可筛选；当前优先支持流程状态、管理门闸、时间范围与<strong>任务类型（图像 / 论文 / Review）</strong>等协作字段。
            </v-alert>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="resetFilters">重置</v-btn>
          <v-btn color="primary" @click="applyFilters">应用</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import reviewerApi from '@/api/reviewer'
import { useSnackbarStore } from '@/stores/snackbar'
import { resolveBackendMediaUrl } from '@/utils/backendUrl'
import { useEffectiveRole } from '@/composables/useEffectiveRole'

const router = useRouter()
const snackbar = useSnackbarStore()
const { isPreviewMode } = useEffectiveRole()

interface Task {
  manual_review_id: number
  manual_review_time: string
  publisher_username: string
  publisher_avatar: string | null
  /** 图像类：待审图张数；其它类型后端可复用或另给 scale 字段 */
  image_count?: number
  status: string
  review_request_id?: number
  review_request_status?: string
  admin_gate_status?: string
  task_kind?: string
  /** 论文类：可选页数/段数（后端扩展） */
  paper_unit_count?: number
  /** Review 类：可选字符数（后端扩展） */
  review_text_units?: number
}

const headers = [
  { title: '类型', key: 'task_kind', align: 'center', minWidth: 96 },
  { title: '头像', key: 'publisher_avatar', align: 'center', sortable: false, width: 72 },
  { title: '发布者', key: 'publisher_username', align: 'start', minWidth: 112 },
  { title: '审核规模', key: 'image_count', align: 'center', minWidth: 120 },
  { title: '流程状态', key: 'review_request_status', align: 'center', minWidth: 120 },
  { title: '管理审批', key: 'admin_gate_status', align: 'center', minWidth: 120 },
  { title: '我的进度', key: 'status', align: 'center', minWidth: 112 },
  { title: '分配时间', key: 'manual_review_time', align: 'center', minWidth: 176 },
  { title: '操作', key: 'actions', align: 'center', sortable: false, width: 72 },
] as const

const tasks = ref<Task[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const totalTasks = ref(0)
const totalPages = ref(1)
const searchQuery = ref('')
const showFilterDialog = ref(false)

const filters = ref({
  taskKind: null as string | null,
  status: null as string | null,
  reviewRequestStatus: null as string | null,
  adminGateStatus: null as string | null,
  timeRange: null as string | null,
  startDate: null as string | null,
  endDate: null as string | null,
})

const taskKindOptions = [
  { title: '全部类型', value: null },
  { title: '学术图像', value: 'image' },
  { title: '全篇论文', value: 'paper' },
  { title: '同行评审 Review', value: 'review' },
]

const statusOptions = [
  { title: '未完成', value: 'undo' },
  { title: '已完成', value: 'completed' },
]

const reviewRequestStatusOptions = [
  { title: '待处理', value: 'pending' },
  { title: '进行中', value: 'in_progress' },
  { title: '已完成', value: 'completed' },
]

const adminGateOptions = [
  { title: '待审批', value: 'pending' },
  { title: '已通过', value: 'accepted' },
  { title: '已拒绝', value: 'refused' },
]

const timeRangeOptions = [
  { title: '最近一天', value: '1d' },
  { title: '最近一周', value: '7d' },
  { title: '最近一月', value: '30d' },
  { title: '最近三月', value: '90d' },
  { title: '最近一年', value: '365d' },
]

const timeError = ref('')

function avatarSrc(path: string | null | undefined) {
  return resolveBackendMediaUrl(path) || 'https://randomuser.me/api/portraits/lego/1.jpg'
}

function taskKindLabel(kind?: string) {
  const k = (kind || '').toLowerCase()
  if (k === 'image' || k === 'image_detection') return '学术图像'
  if (k === 'paper' || k === 'paper_aigc' || k === 'paper_manual') return '论文'
  if (k === 'review' || k === 'review_detection' || k === 'review_manual') return 'Review'
  return kind || '—'
}

/** 列表「审核规模」列：按任务类型展示张数 / 段数 / 字数等 */
function materialScaleText(item: Task): string {
  const k = (item.task_kind || 'image').toLowerCase()
  if (k === 'image' || k === 'image_detection' || !item.task_kind) {
    const n = item.image_count
    return typeof n === 'number' ? `${n} 张` : '—'
  }
  if (k === 'paper' || k === 'paper_aigc' || k === 'paper_manual') {
    const n = item.paper_unit_count ?? item.image_count
    return typeof n === 'number' ? `${n} 段` : '论文 · 见详情'
  }
  if (k === 'review' || k === 'review_detection' || k === 'review_manual') {
    const n = item.review_text_units
    return typeof n === 'number' ? `约 ${n} 字` : 'Review · 见详情'
  }
  return '—'
}

function requestStatusLabel(s?: string) {
  switch (s) {
    case 'pending':
      return '待处理'
    case 'in_progress':
      return '进行中'
    case 'completed':
      return '已完成'
    default:
      return s || '—'
  }
}

function requestStatusColor(s?: string) {
  switch (s) {
    case 'pending':
      return 'grey'
    case 'in_progress':
      return 'info'
    case 'completed':
      return 'success'
    default:
      return 'grey'
  }
}

function adminGateLabel(s?: string) {
  switch (s) {
    case 'pending':
      return '待审批'
    case 'accepted':
      return '已通过'
    case 'refused':
      return '已拒绝'
    default:
      return s || '—'
  }
}

function adminGateColor(s?: string) {
  switch (s) {
    case 'accepted':
      return 'success'
    case 'refused':
      return 'error'
    case 'pending':
      return 'warning'
    default:
      return 'grey'
  }
}

function getStatusColor(status: string) {
  switch (status) {
    case 'undo':
      return 'warning'
    case 'completed':
      return 'success'
    default:
      return 'grey'
  }
}

function getStatusName(status: string) {
  switch (status) {
    case 'undo':
      return '未完成'
    case 'completed':
      return '已完成'
    default:
      return status
  }
}

function goToTaskDetail(task: Task) {
  router.push(`/task/detail/${task.manual_review_id}`)
}

function handleTimeRangeChange(value: string | null) {
  if (value) {
    filters.value.startDate = null
    filters.value.endDate = null
    timeError.value = ''
  }
}

function handleCustomTimeChange() {
  filters.value.timeRange = null
  if (!filters.value.startDate || !filters.value.endDate) {
    timeError.value = '开始时间和结束时间不能为空'
    return
  }
  const startTime = new Date(filters.value.startDate).getTime()
  const endTime = new Date(filters.value.endDate).getTime()
  timeError.value = startTime >= endTime ? '开始时间必须早于结束时间' : ''
}

function resetFilters() {
  filters.value = {
    taskKind: null,
    status: null,
    reviewRequestStatus: null,
    adminGateStatus: null,
    timeRange: null,
    startDate: null,
    endDate: null,
  }
  timeError.value = ''
  currentPage.value = 1
  fetchTasks(1, pageSize.value)
  showFilterDialog.value = false
}

function applyFilters() {
  if (timeError.value) return
  currentPage.value = 1
  fetchTasks(1, pageSize.value)
  showFilterDialog.value = false
}

function handleSearch() {
  currentPage.value = 1
  fetchTasks(1, pageSize.value)
}

function formatDateFilter(timestamp: number) {
  const date = new Date(timestamp)
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const h = String(date.getHours()).padStart(2, '0')
  const mi = String(date.getMinutes()).padStart(2, '0')
  const s = String(date.getSeconds()).padStart(2, '0')
  return `${y}-${m}-${d} ${h}:${mi}:${s}`
}

async function fetchTasks(page: number, size: number) {
  loading.value = true
  try {
    let startTimeFilter: string | undefined
    let endTimeFilter: string | undefined
    if (filters.value.timeRange) {
      const now = Date.now()
      const ranges: Record<string, number> = {
        '1d': 24 * 60 * 60 * 1000,
        '7d': 7 * 24 * 60 * 60 * 1000,
        '30d': 30 * 24 * 60 * 60 * 1000,
        '90d': 90 * 24 * 60 * 60 * 1000,
        '365d': 365 * 24 * 60 * 60 * 1000,
      }
      const rangeMs = ranges[filters.value.timeRange as keyof typeof ranges]
      startTimeFilter = formatDateFilter(now - rangeMs)
      endTimeFilter = formatDateFilter(now)
    } else if (filters.value.startDate && filters.value.endDate) {
      startTimeFilter = formatDateFilter(new Date(filters.value.startDate).getTime())
      endTimeFilter = formatDateFilter(new Date(filters.value.endDate).getTime())
    }

    const params: Record<string, string | number> = {
      page,
      page_size: size,
      query: searchQuery.value || '',
      status: filters.value.status || '',
      start_time: startTimeFilter || '',
      end_time: endTimeFilter || '',
      review_request_status: filters.value.reviewRequestStatus || '',
      admin_gate_status: filters.value.adminGateStatus || '',
    }
    if (filters.value.taskKind) {
      params.task_kind = filters.value.taskKind
    }

    const response = await reviewerApi.getReviewerTasks(params)
    const {
      results: taskList,
      current_page,
      total_pages,
      total_count,
    } = response.data

    tasks.value = (taskList || [])
      .filter((task: Task) => !filters.value.taskKind || task.task_kind === filters.value.taskKind)
      .map((task: Task) => ({
        ...task,
        publisher_avatar: task.publisher_avatar,
      }))

    currentPage.value = current_page
    totalPages.value = total_pages
    totalTasks.value = total_count ?? 0
  } catch (error) {
    console.error(error)
    snackbar.showMessage('获取任务列表失败', 'error')
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  fetchTasks(page, pageSize.value)
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  fetchTasks(1, size)
}

onMounted(() => {
  if (isPreviewMode.value) return
  fetchTasks(currentPage.value, pageSize.value)
})
</script>

<style scoped>
.search-input {
  max-width: 420px;
}

.review-task-table :deep(th) {
  font-weight: 600;
  white-space: nowrap !important;
}

</style>
