<template>
  <v-card flat>
    <v-card-title class="text-h5 font-weight-bold">Paper Detection Workspace</v-card-title>
    <v-card-text>
      <v-tabs v-model="activeTab" color="primary">
        <v-tab value="aigc">Paper AIGC</v-tab>
        <v-tab value="resource">Academic Resource Check</v-tab>
      </v-tabs>

      <v-window v-model="activeTab" class="mt-4">
        <v-window-item value="aigc">
          <v-alert type="info" variant="tonal" class="mb-4">
            Supports PDF/DOCX/TXT upload, batch submit, task polling and result preview.
          </v-alert>
        </v-window-item>
        <v-window-item value="resource">
          <v-alert type="info" variant="tonal" class="mb-4">
            Resource check task uses the same upload flow and status sync strategy.
          </v-alert>
        </v-window-item>
      </v-window>

      <v-row>
        <v-col cols="12" md="7">
          <v-card variant="outlined" class="pa-4">
            <div class="text-h6 mb-3">A. Upload and Batch Submit</div>
            <v-file-input
              v-model="selectedFiles"
              accept=".pdf,.docx,.txt"
              label="Upload paper files (PDF/DOCX/TXT)"
              prepend-icon="mdi-file-document-multiple-outline"
              :disabled="isSubmitting"
              show-size
              multiple
              chips
            />
            <v-text-field
              v-model="taskNamePrefix"
              label="Task name prefix"
              placeholder="Example: weekly-paper-check"
              :disabled="isSubmitting"
            />
            <v-text-field
              v-model.number="batchLimit"
              label="Batch submit count limit"
              type="number"
              :min="1"
              :max="20"
              :disabled="isSubmitting"
            />
            <div class="d-flex ga-3">
              <v-btn color="primary" :loading="isSubmitting" @click="submitBatchTasks">
                Submit Tasks
              </v-btn>
              <v-btn variant="outlined" @click="syncAllTaskStatus" :disabled="isSubmitting || !tasks.length">
                Sync Status
              </v-btn>
              <v-btn variant="outlined" @click="resetForm" :disabled="isSubmitting">
                Reset
              </v-btn>
            </div>
            <v-alert v-if="error" type="error" variant="tonal" class="mt-3">{{ error }}</v-alert>
          </v-card>
        </v-col>

        <v-col cols="12" md="5">
          <v-card variant="outlined" class="pa-4 h-100">
            <div class="text-h6 mb-3">B. Task Overview</div>
            <div class="text-body-2 mb-1">Mode: {{ activeTab === 'aigc' ? 'AIGC' : 'Resource Check' }}</div>
            <div class="text-body-2 mb-1">Total Tasks: {{ tasks.length }}</div>
            <div class="text-body-2 mb-1">Completed: {{ completedCount }}</div>
            <div class="text-body-2 mb-3">Failed: {{ failedCount }}</div>
            <v-progress-linear :model-value="overallProgress" color="primary" height="12" rounded />
            <div class="text-caption mt-2">Overall Progress: {{ overallProgress }}%</div>
          </v-card>
        </v-col>
      </v-row>

      <v-card v-if="tasks.length" variant="outlined" class="mt-5 pa-4">
        <div class="text-h6 mb-3">C. Batch Task Status</div>
        <v-table density="compact">
          <thead>
            <tr>
              <th>File Name</th>
              <th>Task ID</th>
              <th>Status</th>
              <th>Progress</th>
              <th>Error</th>
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
        <div class="text-h6 mb-3">D. Latest Result</div>
        <v-row>
          <v-col cols="12" md="4">
            <v-sheet class="pa-4 rounded border">
              <div class="text-caption">Task ID</div>
              <div class="text-h5 font-weight-bold">{{ latestResult.taskId }}</div>
            </v-sheet>
          </v-col>
          <v-col cols="12" md="4">
            <v-sheet class="pa-4 rounded border">
              <div class="text-caption">Result Type</div>
              <div class="text-h5 font-weight-bold">{{ latestResult.resultType }}</div>
            </v-sheet>
          </v-col>
          <v-col cols="12" md="4">
            <v-sheet class="pa-4 rounded border">
              <div class="text-caption">Summary Score</div>
              <div class="text-h5 font-weight-bold">{{ latestResult.score }}</div>
            </v-sheet>
          </v-col>
        </v-row>
        <div class="text-body-1 mt-4">{{ latestResult.summary }}</div>
      </v-card>

      <v-card v-if="paragraphRows.length" variant="outlined" class="mt-5 pa-4">
        <div class="text-h6 mb-3">E. Paragraph Analysis</div>
        <v-table density="compact">
          <thead>
            <tr>
              <th>Paragraph</th>
              <th>Risk Score</th>
              <th>Risk Level</th>
              <th>Excerpt</th>
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
        <div class="text-h6 mb-3">F. Resource Issue Analysis</div>
        <v-table density="compact">
          <thead>
            <tr>
              <th>Reference</th>
              <th>Issue Type</th>
              <th>Severity</th>
              <th>Detail</th>
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
import { computed, ref } from 'vue'
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

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const completedCount = computed(() => tasks.value.filter((item) => item.status === 'completed').length)
const failedCount = computed(() => tasks.value.filter((item) => item.status === 'failed').length)
const overallProgress = computed(() => {
  if (!tasks.value.length) return 0
  const total = tasks.value.reduce((sum, item) => sum + item.progress, 0)
  return Math.floor(total / tasks.value.length)
})

const renderStatus = (status: BatchTaskRow['status']) => {
  if (status === 'in_progress') return 'Running'
  if (status === 'completed') return 'Completed'
  if (status === 'failed') return 'Failed'
  return 'Pending'
}

const createTaskName = (index: number) => `${taskNamePrefix.value.trim()}-${index + 1}`

const submitBatchTasks = async () => {
  error.value = ''
  latestResult.value = null
  paragraphRows.value = []
  resourceIssueRows.value = []
  if (!selectedFiles.value.length) {
    error.value = 'Please upload at least one paper file first.'
    return
  }
  if (!taskNamePrefix.value.trim()) {
    error.value = 'Please enter a task name prefix.'
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
    error.value = e?.response?.data?.message || e?.message || 'Batch submit failed.'
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
      summary: data.summary || 'No summary',
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
      summary: data.summary || 'No summary',
    }
    paragraphRows.value = []
    resourceIssueRows.value = (data.issues || data.issues_json || []).map((item: any, idx: number) => ({
      reference_index: Number(item.reference_index ?? idx + 1),
      issue_type: String(item.issue_type ?? 'unknown'),
      detail: String(item.detail ?? item.message ?? 'No detail'),
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
          ? 'Mock AIGC result: medium risk, please review highlighted paragraphs.'
          : 'Mock resource result: 2 references need manual verification.',
    }
    paragraphRows.value =
      activeTab.value === 'aigc'
        ? [
            { index: 2, score: 0.78, level: 'high', excerpt: 'High lexical pattern repetition found in this paragraph.' },
            { index: 5, score: 0.59, level: 'medium', excerpt: 'Potential style inconsistency with adjacent paragraphs.' },
          ]
        : []
    resourceIssueRows.value =
      activeTab.value === 'resource'
        ? [
            {
              reference_index: 3,
              issue_type: 'doi_invalid',
              severity: 'high',
              detail: 'DOI format invalid, please verify source metadata.',
            },
            {
              reference_index: 8,
              issue_type: 'citation_incomplete',
              severity: 'medium',
              detail: 'Missing journal volume and issue information.',
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