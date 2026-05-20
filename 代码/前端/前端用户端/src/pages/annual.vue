<template>
  <div class="annual-page">
    <v-row class="mb-2">
      <v-col>
        <h1 class="text-h4 font-weight-bold">人工审核申请</h1>
        <p class="text-body-2 text-medium-emphasis mb-0">
          发布者（编辑）侧：发起人工审核申请 → 组织管理员审批 → 专家鉴定 → <strong>本页查看进度与最终结果</strong>。
          专家提交后请点击「查看结果」进入汇总页（<code>/manual-review-result</code>）。
        </p>
      </v-col>
    </v-row>

    <v-alert
      v-if="fromTaskId"
      type="info"
      variant="tonal"
      density="comfortable"
      class="mb-4 text-body-2"
      closable
      @click:close="clearFromTaskHint"
    >
      您从检测任务 <code>{{ fromTaskId }}</code> 跳转而来；可直接点击「发起人工审核申请」预填该任务 ID，或在下列列表中跟踪进度。
    </v-alert>

    <v-row class="mb-4">
      <v-col cols="12" class="d-flex flex-wrap align-center ga-2 justify-space-between">
        <div class="d-flex flex-wrap ga-2">
          <v-btn color="primary" class="text-none" prepend-icon="mdi-plus-circle-outline" @click="openCreateDialog">
            发起人工审核申请
          </v-btn>
        </div>
        <v-btn color="primary" variant="tonal" class="text-none" prepend-icon="mdi-filter-variant" @click="showFilterDialog = true">
          筛选
        </v-btn>
      </v-col>
    </v-row>

    <v-card class="elevation-2">
      <v-data-table
        :headers="headers"
        :items="tasks"
        class="elevation-0"
        :items-per-page="pageSize"
        hover
        :width="'100%'"
        :loading="loading"
        hide-default-footer
      >
        <template v-slot:top>
          <div class="d-flex align-center pa-4">
            <div class="text-caption text-medium-emphasis">
              共 {{ totalTasks }} 条记录
            </div>
          </div>
        </template>

        <template v-slot:item.status="{ item }">
          <v-chip
            :color="getStatusColor(item.status)"
            size="small"
            class="status-chip"
          >
            {{ getStatusName(item.status) }}
          </v-chip>
        </template>

        <template v-slot:item.progress="{ item }">
          <div class="d-flex align-center">
            <v-progress-linear
              :model-value="getProgressValue(item.progress)"
              :color="getProgressColor(item.progress)"
              height="20"
            >
              <template v-slot:default="{ value }">
                <span class="text-caption">{{ item.progress }}</span>
              </template>
            </v-progress-linear>
          </div>
        </template>

        <template v-slot:item.detection_task_id="{ item }">
          <code class="text-body-2">{{ item.detection_task_id || '—' }}</code>
        </template>

        <template v-slot:item.actions="{ item }">
          <div class="d-flex flex-wrap justify-center ga-1">
            <v-btn
              size="small"
              variant="tonal"
              color="primary"
              class="text-none"
              :disabled="!canViewResult(item)"
              @click="goToReviewResult(item)"
            >
              查看结果
            </v-btn>
            <v-btn
              size="small"
              variant="outlined"
              color="secondary"
              class="text-none"
              :disabled="!canDownloadReport(item)"
              :loading="downloadingReportId === item.review_request_id"
              @click="downloadManualReport(item)"
            >
              下载报告
            </v-btn>
            <v-btn
              size="small"
              variant="text"
              color="error"
              class="text-none"
              :disabled="!canTerminate(item)"
              @click="terminateReview(item)"
            >
              终止审核
            </v-btn>
          </div>
        </template>
      </v-data-table>
      
      <div class="d-flex align-center justify-center pa-4">
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
          ></v-select>
          <span class="text-caption ml-2">条</span>
        </div>
        <v-pagination
          v-model="currentPage"
          :length="totalPages"
          :total-visible="7"
          class="ml-4"
          @update:model-value="handlePageChange"
        ></v-pagination>
      </div>
    </v-card>

    <!-- 发起申请 -->
    <v-dialog v-model="showCreateDialog" max-width="560" persistent>
      <v-card>
        <v-card-title class="text-h6 font-weight-bold">发起人工审核申请</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="createForm.detection_task_id"
            label="关联自动检测任务 ID *"
            variant="outlined"
            density="comfortable"
            hide-details="auto"
            class="mb-3"
          />
          <v-select
            v-model="createForm.task_type"
            :items="taskTypeItems"
            label="任务类型 *"
            variant="outlined"
            density="comfortable"
            hide-details="auto"
            class="mb-3"
          />
          <v-textarea
            v-model="createForm.reason"
            label="申请理由 *（建议不少于 10 字）"
            variant="outlined"
            rows="4"
            hide-details="auto"
            class="mb-3"
          />
          <v-select
            v-model="createForm.priority"
            :items="priorityItems"
            label="优先级"
            variant="outlined"
            density="comfortable"
            hide-details="auto"
            class="mb-3"
          />
          <v-text-field
            v-model="createForm.batch_session_id"
            label="统一检测批次 ID（可选）"
            variant="outlined"
            density="comfortable"
            hide-details="auto"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="createSubmitting" @click="showCreateDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="createSubmitting" @click="submitCreate">提交申请</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 筛选对话框 -->
    <v-dialog v-model="showFilterDialog" max-width="500">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">筛选条件</v-card-title>
        <v-card-text>
          <div class="d-flex flex-column gap-4">
            <v-select
              v-model="filters.status"
              :items="statusOptions"
              label="任务状态"
              clearable
              hide-details
            ></v-select>
            
            <v-select
              v-model="filters.timeRange"
              :items="timeRangeOptions"
              label="快速选择时间范围"
              clearable
              hide-details
              @update:model-value="handleTimeRangeChange"
            ></v-select>

            <div class="d-flex align-center gap-4">
              <v-text-field
                v-model="filters.startDate"
                label="开始时间"
                type="datetime-local"
                hide-details
                density="compact"
                :error-messages="timeError"
                @update:model-value="handleCustomTimeChange"
              ></v-text-field>
              <v-text-field
                v-model="filters.endDate"
                label="结束时间"
                type="datetime-local"
                hide-details
                density="compact"
                :error-messages="timeError"
                @update:model-value="handleCustomTimeChange"
              ></v-text-field>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="resetFilters">重置</v-btn>
          <v-btn color="primary" @click="applyFilters">应用</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  createManualReviewRequest,
  listPublisherManualReviewApplications,
} from '@/api/manualReviewWorkflow'
import platform from '@/api/platform'
import publisher from '@/api/publisher'
import { useSnackbarStore } from '@/stores/snackbar'
import { useUserStore } from '@/stores/user'
import { savePdfFromAxiosResponse } from '@/utils/downloadPdf'
const router = useRouter()
const route = useRoute()
const snackbar = useSnackbarStore()
const userStore = useUserStore()

const showCreateDialog = ref(false)
const createSubmitting = ref(false)
const createForm = ref({
  detection_task_id: '',
  task_type: 'image_detection',
  reason: '',
  priority: 'normal' as 'normal' | 'urgent',
  batch_session_id: '',
})

const taskTypeItems = [
  { title: '图像检测', value: 'image_detection' },
  { title: '论文 AIGC', value: 'paper_aigc' },
  { title: '学术资源', value: 'resource_check' },
  { title: 'Review 检测', value: 'review_detection' },
]

const priorityItems = [
  { title: '普通', value: 'normal' },
  { title: '加急', value: 'urgent' },
]

function openCreateDialog() {
  createForm.value.detection_task_id = fromTaskId.value || ''
  createForm.value.reason = ''
  createForm.value.batch_session_id = ''
  createForm.value.priority = 'normal'
  createForm.value.task_type = 'image_detection'
  showCreateDialog.value = true
}

async function submitCreate() {
  const tid = createForm.value.detection_task_id.trim()
  const reason = createForm.value.reason.trim()
  if (!tid) {
    snackbar.showMessage('请填写关联检测任务 ID', 'warning')
    return
  }
  if (reason.length < 10) {
    snackbar.showMessage('申请理由请至少 10 个字', 'warning')
    return
  }
  createSubmitting.value = true
  try {
    await createManualReviewRequest({
      detection_task_id: tid,
      task_type: createForm.value.task_type,
      reason,
      priority: createForm.value.priority,
      batch_session_id: createForm.value.batch_session_id.trim() || undefined,
    })
    snackbar.showMessage('人工审核申请已提交', 'success')
    showCreateDialog.value = false
    await fetchTasks(currentPage.value, pageSize.value)
  } catch {
    snackbar.showMessage('提交失败，请确认 Django 已启动且 POST /manual-review-requests/ 可用', 'error')
  } finally {
    createSubmitting.value = false
  }
}

const fromTaskId = computed(() => {
  const raw = route.query.task_id
  if (raw == null || Array.isArray(raw)) return ''
  const s = String(raw).trim()
  return s || ''
})

function clearFromTaskHint() {
  router.replace({ path: '/annual', query: {} })
}

interface Task {
  review_request_id: number
  detection_task_id: string
  task_type: string
  request_time: string
  status: string
  progress: string
}

const headers = [
  { title: '申请单号', key: 'review_request_id', align: 'start' as const },
  { title: '检测任务 ID', key: 'detection_task_id', align: 'center' as const },
  { title: '提交时间', key: 'request_time', align: 'center' as const },
  { title: '状态', key: 'status', align: 'center' as const },
  { title: '专家进度', key: 'progress', align: 'center' as const },
  { title: '操作', key: 'actions', align: 'center' as const, sortable: false },
]

// 分页相关
const tasks = ref<Task[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const totalTasks = ref(0)
const totalPages = ref(1)

// 筛选相关
const showFilterDialog = ref(false)
const filters = ref<{
  status: string | null
  timeRange: string | null
  startDate: string | null
  endDate: string | null
}>({
  status: null,
  timeRange: null,
  startDate: null,
  endDate: null
})

const statusOptions = [
  { title: '待管理端审批', value: 'pending' },
  { title: '专家审核中', value: 'in_progress' },
  { title: '已完成', value: 'completed' },
  { title: '管理端已拒绝', value: 'failed' },
]

const timeRangeOptions = [
  { title: '最近一天', value: '1d' },
  { title: '最近一周', value: '7d' },
  { title: '最近一月', value: '30d' },
  { title: '最近三月', value: '90d' },
  { title: '最近一年', value: '365d' }
]

const getStatusColor = (status: string) => {
  switch (status) {
    case 'pending':
      return 'warning'
    case 'in_progress':
      return 'info'
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    case 'cancelled':
      return 'grey'
    default:
      return 'grey'
  }
}

const getStatusName = (status: string) => {
  switch (status) {
    case 'pending':
      return '待管理端审批'
    case 'in_progress':
      return '专家审核中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '管理端已拒绝'
    case 'cancelled':
      return '已终止'
    default:
      return status
  }
}

function canTerminate(item: Task) {
  return item.status === 'pending' || item.status === 'in_progress'
}

async function terminateReview(item: Task) {
  if (!confirm('确定终止该人工审核？终止后专家将无法继续提交。')) return
  try {
    await platform.cancelManualReview(item.review_request_id)
    snackbar.showMessage('已终止', 'success')
    await fetchTasks(currentPage.value, pageSize.value)
  } catch {
    snackbar.showMessage('终止失败', 'error')
  }
}

const getProgressValue = (progress: string) => {
  const [completed, total] = progress.split('/').map(Number)
  if (!total || Number.isNaN(completed) || Number.isNaN(total)) return 0
  return Math.round((completed / total) * 100)
}

const getProgressColor = (progress: string) => {
  const [completed, total] = progress.split('/').map(Number)
  if (!total) return 'grey'
  if (completed >= total) return 'success'
  if (completed > 0) return 'info'
  return 'warning'
}

function canViewResult(item: Task) {
  return item.status === 'completed'
}

function canDownloadReport(item: Task) {
  return item.status === 'completed' || item.status === 'in_progress'
}

const downloadingReportId = ref<number | null>(null)

function formatReportDownloadError(e: unknown): string {
  const ax = e as {
    response?: { status?: number; data?: Blob | { detail?: string } }
  }
  const d = ax.response?.data
  if (d && typeof d === 'object' && 'detail' in d && typeof d.detail === 'string') {
    return d.detail
  }
  if (d instanceof Blob) {
    return '报告生成失败（请重启 Django 后重试）'
  }
  if (ax.response?.status === 202) {
    return '报告正在生成，请稍后重试'
  }
  return '报告下载失败，请确认专家已提交且后端服务正常'
}

async function downloadManualReport(item: Task) {
  if (!canDownloadReport(item)) return
  downloadingReportId.value = item.review_request_id
  try {
    const res = await publisher.downloadReviewReport({ review_request_id: item.review_request_id })
    savePdfFromAxiosResponse(res, `manual_review_${item.review_request_id}_report.pdf`)
    snackbar.showMessage('人工审核报告已下载', 'success')
  } catch (e) {
    snackbar.showMessage(formatReportDownloadError(e), 'error')
  } finally {
    downloadingReportId.value = null
  }
}

function goToReviewResult(task: Task) {
  router.push({
    path: '/manual-review-result',
    query: {
      review_request_id: String(task.review_request_id),
      task_id: task.detection_task_id || '',
      task_type: task.task_type || 'image_detection',
    },
  })
}

function formatLoadListError(e: unknown): string {
  const ax = e as { response?: { status?: number; data?: { error?: string; message?: string } } }
  const status = ax.response?.status
  const d = ax.response?.data
  if (status === 403) {
    return '当前账号不是发布者（编辑）。请使用 publisher_test@example.com 登录并选择「编辑」。'
  }
  if (typeof d?.error === 'string') return d.error
  if (typeof d?.message === 'string') return d.message
  return '获取任务列表失败，请确认已用编辑账号登录且 Django 已启动'
}

// 时间验证相关
const timeError = ref('')

// 处理快速选择时间范围变化
const handleTimeRangeChange = (value: string | null) => {
  if (value) {
    filters.value.startDate = null
    filters.value.endDate = null
    timeError.value = ''
  }
}

// 处理自定义时间变化
const handleCustomTimeChange = () => {
  filters.value.timeRange = null
  
  if (!filters.value.startDate || !filters.value.endDate) {
    timeError.value = '开始时间和结束时间不能为空'
    return
  }

  const startTime = new Date(filters.value.startDate).getTime()
  const endTime = new Date(filters.value.endDate).getTime()
  
  if (startTime >= endTime) {
    timeError.value = '开始时间必须早于结束时间'
  } else {
    timeError.value = ''
  }
}

// 重置筛选条件
const resetFilters = () => {
  filters.value = {
    status: null,
    timeRange: null,
    startDate: null,
    endDate: null
  }
  timeError.value = ''
  currentPage.value = 1
  pageSize.value = 10
  fetchTasks(1, 10)
  showFilterDialog.value = false
}

// 应用筛选条件
const applyFilters = () => {
  if (timeError.value) {
    return
  }
  
  currentPage.value = 1
  pageSize.value = 10
  fetchTasks(1, 10)
  showFilterDialog.value = false
}

// 从后端获取任务数据
const fetchTasks = async (page: number, pageSize: number) => {
  loading.value = true
  try {
    // 计算时间筛选
    let startTimeFilter: string | undefined
    let endTimeFilter: string | undefined
    if (filters.value.timeRange) {
      const now = Date.now()
      const ranges: Record<string, number> = {
        '1d': 24 * 60 * 60 * 1000,
        '7d': 7 * 24 * 60 * 60 * 1000,
        '30d': 30 * 24 * 60 * 60 * 1000,
        '90d': 90 * 24 * 60 * 60 * 1000,
        '365d': 365 * 24 * 60 * 60 * 1000
      }
      const rangeMs = ranges[filters.value.timeRange as keyof typeof ranges]
      startTimeFilter = formatDateFilter(now - rangeMs)
      endTimeFilter = formatDateFilter(now)
    } else if (filters.value.startDate && filters.value.endDate) {
      startTimeFilter = formatDateFilter(new Date(filters.value.startDate).getTime())
      endTimeFilter = formatDateFilter(new Date(filters.value.endDate).getTime())
    }

    const params = {
      page,
      page_size: pageSize,
      status: filters.value.status || '',
      startTime: startTimeFilter,
      endTime: endTimeFilter
    }
    const response = await listPublisherManualReviewApplications(params)
    const data = response.data as Record<string, unknown>
    const taskList = Array.isArray(data.tasks) ? data.tasks : []
    const current_page = Number(data.current_page) || page
    const total_pages = Number(data.total_pages) || 1
    const total_count = Number(data.total_count ?? data.total_tasks ?? taskList.length)
    
    tasks.value = taskList.map((task: Record<string, unknown>) => ({
      review_request_id: Number(task.review_request_id),
      detection_task_id: String(task.detection_task_id ?? ''),
      task_type: String(task.task_type ?? ''),
      request_time: String(task.request_time ?? ''),
      status: String(task.status ?? ''),
      progress: String(task.progress ?? '0/1'),
    }))
    
    currentPage.value = current_page
    totalPages.value = total_pages
    totalTasks.value = total_count
  } catch (error) {
    console.error('获取任务列表失败:', error)
    tasks.value = []
    totalTasks.value = 0
    snackbar.showMessage(formatLoadListError(error), 'error')
  } finally {
    loading.value = false
  }
}

// 处理页码变化
const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchTasks(page, pageSize.value)
}

// 处理每页数量变化
const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchTasks(1, size)
}

// 时间格式化，用于筛选条件
const formatDateFilter = (timestamp: number) => {
  const date = new Date(timestamp)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

onMounted(async () => {
  if (!userStore.isLoaded) {
    await userStore.fetchUserInfo()
  }
  if (userStore.role !== 'publisher') {
    snackbar.showMessage('人工审核申请页仅供发布者（编辑）使用', 'warning')
    return
  }
  fetchTasks(currentPage.value, pageSize.value)
})
</script>

<style scoped>
.v-card {
  border-radius: 12px;
  overflow: hidden;
}

.status-chip {
  font-size: 12px;
  padding: 0 12px;
  font-weight: 500;
}

.v-btn.v-btn--size-small {
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 8px;
}

.v-btn--icon.v-btn--size-small .v-icon {
  font-size: 18px;
}

:deep(.v-data-table) {
  border-radius: 12px;
  width: 100%;
}

:deep(.v-data-table-header) {
  background-color: rgb(var(--v-theme-surface-variant));
}

:deep(.v-data-table-header th) {
  font-weight: 600;
  font-size: 14px;
  color: rgb(var(--v-theme-on-surface));
  white-space: nowrap;
}

:deep(.v-data-table__tr td) {
  white-space: nowrap;
}

:deep(.v-data-table__tr:hover) {
  background-color: rgba(var(--v-theme-on-surface), 0.04);
}

:deep(.v-chip) {
  font-weight: 500;
}

:deep(.v-text-field .v-field__input) {
  min-height: 40px;
}

:deep(.v-btn--variant-outlined) {
  border-color: rgb(var(--v-theme-outline));
}

:deep(.v-select .v-field__input) {
  min-height: 40px;
}

:deep(.v-select .v-field__append-inner) {
  padding-top: 0;
}

:deep(.v-progress-linear) {
  border-radius: 10px;
}

:deep(.v-progress-linear__content) {
  color: white;
  font-weight: 500;
}
</style>