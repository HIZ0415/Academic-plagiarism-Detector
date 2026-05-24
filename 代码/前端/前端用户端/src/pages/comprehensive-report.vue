<template>
  <v-container class="py-4 report-hub">
    <div class="d-flex align-center flex-wrap ga-2 mb-4">
      <v-btn icon="mdi-arrow-left" variant="text" @click="router.back()" />
      <div>
        <h1 class="text-h4 font-weight-bold mb-0">综合鉴伪报告</h1>
        <p class="text-body-2 text-medium-emphasis mb-0">
          <span v-if="batchSessionId">批次 {{ shortBatch(batchSessionId) }}</span>
          <span v-if="batchSessionId && focusedTaskId"> · </span>
          <span v-if="focusedTaskId">任务 {{ focusedTaskId }}</span>
          <span v-if="!batchSessionId && !focusedTaskId">请从检测历史进入</span>
        </p>
      </div>
      <v-spacer />
      <v-btn
        v-if="taskReady && focusedTaskId"
        color="primary"
        variant="tonal"
        prepend-icon="mdi-download"
        class="text-none"
        @click="downloadComprehensivePdf"
      >
        下载 PDF
      </v-btn>
      <v-btn
        v-if="taskReady && taskSections"
        variant="outlined"
        prepend-icon="mdi-file-code-outline"
        class="text-none"
        @click="downloadHtmlSnapshot"
      >
        导出 HTML
      </v-btn>
    </div>

    <v-alert v-if="pageError" type="error" variant="tonal" class="mb-4">{{ pageError }}</v-alert>
    <v-progress-linear v-else-if="pageLoading" indeterminate color="primary" class="mb-4" />

    <v-row v-else>
      <!-- 主区：整体 / 当前选中分块 -->
      <v-col cols="12" lg="9" order-lg="1">
        <!-- 整批联合（多模态整体） -->
        <template v-if="sidebarSelection === 'batch'">
          <v-alert v-if="fusionError" type="warning" variant="tonal">{{ fusionError }}</v-alert>
          <template v-else-if="fusion">
            <v-row class="mb-4">
              <v-col cols="12" sm="4">
                <v-card variant="tonal" color="primary" class="pa-4">
                  <div class="text-caption">整批融合可信度</div>
                  <div class="text-h4 font-weight-bold">{{ (fusion.fusion_score * 100).toFixed(1) }}%</div>
                </v-card>
              </v-col>
              <v-col cols="12" sm="4">
                <v-card variant="outlined" class="pa-4">
                  <div class="text-caption text-medium-emphasis">整批综合风险</div>
                  <div class="text-h5 font-weight-bold">{{ riskLevelLabel(fusion.overall_risk) }}</div>
                </v-card>
              </v-col>
              <v-col cols="12" sm="4">
                <v-card variant="outlined" class="pa-4">
                  <div class="text-caption text-medium-emphasis">已完成子任务</div>
                  <div class="text-h5 font-weight-bold">{{ fusion.task_count }}</div>
                </v-card>
              </v-col>
            </v-row>

            <v-card variant="outlined" class="pa-4 mb-4">
              <div class="text-subtitle-1 font-weight-bold mb-2">整批结论与跨模态提示</div>
              <v-list v-if="fusion.cross_modal_notes?.length" density="compact">
                <v-list-item
                  v-for="(n, i) in fusion.cross_modal_notes"
                  :key="i"
                  prepend-icon="mdi-link-variant"
                >
                  {{ n }}
                </v-list-item>
              </v-list>
              <p class="text-body-2 text-medium-emphasis mb-0 mt-2">{{ fusion.recommendation }}</p>
            </v-card>

            <v-card v-if="fusion.dimension_averages" variant="outlined" class="pa-4 mb-4">
              <div class="text-subtitle-2 font-weight-bold mb-3">各模态平均得分</div>
              <v-row>
                <v-col v-for="(val, dim) in fusion.dimension_averages" :key="dim" cols="12" sm="4">
                  <div class="text-caption text-medium-emphasis">{{ dimensionLabel(String(dim)) }}</div>
                  <div class="text-body-1 font-weight-medium">
                    {{ val != null ? `${(Number(val) * 100).toFixed(1)}%` : '—' }}
                  </div>
                </v-col>
              </v-row>
            </v-card>

            <p class="text-caption text-medium-emphasis">
              右侧选择某一子任务，可查看该任务的<strong>综合鉴伪</strong>分项（图像 / 论文 / Review 等）。
            </p>
          </template>
        </template>

        <!-- 单任务：综合概览 -->
        <template v-else-if="sidebarSelection === 'overview'">
          <v-alert v-if="!focusedTaskId" type="info" variant="tonal">请从右侧选择子任务。</v-alert>
          <v-alert v-else-if="taskLoadError" type="error" variant="tonal">{{ taskLoadError }}</v-alert>
          <v-alert v-else-if="!taskReady" type="warning" variant="tonal">{{ taskNotReadyMessage }}</v-alert>
          <template v-else-if="taskSections">
            <v-row class="mb-4">
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-4">
                  <div class="text-caption text-medium-emphasis">综合风险</div>
                  <div class="text-h5 font-weight-bold">{{ riskLevelLabel(taskConclusion.risk_level) }}</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-4">
                  <div class="text-caption text-medium-emphasis">AI 贡献占比（等价）</div>
                  <div class="text-h5 font-weight-bold">{{ aiRatioPercent }}</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-4">
                  <div class="text-caption text-medium-emphasis">检测模式</div>
                  <div class="text-h6">
                    {{ taskSections.models_used?.mode === 'precise' ? '精准模式' : '标准模式' }}
                  </div>
                </v-card>
              </v-col>
            </v-row>
            <v-card variant="outlined" class="pa-4 mb-4">
              <div class="text-subtitle-1 font-weight-bold mb-2">综合结论</div>
              <p class="text-body-1">{{ taskConclusion.headline || '—' }}</p>
              <v-list v-if="taskSections.usage_advice?.length" density="compact" class="mt-2">
                <v-list-item
                  v-for="(tip, i) in taskSections.usage_advice"
                  :key="i"
                  prepend-icon="mdi-lightbulb-outline"
                >
                  {{ tip }}
                </v-list-item>
              </v-list>
            </v-card>
            <v-alert
              v-if="taskSectionsEmpty"
              type="info"
              variant="tonal"
              text="该任务暂无分模态数据，请确认检测已完成。"
            />
          </template>
        </template>

        <!-- 分模态小节 -->
        <template v-else-if="sidebarSelection === 'image' && taskSections?.image">
          <v-card variant="outlined" class="pa-4">
            <div class="text-subtitle-1 font-weight-bold mb-2">图像 · 可疑区域</div>
            <p class="text-body-2 mb-3">{{ taskSections.image.summary }}</p>
            <v-row>
              <v-col
                v-for="(r, idx) in taskSections.image.suspicious_regions"
                :key="idx"
                cols="12"
                md="6"
              >
                <v-card variant="tonal">
                  <v-img v-if="r.image_url" :src="mediaUrl(r.image_url)" max-height="220" />
                  <v-card-text class="text-caption">
                    图 {{ r.image_id }} · 置信度 {{ r.confidence_score }} · {{ r.masks?.length || 0 }} 处标注
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
            <p
              v-if="!taskSections.image.suspicious_regions?.length"
              class="text-body-2 text-medium-emphasis mb-0"
            >
              未检出可疑区域。
            </p>
          </v-card>
        </template>

        <template v-else-if="sidebarSelection === 'paper' && taskSections?.paper">
          <v-card variant="outlined" class="pa-4">
            <div class="text-subtitle-1 font-weight-bold mb-2">论文 AIGC / 资源规范性</div>
            <p class="text-body-2">{{ taskSections.paper.summary }}</p>
            <v-list v-if="taskSections.paper.factual_conclusions?.length" density="compact" class="mt-3">
              <v-list-subheader>事实性鉴伪子结论</v-list-subheader>
              <v-list-item v-for="fc in taskSections.paper.factual_conclusions" :key="fc.id || fc.title">
                <v-list-item-title>{{ fc.title }}</v-list-item-title>
                <v-list-item-subtitle class="text-wrap">
                  <div v-for="(r, i) in fc.reasons" :key="i">{{ r }}</div>
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
            <v-table v-if="taskSections.paper.paragraphs?.length" density="compact" class="mt-3">
              <thead>
                <tr><th>段落</th><th>风险</th><th>摘录</th></tr>
              </thead>
              <tbody>
                <tr v-for="p in taskSections.paper.paragraphs" :key="p.index">
                  <td>P{{ p.index }}</td>
                  <td>{{ p.risk_level }} ({{ p.risk_score }})</td>
                  <td class="text-truncate" style="max-width: 360px">{{ p.excerpt }}</td>
                </tr>
              </tbody>
            </v-table>
          </v-card>
        </template>

        <template v-else-if="sidebarSelection === 'review' && taskSections?.review">
          <v-card variant="outlined" class="pa-4">
            <div class="text-subtitle-1 font-weight-bold mb-2">Review 检测</div>
            <p class="text-body-2">{{ taskSections.review.summary }}</p>
          </v-card>
        </template>

        <template v-else-if="sidebarSelection === 'manual' && taskSections?.manual_review">
          <v-card variant="tonal" color="secondary" class="pa-4">
            <div class="text-subtitle-2 font-weight-bold">人工审核关联</div>
            <p class="text-body-2 mb-0">
              申请单 #{{ taskSections.manual_review.review_request_id }} ·
              状态 {{ taskSections.manual_review.status }}
            </p>
            <v-btn
              class="mt-2 text-none"
              size="small"
              variant="elevated"
              :to="{
                path: '/manual-review-result',
                query: {
                  review_request_id: String(taskSections.manual_review.review_request_id),
                  task_id: focusedTaskId,
                },
              }"
            >
              查看人工审核汇总
            </v-btn>
          </v-card>
        </template>

        <v-alert v-else type="info" variant="tonal">
          当前分项暂无数据，请从右侧选择其他条目。
        </v-alert>
      </v-col>

      <!-- 右侧：分部分导航（非侧栏菜单） -->
      <v-col cols="12" lg="3" order-lg="2">
        <v-card variant="outlined" class="report-side-nav sticky-side">
          <v-card-title class="text-subtitle-1 font-weight-bold py-3">报告目录</v-card-title>
          <v-divider />
          <v-list density="compact" nav>
            <v-list-subheader v-if="batchSessionId">整批（多模态整体）</v-list-subheader>
            <v-list-item
              v-if="batchSessionId"
              :active="sidebarSelection === 'batch'"
              prepend-icon="mdi-chart-timeline-variant"
              title="整批联合分析"
              value="batch"
              @click="selectSidebar('batch')"
            />

            <v-list-subheader class="mt-2">子任务 · 综合鉴伪</v-list-subheader>
            <v-list-item
              v-for="t in sidebarTasks"
              :key="t.task_id"
              :active="focusedTaskId === String(t.task_id) && sidebarSelection !== 'batch'"
              prepend-icon="mdi-file-document-outline"
              @click="selectTask(String(t.task_id))"
            >
              <v-list-item-title class="text-body-2">
                #{{ t.task_id }} · {{ taskTypeShort(t.task_type) }}
              </v-list-item-title>
              <v-list-item-subtitle class="text-caption text-truncate">
                {{ t.task_name || '—' }}
              </v-list-item-subtitle>
            </v-list-item>

            <template v-if="focusedTaskId && taskReady && taskSections">
              <v-divider class="my-2" />
              <v-list-subheader>当前任务分项</v-list-subheader>
              <v-list-item
                :active="sidebarSelection === 'overview'"
                prepend-icon="mdi-clipboard-text-outline"
                title="综合结论"
                @click="selectSidebar('overview')"
              />
              <v-list-item
                v-if="taskSections.image"
                :active="sidebarSelection === 'image'"
                prepend-icon="mdi-image"
                title="图像"
                @click="selectSidebar('image')"
              />
              <v-list-item
                v-if="taskSections.paper"
                :active="sidebarSelection === 'paper'"
                prepend-icon="mdi-file-document"
                title="论文"
                @click="selectSidebar('paper')"
              />
              <v-list-item
                v-if="taskSections.review"
                :active="sidebarSelection === 'review'"
                prepend-icon="mdi-text-box-search"
                title="Review"
                @click="selectSidebar('review')"
              />
              <v-list-item
                v-if="taskSections.manual_review"
                :active="sidebarSelection === 'manual'"
                prepend-icon="mdi-gavel"
                title="人工审核"
                @click="selectSidebar('manual')"
              />
            </template>
          </v-list>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import platform from '@/api/platform'
import { useSnackbarStore } from '@/stores/snackbar'
import { savePdfFromAxiosResponse } from '@/utils/downloadPdf'
import { API_BASE_URL } from '@/api/request'
import { formatBatchSessionLabel } from '@shared/batchSessionId.ts'

type SidebarKey = 'batch' | 'overview' | 'image' | 'paper' | 'review' | 'manual'
type FusionTask = {
  task_id: number
  task_type: string
  task_name?: string
  risk?: string
  score?: number
}
type FusionPayload = {
  fusion_score: number
  overall_risk: string
  task_count: number
  cross_modal_notes?: string[]
  recommendation?: string
  dimension_averages?: Record<string, number | null>
  tasks?: FusionTask[]
}

const route = useRoute()
const router = useRouter()
const snackbar = useSnackbarStore()

const batchSessionId = computed(() => String(route.query.batch_session_id || '').trim())
const focusedTaskId = ref(String(route.query.task_id || ''))
const sidebarSelection = ref<SidebarKey>('overview')

const pageLoading = ref(false)
const pageError = ref('')
const fusion = ref<FusionPayload | null>(null)
const fusionError = ref('')

const taskLoading = ref(false)
const taskLoadError = ref('')
const taskReady = ref(false)
const taskNotReadyMessage = ref('')
const taskSections = ref<Record<string, any> | null>(null)

const taskConclusion = computed(() => taskSections.value?.conclusion || {})
const aiRatioPercent = computed(() => {
  const r = taskConclusion.value.ai_contribution_ratio
  if (r == null) return '—'
  const n = Number(r)
  return n <= 1 ? `${(n * 100).toFixed(1)}%` : `${n}%`
})
const taskSectionsEmpty = computed(() => {
  if (!taskSections.value) return false
  const c = taskConclusion.value
  const hasConclusion = !!(c.headline || c.risk_level || c.ai_contribution_ratio != null)
  const hasModality = !!(taskSections.value.image || taskSections.value.paper || taskSections.value.review)
  return !hasConclusion && !hasModality
})

const sidebarTasks = computed((): FusionTask[] => {
  if (fusion.value?.tasks?.length) return fusion.value.tasks
  if (focusedTaskId.value) {
    return [
      {
        task_id: Number(focusedTaskId.value),
        task_type: taskSections.value?.overview?.task_type || 'unknown',
        task_name: taskSections.value?.overview?.task_name,
      },
    ]
  }
  return []
})

function shortBatch(id: string) {
  return formatBatchSessionLabel(id).short
}

function riskLevelLabel(level: string | undefined) {
  if (!level) return '—'
  const map: Record<string, string> = {
    high: '高风险',
    medium: '中风险',
    low: '低风险',
    高风险: '高风险',
    中风险: '中风险',
    低风险: '低风险',
  }
  return map[level] || level
}

function dimensionLabel(dim: string) {
  return { image: '图像', paper: '论文', review: 'Review' }[dim] || dim
}

function taskTypeShort(t: string) {
  const m: Record<string, string> = {
    image_detection: '图像',
    paper_aigc: '论文 AIGC',
    resource_check: '资源规范',
    review_detection: 'Review',
  }
  return m[t] || t
}

function mediaUrl(path: string) {
  if (!path) return ''
  if (path.startsWith('http')) return path
  const base = API_BASE_URL.replace(/\/api$/, '')
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

function selectSidebar(key: SidebarKey) {
  sidebarSelection.value = key
  if (key === 'batch') {
    router.replace({
      path: '/comprehensive-report',
      query: { ...route.query, view: 'batch', task_id: focusedTaskId.value || undefined },
    })
    return
  }
  const q: Record<string, string | undefined> = { ...route.query, view: undefined }
  if (focusedTaskId.value) q.task_id = focusedTaskId.value
  router.replace({ path: '/comprehensive-report', query: q })
}

async function loadFusion() {
  fusionError.value = ''
  fusion.value = null
  if (!batchSessionId.value) return
  try {
    const res = await platform.getBatchFusion({ batch_session_id: batchSessionId.value })
    fusion.value = res.data as FusionPayload
  } catch (e: any) {
    fusionError.value = e?.response?.data?.error || '整批联合分析失败（请确认批次内任务均已完成）'
  }
}

async function loadTaskReport(taskId: string) {
  if (!taskId) {
    taskReady.value = false
    taskSections.value = null
    return
  }
  taskLoading.value = true
  taskLoadError.value = ''
  try {
    const res = await platform.getComprehensiveReport(taskId)
    taskReady.value = !!res.data.ready
    taskSections.value = res.data.sections
    taskNotReadyMessage.value = res.data.message || '报告尚未就绪'
  } catch (e: any) {
    taskLoadError.value = e?.response?.data?.detail || '加载失败'
    taskReady.value = false
    taskSections.value = null
  } finally {
    taskLoading.value = false
  }
}

function selectTask(taskId: string) {
  focusedTaskId.value = taskId
  sidebarSelection.value = 'overview'
  router.replace({
    path: '/comprehensive-report',
    query: {
      ...route.query,
      task_id: taskId,
      ...(batchSessionId.value ? { batch_session_id: batchSessionId.value } : {}),
    },
  })
  loadTaskReport(taskId)
}

async function refreshPage() {
  pageError.value = ''
  const qTask = String(route.query.task_id || '').trim()
  focusedTaskId.value = qTask

  if (!batchSessionId.value && !qTask) {
    pageError.value = '请从检测历史或批量提交完成页进入综合鉴伪报告'
    return
  }

  pageLoading.value = true
  try {
    if (batchSessionId.value) {
      await loadFusion()
    }
    if (qTask) {
      await loadTaskReport(qTask)
      sidebarSelection.value = route.query.view === 'batch' ? 'batch' : 'overview'
    } else if (batchSessionId.value) {
      taskSections.value = null
      taskReady.value = false
      sidebarSelection.value = 'batch'
    }
  } finally {
    pageLoading.value = false
  }
}

async function downloadComprehensivePdf() {
  if (!focusedTaskId.value) return
  try {
    const res = await platform.downloadComprehensiveReport(focusedTaskId.value)
    savePdfFromAxiosResponse(res, `comprehensive_task_${focusedTaskId.value}.pdf`)
    snackbar.showMessage('综合鉴伪 PDF 已下载', 'success')
  } catch {
    snackbar.showMessage('下载失败', 'error')
  }
}

function downloadHtmlSnapshot() {
  if (!taskSections.value) return
  const payload = {
    batch: fusion.value,
    task_id: focusedTaskId.value,
    sections: taskSections.value,
  }
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>综合鉴伪报告</title></head><body><pre>${JSON.stringify(payload, null, 2)}</pre></body></html>`
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `report_${focusedTaskId.value || batchSessionId.value}.html`
  a.click()
  URL.revokeObjectURL(a.href)
  snackbar.showMessage('已导出 HTML', 'success')
}

watch(
  () => [route.query.batch_session_id, route.query.task_id],
  () => {
    focusedTaskId.value = String(route.query.task_id || '')
    refreshPage()
  },
)

onMounted(refreshPage)
</script>

<style scoped>
.report-side-nav.sticky-side {
  position: sticky;
  top: 72px;
  max-height: calc(100vh - 96px);
  overflow-y: auto;
}
</style>
