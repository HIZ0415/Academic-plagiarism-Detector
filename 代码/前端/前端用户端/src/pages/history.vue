<template>
  <v-card flat border="0">
    <template v-if="detailId">
      <v-card-title class="d-flex align-center pa-0">
        <div>
          <div class="text-h5 font-weight-bold">检测记录详情</div>
          <div class="text-body-2 text-medium-emphasis">任务 ID：{{ detailTask.task_id }}</div>
        </div>
        <v-spacer></v-spacer>
        <v-chip :color="getStatusColor(detailTask.status)" size="small">{{ getStatus(detailTask.status) }}</v-chip>
      </v-card-title>

      <v-card-text class="pa-0 mt-4">
        <v-row>
          <v-col cols="12" md="12">
            <v-card variant="outlined" class="pa-4 mb-4">
              <div class="text-subtitle-1 font-weight-bold mb-3">任务概览</div>
              <v-row>
                <v-col cols="12" md="3" class="text-body-2">类型：{{ getTaskTypeLabel(detailTask.task_type) }}</v-col>
                <v-col cols="12" md="3" class="text-body-2">状态：{{ getStatus(detailTask.status) }}</v-col>
                <v-col cols="12" md="3" class="text-body-2">进度：{{ detailTask.progress || 0 }}%</v-col>
                <v-col cols="12" md="3" class="text-body-2">时间：{{ formatDateTime(detailTask.upload_time) || '暂无' }}</v-col>
              </v-row>
              <v-alert v-if="detailTask.error_message" type="error" variant="tonal" class="mt-3">
                {{ detailTask.error_message }}
              </v-alert>
            </v-card>

            <v-card variant="outlined" class="pa-4 mb-4">
              <div class="text-subtitle-1 font-weight-bold mb-3">图片检测结果</div>
              <v-row>
                <v-col cols="12" md="4"><div class="text-body-2">总图片数：{{ unifiedResult.image.total }}</div></v-col>
                <v-col cols="12" md="4"><div class="text-body-2">疑似造假：{{ unifiedResult.image.suspicious }}</div></v-col>
                <v-col cols="12" md="4"><div class="text-body-2">正常图片：{{ unifiedResult.image.normal }}</div></v-col>
              </v-row>
            </v-card>

            <v-card variant="outlined" class="pa-4 mb-4">
              <div class="text-subtitle-1 font-weight-bold mb-3">论文检测结果</div>
              <v-row>
                <v-col cols="12" md="4"><div class="text-body-2">AIGC 风险：{{ unifiedResult.paper.riskLevel }}</div></v-col>
                <v-col cols="12" md="4"><div class="text-body-2">AI 占比：{{ unifiedResult.paper.aiRatio }}%</div></v-col>
                <v-col cols="12" md="4"><div class="text-body-2">高风险段落：{{ unifiedResult.paper.highRiskParagraphs }}</div></v-col>
              </v-row>
            </v-card>

            <v-card variant="outlined" class="pa-4 mb-4">
              <div class="text-subtitle-1 font-weight-bold mb-3">Review 检测结果</div>
              <v-row>
                <v-col cols="12" md="4"><div class="text-body-2">模板化风险：{{ unifiedResult.review.templateRisk }}</div></v-col>
                <v-col cols="12" md="4"><div class="text-body-2">文本异常片段：{{ unifiedResult.review.anomalySegments }}</div></v-col>
                <v-col cols="12" md="4"><div class="text-body-2">综合建议：{{ unifiedResult.review.suggestion }}</div></v-col>
              </v-row>
            </v-card>

            <v-card variant="outlined" class="pa-4 mb-4">
              <div class="text-subtitle-1 font-weight-bold mb-3">人工审核流程</div>
              <v-stepper :model-value="manualReviewStep" flat>
                <v-stepper-header>
                  <v-stepper-item :value="1" title="发起申请" />
                  <v-divider />
                  <v-stepper-item :value="2" title="管理员审批" />
                  <v-divider />
                  <v-stepper-item :value="3" title="审核员执行" />
                  <v-divider />
                  <v-stepper-item :value="4" title="结果回传" />
                </v-stepper-header>
              </v-stepper>
              <v-alert type="info" variant="tonal" class="mt-3">
                当前阶段：{{ manualReviewStageText }}
              </v-alert>
              <div class="text-body-2 mt-2">
                说明：当你对自动检测结果存在疑问时，可发起人工审核，由管理员审批后分配审核员进行逐项复核。
              </div>
            </v-card>

            <v-card variant="outlined" class="pa-4">
              <div class="d-flex flex-wrap ga-3">
                <v-btn color="primary" :disabled="detailTask.status !== 'completed'" @click="goSpecialDetail(detailTask)">
                  进入专项详情
                </v-btn>
                <v-btn color="success" variant="outlined" :disabled="detailTask.status !== 'completed'" @click="goManualReview">
                  进入人工审核
                </v-btn>
                <v-btn variant="outlined" @click="backToList">返回历史列表</v-btn>
              </div>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </template>
    <template v-else>
    <!-- 任务详情弹窗 -->
    <v-dialog v-model="showDetail" max-width="800" persistent>
      <task-detail v-if="showDetail" :task="currentTask" @close="showDetail = false" />
    </v-dialog>

    <v-card-title class="d-flex align-center pa-0">
      <h1 class="text-h4 font-weight-bold">检测历史</h1>
      <v-spacer></v-spacer>
      <v-btn variant="outlined" class="mr-2" @click="showFilter = true"
        :color="hasActiveFilters ? 'primary' : undefined">
        <v-icon class="mr-2">mdi-filter</v-icon>
        筛选
      </v-btn>
      <!-- <v-btn variant="outlined">新建</v-btn> -->
    </v-card-title>

    <!-- 筛选对话框 -->
    <v-dialog v-model="showFilter" max-width="500">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">筛选条件</v-card-title>
        <v-card-text>
          <div class="d-flex flex-column gap-4">
            <v-select v-model="filters.status" :items="statusOptions" label="任务状态" clearable hide-details></v-select>

            <v-select v-model="filters.timeRange" :items="timeRangeOptions" label="快速选择时间范围" clearable hide-details
              @update:model-value="handleTimeRangeChange"></v-select>

            <div class="d-flex align-center gap-4">
              <v-text-field v-model="filters.startDate" label="开始时间" type="datetime-local" hide-details
                density="compact" :error-messages="timeError"
                @update:model-value="handleCustomTimeChange"></v-text-field>
              <v-text-field v-model="filters.endDate" label="结束时间" type="datetime-local" hide-details density="compact"
                :error-messages="timeError" @update:model-value="handleCustomTimeChange"></v-text-field>
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

    <v-card-text class="pa-0 mt-4">
      <v-data-table v-model="selected" :headers="headers" :items="filteredTasks" :items-per-page="10"
        class="elevation-1" :show-select="showSelection" item-value="id" hide-default-footer>
        <!-- 任务状态列自定义 -->
        <template v-slot:item.task_id="{ item }">
          <span>{{ item.task_id }}</span>
        </template>

        <template v-slot:item.upload_time="{ item }">
          <span>{{ formatDateTime(item.upload_time) }}</span>
        </template>

        <template v-slot:item.completion_time="{ item }">
          <span>{{ formatDateTime(item.completion_time) }}</span>
        </template>

        <template v-slot:item.status="{ item }">
          <div class="d-flex justify-center">
            <v-chip :color="getStatusColor(item.status)" size="small" class="operation-chip">
              {{ getStatus(item.status) }}
            </v-chip>
          </div>
        </template>

        <!-- 操作列自定义 -->
        <template v-slot:item.actions="{ item }">
          <div class="d-flex justify-center gap-2">
            <v-btn size="small" color="primary" variant="text" @click="handleNext(item)"
              :disabled="!canEnterDetail(item)">
              下一步
            </v-btn>
            <v-btn size="small" color="error" variant="text" @click="handleDelete(item)"
              :disabled="item.status !== 'completed'">
              删除
            </v-btn>
          </div>
        </template>

        <template v-slot:top>
          <div class="d-flex align-center pa-4">
            <div class="text-caption text-medium-emphasis">
              共 {{ totalTasks }} 条记录
            </div>
          </div>
        </template>
      </v-data-table>

      <div class="d-flex align-center justify-center pa-4">
        <div class="d-flex align-center">
          <span class="text-caption mr-2">每页显示</span>
          <v-select v-model="pageSize" :items="[5, 10, 20, 50, 100]" density="compact" variant="outlined" hide-details
            style="width: 100px" @update:model-value="handlePageSizeChange"></v-select>
          <span class="text-caption ml-2">条</span>
        </div>
        <v-pagination v-model="currentPage" :length="totalPages" :total-visible="7" class="ml-4"
          @update:model-value="handlePageChange"></v-pagination>
      </div>

    </v-card-text>
    </template>
  </v-card>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSnackbarStore } from '@/stores/snackbar'
import publisher from '@/api/publisher'

const router = useRouter()
const route = useRoute()
const snackbar = useSnackbarStore()
const useMockAigc = import.meta.env.VITE_USE_MOCK_AIGC === 'true'

// 分页相关
const pageSize = ref(10)
const currentPage = ref(1)
const totalTasks = ref(0)
const totalPages = ref(1)
const loading = ref(false)

// 表格列定义
const headers = [
  { title: '任务ID', key: 'task_id', align: 'center' as const, width: '120px' },
  { title: '上传时间', key: 'upload_time', align: 'center' as const, width: '180px' },
  { title: '完成时间', key: 'completion_time', align: 'center' as const, width: '180px' },
  { title: '检测状态', key: 'status', align: 'center' as const, width: '200px' },
  { title: '操作', key: 'actions', sortable: false, align: 'center' as const, width: '350px' }
]

interface Task {
  task_id: string
  upload_time: string
  completion_time: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  task_type?: string
  progress?: number
  source?: 'server' | 'local'
  error_message?: string
}

// 任务数据
const tasks = ref<Task[]>([])

// 筛选相关
const showFilter = ref(false)
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

// 时间验证相关
const timeError = ref('')

const statusOptions = [
  { title: '排队中', value: 'pending' },
  { title: '进行中', value: 'in_progress' },
  { title: '已完成', value: 'completed' }
] as const

const timeRangeOptions = [
  { title: '最近一天', value: '1d' },
  { title: '最近一周', value: '7d' },
  { title: '最近一月', value: '30d' },
  { title: '最近三月', value: '90d' },
  { title: '最近一年', value: '365d' }
]

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

  // 检查是否都为空或都存在
  if ((!filters.value.startDate && filters.value.endDate) ||
    (filters.value.startDate && !filters.value.endDate)) {
    timeError.value = '开始时间和结束时间必须同时设置或同时为空'
    return
  }

  // 如果都为空，清除错误信息
  if (!filters.value.startDate && !filters.value.endDate) {
    timeError.value = ''
    return
  }

  const startTime = new Date(filters.value.startDate!).getTime()
  const endTime = new Date(filters.value.endDate!).getTime()

  if (startTime >= endTime) {
    timeError.value = '开始时间必须早于结束时间'
  } else {
    timeError.value = ''
  }
}

// 从后端获取任务数据
const fetchTasks = async (page: number, pageSize: number) => {
  loading.value = true
  try {
    // 构建筛选参数
    const params: any = {
      page,
      page_size: pageSize
    }

    // 添加状态筛选
    if (filters.value.status) {
      params.status = filters.value.status
    }

    // 添加时间范围筛选
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
      params.startTime = formatDateFilter(now - rangeMs)
      params.endTime = formatDateFilter(now)
    } else if (filters.value.startDate && filters.value.endDate) {
      params.startTime = formatDateFilter(new Date(filters.value.startDate).getTime())
      params.endTime = formatDateFilter(new Date(filters.value.endDate).getTime())
    }

    const response = await publisher.getAllDetectionTask(params)
    const { tasks: taskList, current_page, total_pages, total_tasks } = response.data

    const remoteTasks: Task[] = taskList.map((task: any) => ({
      task_id: task.task_id,
      upload_time: task.upload_time,
      completion_time: task.completion_time,
      status: task.status,
      task_type: task.task_type || 'image_detection',
      progress: task.status === 'completed' ? 100 : task.status === 'in_progress' ? 60 : 20,
      source: 'server',
      error_message: task.error_message || '',
    }))

    const localTasksRaw = JSON.parse(localStorage.getItem('local_detection_tasks') || '[]') as any[]
    const localTasks: Task[] = localTasksRaw.map((t) => ({
      task_id: String(t.task_id),
      upload_time: String(t.upload_time || ''),
      completion_time: String(t.completion_time || ''),
      status: t.status || 'pending',
      task_type: t.task_type || 'unknown',
      progress: Number(t.progress || 0),
      source: 'local',
      error_message: t.error_message || '',
    }))

    const merged = [...remoteTasks]
    const remoteIds = new Set(remoteTasks.map((t) => String(t.task_id)))
    for (const local of localTasks) {
      if (!remoteIds.has(String(local.task_id))) merged.unshift(local)
    }

    tasks.value = merged

    currentPage.value = current_page
    totalPages.value = total_pages
    totalTasks.value = Math.max(total_tasks, merged.length)
  } catch (error) {
    console.error('获取任务列表失败:', error)
    snackbar.showMessage('获取任务列表失败', 'error')
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
  currentPage.value = 1 // 重置到第一页
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

// 初始化
onMounted(() => {
  fetchTasks(currentPage.value, pageSize.value)
})

const getStatus = (status: string) => {
  switch (status) {
    case 'pending':
      return '排队中'
    case 'in_progress':
      return '进行中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    default:
      return '未知'
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'pending':
      return 'yellow'
    case 'in_progress':
      return 'info'
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    default:
      return 'grey'
  }
}

// 选择相关状态
const showSelection = ref(false)
const selected = ref([])

// 控制详情页显示
const showDetail = ref(false)
const currentTask = ref<any>(null)

// 判断是否有激活的筛选条件
const hasActiveFilters = computed(() => {
  return filters.value.startDate ||
    filters.value.endDate ||
    filters.value.status !== null
})

// 筛选后的任务列表
const filteredTasks = computed(() => {
  return tasks.value
})

const detailId = computed(() => String(route.query.detail_id || ''))

const detailTask = computed<Task>(() => {
  const fallback: Task = {
    task_id: detailId.value,
    upload_time: String(route.query.upload_time || ''),
    completion_time: String(route.query.completion_time || ''),
    status: (String(route.query.status || 'pending') as Task['status']),
    task_type: String(route.query.task_type || 'unknown'),
    progress: Number(route.query.progress || 0),
    source: 'local',
    error_message: String(route.query.error_message || ''),
  }
  if (!detailId.value) return fallback
  return tasks.value.find((t) => String(t.task_id) === detailId.value) || fallback
})

const unifiedResult = computed(() => {
  const seed = Number(String(detailTask.value.task_id).replace(/\D/g, '').slice(-2) || '7')
  const imageTotal = Math.max(3, (seed % 8) + 3)
  const imageSuspicious = Math.min(imageTotal, Math.max(1, seed % 4))
  const riskLevels = ['低', '中', '高'] as const
  const templateRiskLevels = ['低', '中', '高'] as const
  return {
    image: {
      total: imageTotal,
      suspicious: imageSuspicious,
      normal: imageTotal - imageSuspicious,
    },
    paper: {
      riskLevel: riskLevels[seed % 3],
      aiRatio: Math.min(95, 25 + (seed % 60)),
      highRiskParagraphs: (seed % 5) + 1,
    },
    review: {
      templateRisk: templateRiskLevels[(seed + 1) % 3],
      anomalySegments: (seed % 4) + 1,
      suggestion: seed % 2 === 0 ? '建议人工复核' : '可直接通过',
    },
  }
})

const resetFilters = () => {
  filters.value = {
    status: null,
    timeRange: null,
    startDate: null,
    endDate: null
  }
  timeError.value = ''
  // 重置到第一页并重新获取数据
  currentPage.value = 1
  fetchTasks(1, pageSize.value)
}

const applyFilters = () => {
  if (timeError.value) {
    return
  }
  showFilter.value = false
  // 重置到第一页并重新获取数据
  currentPage.value = 1
  fetchTasks(1, pageSize.value)
}

// 操作按钮处理函数
const handleNext = (item: Task) => {
  router.push({
    path: '/history',
    query: {
      detail_id: item.task_id,
      task_type: item.task_type || 'unknown',
      status: item.status,
      progress: String(item.progress || 0),
      upload_time: item.upload_time || '',
      completion_time: item.completion_time || '',
      error_message: item.error_message || '',
      source: 'history',
    },
  })
}

const canEnterDetail = (item: Task) => {
  if (useMockAigc) return true
  return ['pending', 'in_progress', 'completed', 'failed'].includes(item.status)
}

const getTaskTypeLabel = (taskType?: string) => {
  if (taskType === 'paper_aigc') return '论文 AIGC'
  if (taskType === 'resource_check') return '学术资源检测'
  if (taskType === 'image_detection') return '图像检测'
  if (taskType === 'review_detection') return 'Review 检测'
  return '未知类型'
}

const backToList = () => {
  router.push('/history')
}

const goSpecialDetail = (task: Task) => {
  if (task.task_type === 'paper_aigc') {
    router.push({ path: '/detect/paper', query: { tab: 'aigc', task_id: task.task_id } })
    return
  }
  if (task.task_type === 'resource_check') {
    router.push({ path: '/detect/paper', query: { tab: 'resource', task_id: task.task_id } })
    return
  }
  router.push(`/step/${task.task_id}`)
}

const manualReviewStep = computed(() => {
  if (detailTask.value.status !== 'completed') return 1
  const seed = Number(String(detailTask.value.task_id).replace(/\D/g, '').slice(-1) || '1')
  return (seed % 4) + 1
})

const manualReviewStageText = computed(() => {
  if (detailTask.value.status !== 'completed') return '自动检测未完成，暂不可发起人工审核'
  if (manualReviewStep.value === 1) return '待你发起人工审核申请'
  if (manualReviewStep.value === 2) return '管理员审批中'
  if (manualReviewStep.value === 3) return '审核员复核中'
  return '人工审核已完成，结果可查看'
})

const goManualReview = () => {
  router.push({
    path: '/manual-review-result',
    query: {
      task_id: detailTask.value.task_id,
      detail_id: detailTask.value.task_id,
      task_type: detailTask.value.task_type || 'image_detection',
      status: detailTask.value.status,
      progress: String(detailTask.value.progress || 100),
    },
  })
}

//处理删除
const handleDelete = async (item: Task) => {
  try {
    await publisher.deleteDetectionTask({ task_id: item.task_id })
    fetchTasks(currentPage.value, pageSize.value)
  } catch {
    snackbar.showMessage('删除检测任务失败', 'error')
  }
}

// 时间格式化函数
const formatDateTime = (dateTime: string) => {
  if (!dateTime) return ''
  const date = new Date(dateTime)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

</script>

<style scoped>
.v-data-table {
  width: 100%;
}

.batch-actions {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  min-width: 300px;
}
</style>