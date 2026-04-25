<template>
  <v-card flat>
    <v-card-title class="text-h5 font-weight-bold">论文检测工作台</v-card-title>
    <v-card-text>
      <v-tabs v-model="activeTab" color="primary">
        <v-tab value="aigc">全篇论文 AIGC 检测</v-tab>
        <v-tab value="resource">学术资源检测</v-tab>
      </v-tabs>

      <v-window v-model="activeTab" class="mt-4">
        <v-window-item value="aigc">
          <v-alert type="info" variant="tonal" class="mb-4">
            支持 PDF/DOCX/TXT 上传、批量提交、任务状态轮询与结果预览。
          </v-alert>
        </v-window-item>
        <v-window-item value="resource">
          <v-alert type="info" variant="tonal" class="mb-4">
            学术资源检测复用同一套上传流程与状态同步策略。
          </v-alert>
        </v-window-item>
      </v-window>

      <v-row>
        <v-col cols="12" md="7">
          <v-card variant="outlined" class="pa-4">
            <div class="text-h6 mb-3">A. 上传与批量提交</div>
            <v-file-input
              v-model="selectedFiles"
              accept=".pdf,.docx,.txt"
              label="上传论文文件（PDF/DOCX/TXT）"
              prepend-icon="mdi-file-document-multiple-outline"
              :disabled="isSubmitting"
              show-size
              multiple
              chips
            />
            <v-text-field
              v-model="taskNamePrefix"
              label="任务名称前缀"
              placeholder="例如：weekly-paper-check"
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
            <div class="d-flex ga-3">
              <v-btn color="primary" :loading="isSubmitting" @click="submitBatchTasks">
                提交任务
              </v-btn>
              <v-btn variant="outlined" @click="syncAllTaskStatus" :disabled="isSubmitting || !tasks.length">
                同步状态
              </v-btn>
              <v-btn variant="outlined" @click="resetForm" :disabled="isSubmitting">
                重置
              </v-btn>
            </div>
            <v-alert v-if="error" type="error" variant="tonal" class="mt-3">{{ error }}</v-alert>
          </v-card>
        </v-col>

        <v-col cols="12" md="5">
          <v-card variant="outlined" class="pa-4 h-100">
            <div class="text-h6 mb-3">B. 任务概览</div>
            <div class="text-body-2 mb-1">模式：{{ activeTab === 'aigc' ? 'AIGC' : '学术资源检测' }}</div>
            <div class="text-body-2 mb-1">总任务数：{{ tasks.length }}</div>
            <div class="text-body-2 mb-1">已完成：{{ completedCount }}</div>
            <div class="text-body-2 mb-3">失败：{{ failedCount }}</div>
            <v-progress-linear :model-value="overallProgress" color="primary" height="12" rounded />
            <div class="text-caption mt-2">总体进度：{{ overallProgress }}%</div>
          </v-card>
        </v-col>
      </v-row>

      <v-card v-if="tasks.length" variant="outlined" class="mt-5 pa-4">
        <div class="text-h6 mb-3">C. 批量任务状态</div>
        <v-table density="compact">
          <thead>
            <tr>
              <th>文件名</th>
              <th>任务 ID</th>
              <th>状态</th>
              <th>进度</th>
              <th>错误</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in tasks" :key="task.localId">
              <td>{{ task.fileName }}</td>
              <td>{{ task.taskId || '-' }}</td>
              <td>{{ renderStatus(task.status) }}</td>
              <td>{{ task.progress }}%</td>
              <td>{{ task.errorMessage || '-' }}</td>
            </tr>
          </tbody>
        </v-table>
      </v-card>

      <v-card v-if="latestResult" variant="outlined" class="mt-5 pa-4">
        <div class="text-h6 mb-3">D. 最新结果</div>
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
              <div class="text-caption">汇总指标</div>
              <div class="text-h5 font-weight-bold">{{ latestResult.score }}</div>
            </v-sheet>
          </v-col>
        </v-row>
        <div class="text-body-1 mt-4">{{ latestResult.summary }}</div>
      </v-card>

      <v-card v-if="paragraphRows.length" variant="outlined" class="mt-5 pa-4">
        <div class="text-h6 mb-3">E. 段落分析</div>
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
            <tr v-for="item in paragraphRows" :key="item.index">
              <td>{{ item.index }}</td>
              <td>{{ item.score }}</td>
              <td>{{ item.level }}</td>
              <td>{{ item.excerpt }}</td>
            </tr>
          </tbody>
        </v-table>
      </v-card>

      <v-card v-if="resourceIssueRows.length" variant="outlined" class="mt-5 pa-4">
        <div class="text-h6 mb-3">F. 学术资源问题分析</div>
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
              <td>{{ item.severity || '-' }}</td>
              <td>{{ item.detail }}</td>
            </tr>
          </tbody>
        </v-table>
      </v-card>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import paperApi from '@/api/paper'
import type { ResourceIssue, TaskStatus } from '@/types/core'

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
}

type LatestResult = {
  taskId: string
  resultType: 'AIGC' | 'RESOURCE'
  score: number
  summary: string
}

const activeTab = ref<'aigc' | 'resource'>('aigc')
const route = useRoute()
const selectedFiles = ref<File[]>([])
const taskNamePrefix = ref('paper-task')
const batchLimit = ref(5)
const isSubmitting = ref(false)
const error = ref('')
const tasks = ref<BatchTaskRow[]>([])
const latestResult = ref<LatestResult | null>(null)
const paragraphRows = ref<ParagraphResult[]>([])
const resourceIssueRows = ref<ResourceIssue[]>([])
const useMockAigc = import.meta.env.VITE_USE_MOCK_AIGC === 'true'

watch(
  () => route.query.tab,
  (tab) => {
    if (tab === 'resource') {
      activeTab.value = 'resource'
      return
    }
    if (tab === 'aigc') {
      activeTab.value = 'aigc'
    }
  },
  { immediate: true }
)

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

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

const submitBatchTasks = async () => {
  error.value = ''
  latestResult.value = null
  paragraphRows.value = []
  resourceIssueRows.value = []
  if (!selectedFiles.value.length) {
    error.value = '请先上传至少一个论文文件。'
    return
  }
  if (!taskNamePrefix.value.trim()) {
    error.value = '请输入任务名称前缀。'
    return
  }

  const limitedFiles = selectedFiles.value.slice(0, Math.max(1, Math.min(batchLimit.value, 20)))
  tasks.value = limitedFiles.map((file) => ({
    localId: `${file.name}-${Date.now()}-${Math.random()}`,
    fileName: file.name,
    taskId: '',
    status: 'pending',
    progress: 0,
  }))

  isSubmitting.value = true
  try {
    for (let i = 0; i < limitedFiles.length; i += 1) {
      const row = tasks.value[i]
      const file = limitedFiles[i]
      row.status = 'in_progress'
      row.progress = 15

      if (useMockAigc) {
        row.taskId = String(Date.now() + i).slice(-8)
        await sleep(400)
        row.progress = 65
        await sleep(500)
        row.status = 'completed'
        row.progress = 100
      } else {
        const taskName = createTaskName(i)
        let submitRes
        if (activeTab.value === 'aigc') {
          submitRes = await paperApi.uploadAndSubmitAigcTask(file, taskName)
        } else {
          submitRes = await paperApi.uploadAndSubmitResourceTask(file, taskName)
        }
        row.taskId = String(submitRes.data.task_id)
        row.progress = 30
      }
    }

    await syncAllTaskStatus()
  } catch (e: any) {
    error.value = e?.response?.data?.message || e?.message || '批量提交失败。'
  } finally {
    isSubmitting.value = false
  }
}

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
  if (activeTab.value === 'aigc') {
    const resultRes = await paperApi.getAigcResult(row.taskId)
    const data = resultRes.data
    latestResult.value = {
      taskId: String(row.taskId),
      resultType: 'AIGC',
      score: Number((data.ai_contribution_ratio * 100).toFixed(0)),
      summary: data.summary || '暂无总结。',
    }
    paragraphRows.value = (data.paragraphs || []).map((item: any) => ({
      index: item.index,
      score: item.risk_score,
      level: item.risk_level,
      excerpt: item.excerpt,
    }))
    resourceIssueRows.value = []
  } else {
    const resultRes = await paperApi.getResourceResult(row.taskId)
    const data = resultRes.data
    latestResult.value = {
      taskId: String(row.taskId),
      resultType: 'RESOURCE',
      score: Number(data.suspected_risk_count || 0),
      summary: data.summary || '暂无总结。',
    }
    paragraphRows.value = []
    resourceIssueRows.value = (data.issues || data.issues_json || []).map((item: any, idx: number) => ({
      reference_index: Number(item.reference_index ?? idx + 1),
      issue_type: String(item.issue_type ?? 'unknown'),
      detail: String(item.detail ?? item.message ?? '暂无详情。'),
      severity: item.severity,
    }))
  }
}

const syncAllTaskStatus = async () => {
  if (!tasks.value.length) return
  if (useMockAigc) {
    for (const row of tasks.value) {
      row.progress = 100
      row.status = 'completed'
    }
    latestResult.value = {
      taskId: tasks.value[tasks.value.length - 1].taskId || '-',
      resultType: activeTab.value === 'aigc' ? 'AIGC' : 'RESOURCE',
      score: activeTab.value === 'aigc' ? 43 : 2,
      summary:
        activeTab.value === 'aigc'
          ? 'Mock AIGC 结果：中等风险，请重点复核标记段落。'
          : 'Mock 学术资源检测结果：有 2 条参考文献需要人工核验。',
    }
    paragraphRows.value =
      activeTab.value === 'aigc'
        ? [
            { index: 2, score: 0.78, level: 'high', excerpt: '该段存在较明显的词汇模式重复，建议重点复核。' },
            { index: 5, score: 0.59, level: 'medium', excerpt: '该段与相邻段落写作风格可能存在不一致。' },
          ]
        : []
    resourceIssueRows.value =
      activeTab.value === 'resource'
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
  activeTab.value = 'aigc'
  selectedFiles.value = []
  taskNamePrefix.value = 'paper-task'
  batchLimit.value = 5
  tasks.value = []
  latestResult.value = null
  paragraphRows.value = []
  resourceIssueRows.value = []
  error.value = ''
}
</script>

<style scoped>
.border {
  border: 1px solid rgba(128, 128, 128, 0.25);
}
</style>