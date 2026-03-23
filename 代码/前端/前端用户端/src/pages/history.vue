<template>
  <v-card flat border="0">
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
              :disabled="item.status !== 'completed'">
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
  </v-card>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSnackbarStore } from '@/stores/snackbar'
import publisher from '@/api/publisher'
import Review_request_id from './task/[review_request_id].vue'

const router = useRouter()
const snackbar = useSnackbarStore()

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
  status: 'pending' | 'in_progress' | 'completed'
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

    tasks.value = taskList.map((task: any) => ({
      task_id: task.task_id,
      upload_time: task.upload_time,
      completion_time: task.completion_time,
      status: task.status
    }))

    currentPage.value = current_page
    totalPages.value = total_pages
    totalTasks.value = total_tasks
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
  router.push(`/step/${item.task_id}`)
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