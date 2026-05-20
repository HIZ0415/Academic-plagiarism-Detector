<template>
  <v-card flat border="0">
    <template v-if="detailId">
      <v-card-title class="d-flex align-center pa-0">
        <div>
          <div class="text-h5 font-weight-bold">检测记录详情</div>
          <div class="text-body-2 text-medium-emphasis">任务编号：{{ formatTaskId(detailTask.task_id) }}</div>
        </div>
        <v-spacer></v-spacer>
        <v-chip :color="getStatusColor(effectiveDetailStatus)" size="small">{{ getStatus(effectiveDetailStatus) }}</v-chip>
      </v-card-title>

      <v-card-text class="pa-0 mt-4">
        <v-row>
          <v-col cols="12" md="12">
            <v-card variant="outlined" class="pa-4 mb-4">
              <div class="text-subtitle-1 font-weight-bold mb-3">任务概览</div>
              <v-row>
                <v-col cols="12" md="3" class="text-body-2">类型：{{ getTaskTypeLabel(detailTask.task_type) }}</v-col>
                <v-col cols="12" md="3" class="text-body-2">状态：{{ getStatus(effectiveDetailStatus) }}</v-col>
                <v-col cols="12" md="3" class="text-body-2">进度：{{ detailTask.progress || 0 }}%</v-col>
                <v-col cols="12" md="3" class="text-body-2">时间：{{ formatDateTime(detailTask.upload_time) || '暂无' }}</v-col>
                <v-col v-if="detailTask.batch_session_id" cols="12" class="text-body-2 mt-2">
                  统一检测批次：<code>{{ detailTask.batch_session_id }}</code>（与同批其他子任务逻辑关联）
                </v-col>
                <v-col v-if="manualReviewWorkflowPayload?.found" cols="12" class="text-body-2 mt-2">
                  人工审核申请单：<code>{{ manualReviewWorkflowPayload.review_request_id }}</code>；
                  管理端：<span class="font-weight-medium">{{ manualReviewAdminLabel }}</span>；
                  专家进度：<span class="font-weight-medium">{{ manualReviewExpertLabel }}</span>
                </v-col>
              </v-row>
              <v-alert v-if="detailTask.error_message" type="error" variant="tonal" class="mt-3">
                {{ detailTask.error_message }}
              </v-alert>
            </v-card>

            <v-progress-linear v-if="detailReportLoading" indeterminate color="primary" class="mb-4" />
            <v-alert v-if="detailReportError" type="warning" variant="tonal" density="compact" class="mb-4">
              {{ detailReportError }}
            </v-alert>
            <v-alert
              v-if="!isBackendTaskId(detailTask.task_id)"
              type="info"
              variant="tonal"
              density="compact"
              class="mb-4"
            >
              当前为<strong>本地记录</strong>（任务 ID 非后端数字），无法下载 PDF。请在列表中选择服务器返回的已完成任务，或重新在「统一学术检测」提交。
            </v-alert>

            <v-card v-if="detailSections?.image" variant="outlined" class="pa-4 mb-4">
              <div class="text-subtitle-1 font-weight-bold mb-3">图像检测结果</div>
              <p class="text-body-2 mb-2">{{ detailSections.image.summary || '—' }}</p>
              <v-row>
                <v-col cols="12" md="4">
                  <div class="text-body-2">综合风险：{{ riskLabelCn(detailSections.image.risk_level || detailSections.conclusion?.risk_level) }}</div>
                </v-col>
                <v-col cols="12" md="4">
                  <div class="text-body-2">可疑区域：{{ detailSections.image.suspicious_regions?.length ?? 0 }} 处</div>
                </v-col>
                <v-col cols="12" md="4">
                  <div class="text-body-2">
                    AI 占比：{{ formatRatioPercent(detailSections.image.ai_contribution_ratio ?? detailSections.conclusion?.ai_contribution_ratio) }}
                  </div>
                </v-col>
              </v-row>
            </v-card>

            <v-card v-if="detailSections?.paper" variant="outlined" class="pa-4 mb-4">
              <div class="text-subtitle-1 font-weight-bold mb-3">论文检测结果</div>
              <p class="text-body-2 mb-2">{{ detailSections.paper.summary || detailSections.conclusion?.headline || '—' }}</p>
              <v-row>
                <v-col cols="12" md="4">
                  <div class="text-body-2">AIGC 风险：{{ riskLabelCn(detailSections.paper.risk_level || detailSections.conclusion?.risk_level) }}</div>
                </v-col>
                <v-col cols="12" md="4">
                  <div class="text-body-2">
                    AI 占比：{{ formatRatioPercent(detailSections.paper.ai_contribution_ratio ?? detailSections.conclusion?.ai_contribution_ratio) }}
                  </div>
                </v-col>
                <v-col cols="12" md="4">
                  <div class="text-body-2">
                    高风险段落：{{ highRiskParagraphCount(detailSections.paper.paragraphs) }}
                  </div>
                </v-col>
              </v-row>
            </v-card>

            <v-card v-if="detailSections?.review" variant="outlined" class="pa-4 mb-4">
              <div class="text-subtitle-1 font-weight-bold mb-3">Review 检测结果</div>
              <p class="text-body-2 mb-2">{{ detailSections.review.summary || detailSections.conclusion?.headline || '—' }}</p>
              <v-row>
                <v-col cols="12" md="4">
                  <div class="text-body-2">综合风险：{{ riskLabelCn(detailSections.review.risk_level || detailSections.conclusion?.risk_level) }}</div>
                </v-col>
                <v-col cols="12" md="4">
                  <div class="text-body-2">模板化信号：{{ detailSections.review.template_signals?.length ?? 0 }} 条</div>
                </v-col>
                <v-col cols="12" md="4">
                  <div class="text-body-2">问题条目：{{ detailSections.review.issues?.length ?? 0 }}</div>
                </v-col>
              </v-row>
            </v-card>

            <v-card
              v-if="effectiveDetailStatus === 'completed' && isBackendTaskId(detailTask.task_id) && !detailSections && !detailReportLoading"
              variant="tonal"
              class="pa-4 mb-4"
            >
              <div class="text-body-2 text-medium-emphasis">暂无结构化结果，仍可尝试下载 PDF 报告。</div>
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
              <div class="text-subtitle-1 font-weight-bold mb-3">报告与操作</div>
              <p class="text-body-2 text-medium-emphasis mb-3">
                AI 检测完成后可下载自动检测报告；若已发起人工审核，可另下载含专家意见的审核报告。
              </p>
              <div class="d-flex flex-wrap align-center ga-3">
                <v-btn
                  color="secondary"
                  variant="tonal"
                  prepend-icon="mdi-file-download-outline"
                  class="text-none"
                  :loading="downloadingDetectionReport"
                  :disabled="!canDownloadDetectionReport"
                  @click="handleDownloadDetectionReport"
                >
                  下载 AI 检测报告
                </v-btn>
                <v-btn
                  color="primary"
                  variant="outlined"
                  prepend-icon="mdi-file-download"
                  class="text-none"
                  :loading="downloadingComprehensiveReport"
                  :disabled="!canDownloadDetectionReport"
                  @click="handleDownloadComprehensivePdf"
                >
                  下载综合鉴伪 PDF
                </v-btn>
                <v-btn
                  variant="text"
                  class="text-none"
                  :disabled="!canDownloadDetectionReport"
                  @click="goComprehensiveReport(detailTask)"
                >
                  在线综合报告
                </v-btn>
                <v-btn
                  color="secondary"
                  variant="outlined"
                  prepend-icon="mdi-file-document-check-outline"
                  class="text-none"
                  :loading="downloadingManualReport"
                  :disabled="!canDownloadManualReviewReport"
                  @click="handleDownloadManualReviewReport"
                >
                  下载人工审核报告
                </v-btn>
                <v-btn
                  color="primary"
                  prepend-icon="mdi-gavel"
                  class="text-none"
                  :disabled="effectiveDetailStatus !== 'completed'"
                  @click="goManualReviewRequest"
                >
                  人工审核申请
                </v-btn>
                <v-btn color="primary" variant="tonal" class="text-none" :disabled="effectiveDetailStatus !== 'completed'" @click="goSpecialDetail(detailTask)">
                  高级检测
                </v-btn>
                <v-btn color="secondary" variant="outlined" class="text-none" @click="goRepeatDetection(detailTask)">
                  再次检测
                </v-btn>
                <v-btn
                  variant="outlined"
                  class="text-none"
                  :disabled="!canViewManualReviewResult"
                  @click="goManualReview"
                >
                  查看人工审核结果
                </v-btn>
                <v-btn variant="text" class="text-none" @click="backToList">返回历史列表</v-btn>
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

    <v-card-title class="d-flex align-center flex-wrap ga-2 pa-0">
      <h1 class="text-h4 font-weight-bold">检测历史</h1>
      <v-spacer></v-spacer>
      <v-text-field
        v-model="keyword"
        density="compact"
        hide-details
        prepend-inner-icon="mdi-magnify"
        label="搜索任务名或 ID"
        style="max-width: 240px"
        clearable
        @keyup.enter="applyKeywordSearch"
      />
      <v-btn variant="outlined" class="mr-2" @click="showFilter = true"
        :color="hasActiveFilters ? 'primary' : undefined">
        <v-icon class="mr-2">mdi-filter</v-icon>
        筛选
      </v-btn>
      <v-btn color="primary" prepend-icon="mdi-upload" @click="goUpload">
        统一检测
      </v-btn>
    </v-card-title>

    <v-tabs v-model="typeTab" color="primary" class="mt-3 mb-2" density="comfortable">
      <v-tab value="all">全部</v-tab>
      <v-tab value="image_detection">图像</v-tab>
      <v-tab value="paper_aigc">论文</v-tab>
      <v-tab value="review_detection">Review</v-tab>
      <v-tab value="resource_check">资源规范</v-tab>
    </v-tabs>

    <v-alert v-if="batchSessionFilter" type="info" variant="tonal" density="compact" class="mt-3 mb-2">
      当前按<strong>统一检测批次</strong>筛选：<code>{{ batchSessionFilter }}</code>。列表仅显示该批次在本地记录的子任务；清除地址栏中的
      <code>batch_session_id</code> 查询参数可恢复完整列表。
      <v-btn size="small" variant="text" class="ms-2" @click="clearBatchFilter">清除批次筛选</v-btn>
    </v-alert>

    <!-- 筛选对话框 -->
    <v-dialog v-model="showFilter" max-width="500">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">筛选条件</v-card-title>
        <v-card-text>
          <div class="d-flex flex-column gap-4">
            <v-select v-model="filters.status" :items="statusOptions" label="任务状态" clearable hide-details></v-select>

            <v-select
              v-model="filters.taskType"
              :items="taskTypeFilterOptions"
              label="内容类型"
              clearable
              hide-details
            ></v-select>

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
          <span :title="`原始 ID：${item.task_id}`">{{ formatTaskId(item.task_id) }}</span>
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
              查看报告
            </v-btn>
            <v-btn
              size="small"
              color="teal"
              variant="text"
              :disabled="item.status !== 'completed'"
              @click="goComprehensiveReport(item)"
            >
              综合鉴伪
            </v-btn>
            <v-btn size="small" color="secondary" variant="text" @click="goRepeatDetection(item)">
              再次检测
            </v-btn>
            <v-btn size="small" color="error" variant="text" @click="handleDelete(item)"
              :disabled="item.status !== 'completed'">
              删除
            </v-btn>
          </div>
        </template>

        <template v-slot:item.batch_session_id="{ item }">
          <span class="text-caption text-medium-emphasis">{{ shortBatchId(item.batch_session_id) }}</span>
        </template>

        <template v-slot:top>
          <div class="d-flex align-center pa-4">
            <div class="text-caption text-medium-emphasis">
              共 {{ listRecordCount }} 条记录{{ batchSessionFilter ? '（批次筛选后）' : '' }}
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
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSnackbarStore } from '@/stores/snackbar'
import publisher from '@/api/publisher'
import platform from '@/api/platform'
import { getManualReviewApplicationByDetectionTask } from '@/api/manualReviewWorkflow'
import { mockAigcFeaturesEnabled } from '@/utils/mockMode'
import { savePdfFromAxiosResponse } from '@/utils/downloadPdf'

const router = useRouter()
const route = useRoute()
const snackbar = useSnackbarStore()
const useMockAigc = mockAigcFeaturesEnabled()

// 分页相关
const pageSize = ref(10)
const currentPage = ref(1)
const totalTasks = ref(0)
const totalPages = ref(1)
const loading = ref(false)

// 表格列定义
const headers = [
  { title: '任务编号', key: 'task_id', align: 'center' as const, width: '130px' },
  { title: '批次', key: 'batch_session_id', align: 'center' as const, width: '130px' },
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
  task_name?: string
  progress?: number
  source?: 'server' | 'local'
  error_message?: string
  /** 与 /upload 同批送检关联（本地记录为主） */
  batch_session_id?: string
}

// 任务数据
const tasks = ref<Task[]>([])

// 筛选相关
const showFilter = ref(false)
const typeTab = ref('all')
const keyword = ref('')

const filters = ref<{
  status: string | null
  taskType: string | null
  timeRange: string | null
  startDate: string | null
  endDate: string | null
}>({
  status: null,
  taskType: null,
  timeRange: null,
  startDate: null,
  endDate: null
})

const taskTypeFilterOptions = [
  { title: '图像检测', value: 'image_detection' },
  { title: '论文 AIGC', value: 'paper_aigc' },
  { title: 'Review', value: 'review_detection' },
  { title: '资源规范', value: 'resource_check' },
]

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
  { title: '最近半年', value: '180d' },
  { title: '最近一年', value: '365d' },
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
    if (filters.value.taskType) {
      params.task_type = filters.value.taskType
    }
    if (keyword.value.trim()) {
      params.keyword = keyword.value.trim()
    }

    // 添加时间范围筛选
    if (filters.value.timeRange) {
      const now = Date.now()
      const ranges: Record<string, number> = {
        '1d': 24 * 60 * 60 * 1000,
        '7d': 7 * 24 * 60 * 60 * 1000,
        '30d': 30 * 24 * 60 * 60 * 1000,
        '90d': 90 * 24 * 60 * 60 * 1000,
        '180d': 180 * 24 * 60 * 60 * 1000,
        '365d': 365 * 24 * 60 * 60 * 1000,
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
      batch_session_id: task.batch_session_id || '',
      task_name: task.task_name || '',
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
      batch_session_id: t.batch_session_id ? String(t.batch_session_id) : undefined,
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

const batchSessionFilter = computed(() => String(route.query.batch_session_id || '').trim())

function shortBatchId(id?: string) {
  if (!id) return '—'
  return id.length > 18 ? `${id.slice(0, 10)}…${id.slice(-6)}` : id
}

function formatTaskId(id?: string | number) {
  const raw = String(id ?? '').trim()
  if (!raw) return 'DT-000000'
  const digits = raw.replace(/\D/g, '')
  if (digits) return `DT-${digits.slice(-6).padStart(6, '0')}`

  let hash = 0
  for (const ch of raw) {
    hash = (hash * 31 + ch.charCodeAt(0)) % 1000000
  }
  return `DT-${String(hash).padStart(6, '0')}`
}

function clearBatchFilter() {
  const q = { ...route.query } as Record<string, string | string[] | undefined>
  delete q.batch_session_id
  router.replace({ path: '/history', query: q })
}

// 筛选后的任务列表（批次 / 类型 Tab / 关键字）
const filteredTasks = computed(() => {
  const b = batchSessionFilter.value
  let list = b ? tasks.value.filter((t) => (t.batch_session_id || '') === b) : tasks.value
  if (typeTab.value !== 'all') {
    list = list.filter((t) => (t.task_type || '') === typeTab.value)
  }
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return list
  return list.filter((t) => {
    const id = String(t.task_id).toLowerCase()
    const name = String(t.task_name || '').toLowerCase()
    return id.includes(kw) || name.includes(kw)
  })
})

function applyKeywordSearch() {
  fetchTasks(currentPage.value, pageSize.value)
}

const listRecordCount = computed(() => (batchSessionFilter.value ? filteredTasks.value.length : totalTasks.value))

const detailId = computed(() => String(route.query.detail_id || ''))

const detailTask = computed<Task>(() => {
  const qBatch = String(route.query.batch_session_id || '').trim()
  const fallback: Task = {
    task_id: detailId.value,
    upload_time: String(route.query.upload_time || ''),
    completion_time: String(route.query.completion_time || ''),
    status: (String(route.query.status || 'pending') as Task['status']),
    task_type: String(route.query.task_type || 'unknown'),
    progress: Number(route.query.progress || 0),
    source: 'local',
    error_message: String(route.query.error_message || ''),
    batch_session_id: qBatch || undefined,
  }
  if (!detailId.value) return fallback
  const found = tasks.value.find((t) => String(t.task_id) === detailId.value)
  if (found) return { ...found, batch_session_id: found.batch_session_id || qBatch || undefined }
  return fallback
})

function isBackendTaskId(id: string | number | undefined) {
  return /^\d+$/.test(String(id ?? '').trim())
}

function riskLabelCn(level?: string) {
  const m: Record<string, string> = { low: '低', medium: '中', high: '高' }
  return m[String(level || '').toLowerCase()] || level || '—'
}

function formatRatioPercent(ratio: unknown) {
  if (ratio == null || ratio === '') return '—'
  const n = Number(ratio)
  if (Number.isNaN(n)) return '—'
  return n <= 1 ? `${(n * 100).toFixed(1)}%` : `${n.toFixed(1)}%`
}

function highRiskParagraphCount(paragraphs: unknown) {
  if (!Array.isArray(paragraphs)) return 0
  return paragraphs.filter((p) => (p as { risk_level?: string }).risk_level === 'high').length
}

const detailSections = ref<Record<string, unknown> | null>(null)
const detailReportLoading = ref(false)
const detailReportError = ref('')

const effectiveDetailStatus = computed(() => {
  const found = tasks.value.find((t) => String(t.task_id) === detailId.value)
  return (found?.status || detailTask.value.status) as Task['status']
})

async function loadDetailReport() {
  detailSections.value = null
  detailReportError.value = ''
  const tid = detailId.value
  if (!tid || !isBackendTaskId(tid)) return
  if (effectiveDetailStatus.value !== 'completed') return

  detailReportLoading.value = true
  try {
    const res = await platform.getComprehensiveReport(tid)
    if (res.data.ready && res.data.sections) {
      detailSections.value = res.data.sections as Record<string, unknown>
    } else {
      detailReportError.value = res.data.message || '检测尚未完成，报告生成中'
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    detailReportError.value = err.response?.data?.detail || '加载检测结果失败'
  } finally {
    detailReportLoading.value = false
  }
}

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
function goComprehensiveReport(item: Task) {
  router.push({ path: '/comprehensive-report', query: { task_id: String(item.task_id) } })
}

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
      ...(item.batch_session_id ? { batch_session_id: item.batch_session_id } : {}),
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

const goUpload = () => {
  router.push('/upload')
}

const goRepeatDetection = (task: Task) => {
  router.push({
    path: '/upload',
    query: {
      task_id: task.task_id,
      task_type: task.task_type || 'unknown',
      source: 'history-repeat',
      ...(task.batch_session_id ? { batch_session_id: task.batch_session_id } : {}),
    },
  })
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
  if (task.task_type === 'review_detection') {
    router.push({ path: '/detect/review', query: { task_id: task.task_id } })
    return
  }
  router.push(`/step/${task.task_id}`)
}

const manualReviewWorkflowPayload = ref<{
  found: boolean
  review_request_id?: number
  admin_state?: string
  manual_review_status?: string
  admin_reject_reason?: string
} | null>(null)

async function loadManualReviewWorkflow() {
  manualReviewWorkflowPayload.value = null
  if (!detailId.value || effectiveDetailStatus.value !== 'completed') return
  try {
    const res = await getManualReviewApplicationByDetectionTask(detailId.value)
    manualReviewWorkflowPayload.value = res.data as typeof manualReviewWorkflowPayload.value
  } catch {
    manualReviewWorkflowPayload.value = null
  }
}

watch(
  () => [detailId.value, effectiveDetailStatus.value] as const,
  () => {
    loadManualReviewWorkflow()
    loadDetailReport()
  },
  { immediate: true },
)

const manualReviewStep = computed(() => {
  if (effectiveDetailStatus.value !== 'completed') return 1
  const w = manualReviewWorkflowPayload.value
  if (!w || !w.found) return 1
  if (w.admin_state === 'refused') return 2
  if (w.admin_state === 'pending') return 2
  if (w.manual_review_status === 'completed') return 4
  return 3
})

const manualReviewStageText = computed(() => {
  if (effectiveDetailStatus.value !== 'completed') return '自动检测未完成，暂不可发起人工审核'
  const w = manualReviewWorkflowPayload.value
  if (!w || !w.found) return '尚未发起人工审核申请，请点击「人工审核申请」填写表单提交'
  if (w.admin_state === 'refused') return `管理端已拒绝：${w.admin_reject_reason || '—'}`
  if (w.admin_state === 'pending') return '管理端审批中，可在侧栏「人工审核申请」列表查看进度'
  if (w.manual_review_status === 'completed') return '专家已完成审核，可查看汇总结果'
  return '已分配专家，审核进行中'
})

const manualReviewAdminLabel = computed(() => {
  const w = manualReviewWorkflowPayload.value
  if (!w?.found) return '—'
  if (w.admin_state === 'pending') return '待审批'
  if (w.admin_state === 'refused') return '已拒绝'
  if (w.admin_state === 'accepted') return '已通过'
  return String(w.admin_state)
})

const manualReviewExpertLabel = computed(() => {
  const w = manualReviewWorkflowPayload.value
  if (!w?.found || w.admin_state !== 'accepted') return '—'
  if (w.manual_review_status === 'completed') return '已完成'
  return '进行中'
})

const canViewManualReviewResult = computed(() => {
  if (effectiveDetailStatus.value !== 'completed') return false
  const w = manualReviewWorkflowPayload.value
  if (!w?.found || !w.review_request_id) return false
  if (w.admin_state === 'refused') return false
  return w.manual_review_status === 'completed'
})

const canDownloadManualReviewReport = computed(() => {
  if (effectiveDetailStatus.value !== 'completed') return false
  const w = manualReviewWorkflowPayload.value
  if (!w?.found || !w.review_request_id) return false
  if (w.admin_state === 'refused') return false
  return w.admin_state === 'accepted'
})

const downloadingDetectionReport = ref(false)
const downloadingComprehensiveReport = ref(false)
const downloadingManualReport = ref(false)

const canDownloadDetectionReport = computed(
  () => effectiveDetailStatus.value === 'completed' && isBackendTaskId(detailTask.value.task_id),
)

async function parseAxiosBlobError(e: unknown): Promise<string> {
  const err = e as { response?: { data?: Blob } }
  const data = err.response?.data
  if (data instanceof Blob) {
    try {
      const text = await data.text()
      const json = JSON.parse(text) as { detail?: string }
      return json.detail || text.slice(0, 160)
    } catch {
      return '服务器返回错误（非 PDF）'
    }
  }
  return ''
}

async function handleDownloadDetectionReport() {
  const tid = detailTask.value.task_id
  if (!canDownloadDetectionReport.value) return
  downloadingDetectionReport.value = true
  try {
    const res = await publisher.downloadReport(tid)
    savePdfFromAxiosResponse(res, `task_${tid}_report.pdf`)
    snackbar.showMessage('AI 检测报告已下载', 'success')
  } catch (e: unknown) {
    const detail = await parseAxiosBlobError(e)
    snackbar.showMessage(
      detail || 'AI 检测报告下载失败，请确认任务已完成且后端已生成报告',
      'error',
    )
  } finally {
    downloadingDetectionReport.value = false
  }
}

async function handleDownloadComprehensivePdf() {
  const tid = detailTask.value.task_id
  if (!canDownloadDetectionReport.value) return
  downloadingComprehensiveReport.value = true
  try {
    const res = await platform.downloadComprehensiveReport(tid)
    savePdfFromAxiosResponse(res, `comprehensive_task_${tid}.pdf`)
    snackbar.showMessage('综合鉴伪 PDF 已下载', 'success')
  } catch (e: unknown) {
    const detail = await parseAxiosBlobError(e)
    snackbar.showMessage(detail || '综合鉴伪 PDF 下载失败', 'error')
  } finally {
    downloadingComprehensiveReport.value = false
  }
}

async function handleDownloadManualReviewReport() {
  const w = manualReviewWorkflowPayload.value
  const rid = w?.review_request_id
  if (!rid || !canDownloadManualReviewReport.value) return
  downloadingManualReport.value = true
  try {
    const res = await publisher.downloadReviewReport({ review_request_id: rid })
    savePdfFromAxiosResponse(res, `manual_review_${rid}_report.pdf`)
    snackbar.showMessage('人工审核报告已下载', 'success')
  } catch {
    snackbar.showMessage('人工审核报告下载失败（专家未完成时可能暂无终稿）', 'error')
  } finally {
    downloadingManualReport.value = false
  }
}

const goManualReview = () => {
  const w = manualReviewWorkflowPayload.value
  router.push({
    path: '/manual-review-result',
    query: {
      task_id: detailTask.value.task_id,
      detail_id: detailTask.value.task_id,
      task_type: detailTask.value.task_type || 'image_detection',
      status: detailTask.value.status,
      progress: String(detailTask.value.progress || 100),
      ...(w?.found && w.review_request_id ? { review_request_id: String(w.review_request_id) } : {}),
    },
  })
}

/** 发布者侧发起/跟踪人工审核（文档 `/annual`，与侧栏「人工审核申请」一致） */
const goManualReviewRequest = () => {
  router.push({
    path: '/annual',
    query: { task_id: String(detailTask.value.task_id) },
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
