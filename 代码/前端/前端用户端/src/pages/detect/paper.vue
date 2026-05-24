<template>
  <v-card flat class="paper-workbench">
    <v-card-item v-if="!embedded">
      <v-card-title class="text-h5 font-weight-bold">论文与学术资源检测工作台</v-card-title>
      <v-card-subtitle class="text-body-2 text-wrap mt-1">
        论文检测<strong>仅支持 PDF</strong>。含「全篇 AIGC」与「学术资源规范性」两类检测，结果分别展示在对应标签页中。
      </v-card-subtitle>
    </v-card-item>
    <v-card-item v-else class="pb-0">
      <v-card-subtitle class="text-body-2 text-wrap">
        论文 PDF 专项：AIGC 段落分析 / 参考文献规范性（与「批量提交」中的论文任务互补；批量提交侧重同批图像+论文+Review）。
      </v-card-subtitle>
    </v-card-item>

    <v-card-text>
      <v-tabs v-model="activeTab" color="primary" class="mb-2">
        <v-tab value="aigc" class="text-none">全篇论文 AIGC 检测</v-tab>
        <v-tab value="resource" class="text-none">学术资源规范性检测</v-tab>
      </v-tabs>

      <v-alert type="info" variant="tonal" density="comfortable" class="mb-4 text-body-2">
        <template v-if="activeTab === 'aigc'">
          <strong>本标签页做什么：</strong>对上传论文做<strong>全文生成痕迹（AIGC）分析</strong>，输出 AI 占比类汇总、段落级风险分数与摘录（见下方 E「段落分析」）。适用于审稿前自查「是否过度依赖生成式写作」。
        </template>
        <template v-else>
          <strong>本标签页做什么：</strong>侧重<strong>参考文献、DOI、著录项与引用完整性</strong>等规范性核验（见下方 F「学术资源问题分析」），与 AIGC「谁写的」不是同一问题；同一 PDF 可先后各跑一次（均需 PDF）。
        </template>
      </v-alert>

      <v-row>
        <v-col cols="12" lg="7">
          <v-card variant="outlined" class="pa-4 h-100">
            <div class="text-h6 mb-1">{{ panelA.title }}</div>
            <p class="text-body-2 text-medium-emphasis mb-4">{{ panelA.hint }}</p>
            <div class="text-subtitle-2 font-weight-medium mb-2">检测模式</div>
            <v-btn-toggle v-model="detectionMode" mandatory divided color="primary" density="comfortable" class="mb-3" :disabled="isSubmitting">
              <v-btn value="fast" class="text-none">标准模式</v-btn>
              <v-btn value="precise" class="text-none">精准模式</v-btn>
            </v-btn-toggle>
            <v-file-input
              v-model="selectedFiles"
              :accept="panelA.accept"
              :label="panelA.fileLabel"
              prepend-icon="mdi-file-document-multiple-outline"
              :disabled="isSubmitting"
              show-size
              multiple
              chips
            />
            <v-text-field
              v-model="taskNamePrefix"
              label="任务名称前缀"
              :placeholder="panelA.prefixPlaceholder"
              :disabled="isSubmitting"
            />
            <v-text-field
              v-model.number="batchLimit"
              label="批量提交数量上限"
              type="number"
              :min="1"
              :max="20"
              :disabled="isSubmitting"
            />
            <v-sheet v-if="activeTab === 'resource'" class="pa-3 mb-3 rounded-lg bg-surface-variant">
              <div class="text-caption font-weight-medium mb-1">资源检测关注点（与 AIGC 结果区分）</div>
              <ul class="text-caption pl-4 mb-0">
                <li>参考文献条目格式、DOI/URL 可解析性</li>
                <li>著录项完整性（卷期页码等）</li>
                <li>与正文引用标注的一致性（以后端返回 issues 为准）</li>
              </ul>
            </v-sheet>
            <div class="d-flex flex-wrap ga-2">
              <v-btn color="primary" :loading="isSubmitting" class="text-none" @click="submitBatchTasks">
                {{ panelA.submitLabel }}
              </v-btn>
              <v-btn variant="outlined" class="text-none" :disabled="isSubmitting || !tasks.length" @click="syncAllTaskStatus">
                同步状态
              </v-btn>
              <v-btn variant="outlined" class="text-none" :disabled="isSubmitting" @click="resetForm">重置</v-btn>
            </div>
            <v-alert v-if="error" type="error" variant="tonal" class="mt-3">{{ error }}</v-alert>
          </v-card>
        </v-col>

        <v-col cols="12" lg="5">
          <v-card variant="outlined" class="pa-4 h-100">
            <div class="text-h6 mb-1">任务概览</div>
            <p class="text-caption text-medium-emphasis mb-3">当前标签页独立队列；切换标签会清空未提交的本地队列，避免两类结果混淆。</p>
            <div class="text-body-2 mb-1">检测类型：<strong>{{ panelB.modeLabel }}</strong></div>
            <div v-if="batchSessionId" class="text-body-2 mb-1">
              批次编号：<strong>{{ formatBatchSessionLabel(batchSessionId).short }}</strong>
              <span class="text-caption text-medium-emphasis">（{{ batchSessionId }}）</span>
            </div>
            <div class="text-body-2 mb-1">总任务数：{{ tasks.length }}</div>
            <div class="text-body-2 mb-1">已完成：{{ completedCount }}</div>
            <div class="text-body-2 mb-3">失败：{{ failedCount }}</div>
            <v-progress-linear :model-value="overallProgress" color="primary" height="12" rounded />
            <div class="text-caption mt-2">总体进度：{{ overallProgress }}%</div>
            <v-divider class="my-3" />
            <div class="text-caption text-medium-emphasis">
              <template v-if="activeTab === 'aigc'">完成后请查看下方「段落分析」；若对自动结论有疑义，可在侧栏「人工审核申请」中发起复核。</template>
              <template v-else>完成后请查看下方「学术资源问题分析」；本视图不展示 AIGC 段落表。</template>
            </div>
          </v-card>
        </v-col>
      </v-row>

      <v-card v-if="tasks.length" variant="outlined" class="mt-5 pa-4">
        <div class="text-h6 mb-3">批量任务状态</div>
        <v-table density="compact">
          <thead>
            <tr>
              <th>文件名</th>
              <th>检测类型</th>
              <th>任务 ID</th>
              <th>状态</th>
              <th>进度</th>
              <th>错误</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in tasks" :key="task.localId">
              <td>{{ task.fileName }}</td>
              <td>{{ task.detectionKindLabel }}</td>
              <td>{{ task.taskId || '—' }}</td>
              <td>{{ renderStatus(task.status) }}</td>
              <td>{{ task.progress }}%</td>
              <td>{{ task.errorMessage || '—' }}</td>
            </tr>
          </tbody>
        </v-table>
      </v-card>

      <v-card v-if="latestResult" variant="outlined" class="mt-5 pa-4">
        <div class="text-h6 mb-3">最新结果摘要</div>
        <v-row>
          <v-col cols="12" md="4">
            <v-sheet class="pa-4 rounded border">
              <div class="text-caption">任务 ID</div>
              <div class="text-h5 font-weight-bold">{{ latestResult.taskId }}</div>
            </v-sheet>
          </v-col>
          <v-col cols="12" md="4">
            <v-sheet class="pa-4 rounded border">
              <div class="text-caption">结果类型</div>
              <div class="text-h5 font-weight-bold">{{ latestResult.resultType }}</div>
            </v-sheet>
          </v-col>
          <v-col cols="12" md="4">
            <v-sheet class="pa-4 rounded border">
              <div class="text-caption">{{ latestResult.metricLabel }}</div>
              <div class="text-h5 font-weight-bold">{{ latestResult.score }}</div>
            </v-sheet>
          </v-col>
        </v-row>
        <div class="text-body-1 mt-4">{{ latestResult.summary }}</div>
      </v-card>

      <v-card v-if="factualRows.length && activeTab === 'aigc'" variant="outlined" class="mt-5 pa-4">
        <div class="text-h6 mb-2">事实性鉴伪子结论</div>
        <v-expansion-panels variant="accordion">
          <v-expansion-panel v-for="fc in factualRows" :key="fc.id || fc.title" :title="fc.title">
            <v-expansion-panel-text>
              <ul class="pl-4 mb-0">
                <li v-for="(r, i) in fc.reasons" :key="i" class="text-body-2">{{ r }}</li>
              </ul>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card>

      <v-card v-if="paragraphRows.length && activeTab === 'aigc'" variant="outlined" class="mt-5 pa-4">
        <div class="text-h6 mb-2">段落级 AIGC 风险（仅 AIGC 检测）</div>
        <p class="text-caption text-medium-emphasis mb-3">点击表格行可在下方查看该段摘录。</p>
        <v-table density="compact">
          <thead>
            <tr>
              <th>段落序号</th>
              <th>风险分数</th>
              <th>风险等级</th>
              <th>摘要片段</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in paragraphRows"
              :key="item.index"
              :class="{ 'bg-amber-lighten-4': selectedParagraphIndex === item.index }"
              class="cursor-pointer"
              @click="selectedParagraphIndex = item.index"
            >
              <td>{{ item.index }}</td>
              <td>{{ item.score }}</td>
              <td>{{ item.level }}</td>
              <td>{{ item.excerpt }}</td>
            </tr>
          </tbody>
        </v-table>
        <v-alert v-if="highlightedExcerpt" type="info" variant="tonal" density="compact" class="mt-3 text-body-2">
          <strong>当前段落 P{{ selectedParagraphIndex }}：</strong>{{ highlightedExcerpt }}
        </v-alert>
      </v-card>

      <v-card v-if="resourceIssueRows.length && activeTab === 'resource'" variant="outlined" class="mt-5 pa-4">
        <div class="text-h6 mb-2">参考文献与规范问题（仅资源检测）</div>
        <p class="text-caption text-medium-emphasis mb-3">以下为参考文献与著录相关问题；与 AIGC 段落分析分开展示。</p>
        <v-table density="compact">
          <thead>
            <tr>
              <th>参考条目</th>
              <th>问题类型</th>
              <th>严重程度</th>
              <th>详情</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in resourceIssueRows" :key="`${item.reference_index}-${item.issue_type}`">
              <td>{{ item.reference_index }}</td>
              <td>{{ item.issue_type }}</td>
              <td>{{ item.severity || '—' }}</td>
              <td>{{ item.detail }}</td>
            </tr>
          </tbody>
        </v-table>
      </v-card>

      <v-alert
        v-if="!tasks.length && !latestResult"
        type="info"
        variant="tonal"
        density="compact"
        class="mt-5 text-body-2"
      >
        <strong>提示：</strong>同批送检请用「批量提交」标签；本标签用于论文 PDF 的 AIGC / 资源规范性专项提交与结果查看。检测历史中「论文」类任务会跳转到本页对应子标签。
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import paperApi from '@/api/paper'
import { newBatchSessionId, formatBatchSessionLabel } from '@shared/batchSessionId.ts'
import { extractApiError } from '@shared/apiError.ts'
import type { ResourceIssue, TaskStatus } from '@/types/core'
import { mockAigcFeaturesEnabled } from '@/utils/mockMode'
import { useDetectionMode } from '@/composables/useDetectionMode'

const props = withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false })

type ParagraphResult = {
  index: number
  score: number
  level: 'low' | 'medium' | 'high'
  excerpt: string
}

type BatchTaskRow = {
  localId: string
  fileName: string
  taskId: string
  status: TaskStatus
  progress: number
  errorMessage?: string
  detectionKindLabel: string
}

type LatestResult = {
  taskId: string
  resultType: 'AIGC' | 'RESOURCE'
  score: number | string
  summary: string
  metricLabel: string
}

const activeTab = ref<'aigc' | 'resource'>('aigc')
const route = useRoute()
const router = useRouter()

function innerTabFromRoute(): 'aigc' | 'resource' {
  const key = props.embedded ? 'paper_tab' : 'tab'
  const raw = route.query[key]
  const tab = (Array.isArray(raw) ? raw[0] : raw)?.toString()
  return tab === 'resource' ? 'resource' : 'aigc'
}
const selectedFiles = ref<File[]>([])
const taskNamePrefix = ref('aigc-paper')
const batchLimit = ref(5)
const isSubmitting = ref(false)
const error = ref('')
const batchSessionId = ref('')
const tasks = ref<BatchTaskRow[]>([])
const latestResult = ref<LatestResult | null>(null)
const paragraphRows = ref<ParagraphResult[]>([])
const factualRows = ref<{ id?: string; title: string; reasons: string[] }[]>([])
const selectedParagraphIndex = ref<number | null>(null)
const resourceIssueRows = ref<ResourceIssue[]>([])

const highlightedExcerpt = computed(() => {
  if (selectedParagraphIndex.value == null) return ''
  return paragraphRows.value.find((p) => p.index === selectedParagraphIndex.value)?.excerpt || ''
})
const useMockAigc = mockAigcFeaturesEnabled()
const { mode: detectionMode, modePayload: detectionModePayload } = useDetectionMode()

const panelA = computed(() => {
  if (activeTab.value === 'aigc') {
    return {
      title: 'A. 全篇 AIGC 检测提交',
      hint: '仅 PDF。系统将做格式校验、PDF 文本提取、段落切分后提交 AIGC 检测（主流程）。',
      accept: '.pdf,application/pdf',
      fileLabel: '论文 PDF 文件（仅 .pdf）',
      prefixPlaceholder: '例如 aigc-weekly-01',
      submitLabel: '提交 AIGC 检测任务',
    }
  }
  return {
    title: 'A. 学术资源规范性检测提交',
    hint: '仅 PDF。在全文文本基础上侧重参考文献与元数据规范性核验；与 AIGC 段落风险为不同结果结构。',
    accept: '.pdf,application/pdf',
    fileLabel: '论文 PDF 文件（仅 .pdf）',
    prefixPlaceholder: '例如 ref-integrity-01',
    submitLabel: '提交资源规范检测任务',
  }
})

const panelB = computed(() => ({
  modeLabel: activeTab.value === 'aigc' ? '全篇论文 AIGC（paper_aigc）' : '学术资源规范性（resource_check）',
}))

watch(
  () => (props.embedded ? route.query.paper_tab : route.query.tab),
  () => {
    const next = innerTabFromRoute()
    if (activeTab.value !== next) {
      activeTab.value = next
    }
    applyDefaultsForTab()
    if (!props.embedded || route.query.section === 'paper') {
      syncQueryWithTab()
    }
  },
  { immediate: true }
)

function applyDefaultsForTab() {
  taskNamePrefix.value = activeTab.value === 'aigc' ? 'aigc-paper' : 'resource-ref'
}

function syncQueryWithTab() {
  if (props.embedded && route.query.section !== 'paper') return
  const t = activeTab.value
  const tabKey = props.embedded ? 'paper_tab' : 'tab'
  if (route.query[tabKey] === t) return
  const path = props.embedded ? '/upload' : route.path
  const query: Record<string, string | string[] | undefined> = {
    ...route.query,
    [tabKey]: t,
  }
  if (props.embedded) {
    query.section = 'paper'
    delete query.tab
  }
  router.replace({ path, query })
}

watch(activeTab, (tab, prev) => {
  if (props.embedded && route.query.section === 'paper') {
    syncQueryWithTab()
  } else if (!props.embedded) {
    syncQueryWithTab()
  }
  if (isSubmitting.value) return
  if (prev !== tab) {
    clearWorkspace()
    applyDefaultsForTab()
  }
})

const completedCount = computed(() => tasks.value.filter((item) => item.status === 'completed').length)
const failedCount = computed(() => tasks.value.filter((item) => item.status === 'failed').length)
const overallProgress = computed(() => {
  if (!tasks.value.length) return 0
  const total = tasks.value.reduce((sum, item) => sum + item.progress, 0)
  return Math.floor(total / tasks.value.length)
})

const renderStatus = (status: BatchTaskRow['status']) => {
  if (status === 'in_progress') return '进行中'
  if (status === 'completed') return '已完成'
  if (status === 'failed') return '失败'
  return '待开始'
}

const createTaskName = (index: number) => `${taskNamePrefix.value.trim()}-${index + 1}`

function clearWorkspace() {
  tasks.value = []
  latestResult.value = null
  paragraphRows.value = []
  factualRows.value = []
  selectedParagraphIndex.value = null
  resourceIssueRows.value = []
  error.value = ''
  batchSessionId.value = ''
  selectedFiles.value = []
}

const submitBatchTasks = async () => {
  error.value = ''
  latestResult.value = null
  paragraphRows.value = []
  resourceIssueRows.value = []
  if (!selectedFiles.value.length) {
    error.value = '请先上传至少一个文件。'
    return
  }
  if (!taskNamePrefix.value.trim()) {
    error.value = '请输入任务名称前缀。'
    return
  }

  const nonPdf = selectedFiles.value.filter((f) => !f.name.toLowerCase().endsWith('.pdf'))
  if (nonPdf.length) {
    error.value = '仅支持 PDF 上传，请移除非 PDF 文件后重试。'
    return
  }

  const tab = activeTab.value
  const kindLabel = tab === 'aigc' ? 'AIGC' : '学术资源'
  const limitedFiles = selectedFiles.value.slice(0, Math.max(1, Math.min(batchLimit.value, 20)))
  tasks.value = limitedFiles.map((file) => ({
    localId: `${file.name}-${Date.now()}-${Math.random()}`,
    fileName: file.name,
    taskId: '',
    status: 'pending',
    progress: 0,
    detectionKindLabel: kindLabel,
  }))

  isSubmitting.value = true
  batchSessionId.value = newBatchSessionId()
  const currentBatchId = batchSessionId.value

  for (let i = 0; i < limitedFiles.length; i += 1) {
    const row = tasks.value[i]
    const file = limitedFiles[i]
    row.status = 'in_progress'
    row.progress = 15
    row.errorMessage = ''

    try {
      if (useMockAigc) {
        row.taskId = String(Date.now() + i).slice(-8)
        await sleep(400)
        row.progress = 65
        await sleep(500)
        row.status = 'completed'
        row.progress = 100
      } else {
        const taskName = createTaskName(i)
        const modeOpts = { detection_mode: detectionModePayload(), batch_session_id: currentBatchId }
        const submitRes =
          tab === 'aigc'
            ? await paperApi.uploadAndSubmitAigcTask(file, taskName, modeOpts)
            : await paperApi.uploadAndSubmitResourceTask(file, taskName, modeOpts)
        const payload = submitRes.data as { task_id?: string | number; status?: string; error_message?: string }
        row.taskId = String(payload.task_id ?? '')
        if (payload.status === 'failed') {
          row.status = 'failed'
          row.progress = 100
          row.errorMessage =
            payload.error_message ||
            '论文检测提交失败（常见原因：AI 服务未启动、PDF 无法解析或账号无权限）'
          error.value = row.errorMessage
          continue
        }
        row.progress = 30
      }
    } catch (e: unknown) {
      row.status = 'failed'
      row.progress = 100
      row.errorMessage = extractApiError(e, '批量提交失败。')
      error.value = row.errorMessage
    }
  }

  try {
    await syncAllTaskStatus()
  } catch (e: unknown) {
    error.value = extractApiError(e, '同步任务状态失败。')
  } finally {
    isSubmitting.value = false
  }
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const syncSingleTask = async (row: BatchTaskRow) => {
  if (!row.taskId) return
  if (useMockAigc) return

  const statusRes = await paperApi.getTaskStatus(row.taskId)
  const status = statusRes.data.status as BatchTaskRow['status']
  row.status = status
  row.errorMessage = statusRes.data.error_message || ''
  if (status === 'pending') {
    row.progress = Math.max(row.progress, 30)
    return
  }
  if (status === 'in_progress') {
    row.progress = Math.min(Math.max(row.progress + 20, 50), 90)
    return
  }
  if (status === 'failed') {
    row.progress = 100
    return
  }

  row.progress = 100
  const tab = activeTab.value
  if (tab === 'aigc') {
    const resultRes = await paperApi.getAigcResult(row.taskId)
    const data = resultRes.data
    latestResult.value = {
      taskId: String(row.taskId),
      resultType: 'AIGC',
      score: Number((data.ai_contribution_ratio * 100).toFixed(0)),
      summary: data.summary || '暂无总结。',
      metricLabel: 'AI 倾向占比（%）',
    }
    paragraphRows.value = (data.paragraphs || []).map((item: Record<string, unknown>) => ({
      index: item.index as number,
      score: item.risk_score as number,
      level: item.risk_level as ParagraphResult['level'],
      excerpt: item.excerpt as string,
    }))
    factualRows.value = (data.factual_conclusions || data.factual_issues || []).map(
      (fc: Record<string, unknown>) => ({
        id: String(fc.id || fc.title || ''),
        title: String(fc.title || '子结论'),
        reasons: Array.isArray(fc.reasons) ? fc.reasons.map(String) : [],
      }),
    )
    selectedParagraphIndex.value = paragraphRows.value[0]?.index ?? null
    resourceIssueRows.value = []
  } else {
    const resultRes = await paperApi.getResourceResult(row.taskId)
    const data = resultRes.data
    latestResult.value = {
      taskId: String(row.taskId),
      resultType: 'RESOURCE',
      score: Number(data.suspected_risk_count || 0),
      summary: data.summary || '暂无总结。',
      metricLabel: '可疑问题条目数',
    }
    paragraphRows.value = []
    resourceIssueRows.value = (data.issues || data.issues_json || []).map((item: Record<string, unknown>, idx: number) => ({
      reference_index: Number(item.reference_index ?? idx + 1),
      issue_type: String(item.issue_type ?? 'unknown'),
      detail: String(item.detail ?? item.message ?? '暂无详情。'),
      severity: item.severity as ResourceIssue['severity'],
    }))
  }
}

const syncAllTaskStatus = async () => {
  if (!tasks.value.length) return
  const tab = activeTab.value
  if (useMockAigc) {
    for (const row of tasks.value) {
      row.progress = 100
      row.status = 'completed'
    }
    latestResult.value = {
      taskId: tasks.value[tasks.value.length - 1].taskId || '—',
      resultType: tab === 'aigc' ? 'AIGC' : 'RESOURCE',
      score: tab === 'aigc' ? 43 : 2,
      summary:
        tab === 'aigc'
          ? 'Mock：中等 AIGC 风险，请重点复核下方高敏段落。'
          : 'Mock：发现 2 条参考文献相关规范问题，见下方问题表。',
      metricLabel: tab === 'aigc' ? 'AI 倾向占比（%）' : '可疑问题条目数',
    }
    paragraphRows.value =
      tab === 'aigc'
        ? [
            { index: 2, score: 0.78, level: 'high', excerpt: '该段存在较明显的词汇模式重复，建议重点复核。' },
            { index: 5, score: 0.59, level: 'medium', excerpt: '该段与相邻段落写作风格可能存在不一致。' },
          ]
        : []
    resourceIssueRows.value =
      tab === 'resource'
        ? [
            {
              reference_index: 3,
              issue_type: 'doi_invalid',
              severity: 'high',
              detail: 'DOI 格式疑似无效，请核对来源元数据。',
            },
            {
              reference_index: 8,
              issue_type: 'citation_incomplete',
              severity: 'medium',
              detail: '引用信息不完整：缺少期刊卷/期等信息。',
            },
          ]
        : []
    return
  }

  for (let round = 0; round < 10; round += 1) {
    await Promise.all(tasks.value.map((row) => syncSingleTask(row)))
    const unfinished = tasks.value.some((row) => row.status === 'pending' || row.status === 'in_progress')
    if (!unfinished) break
    await sleep(1200)
  }
}

const resetForm = () => {
  clearWorkspace()
  applyDefaultsForTab()
  batchLimit.value = 5
  error.value = ''
}
</script>

<style scoped>
.border {
  border: 1px solid rgba(128, 128, 128, 0.25);
}
.paper-workbench :deep(.v-card-subtitle) {
  white-space: normal;
}
</style>
