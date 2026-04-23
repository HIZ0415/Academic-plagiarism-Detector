<template>
  <v-card flat>
    <v-card-title class="text-h5 font-weight-bold">Paper AIGC Detection (Demo)</v-card-title>
    <v-card-text>
      <v-row>
        <v-col cols="12" md="7">
          <v-card variant="outlined" class="pa-4">
            <div class="text-h6 mb-3">A. Upload and Detection Settings</div>
            <v-file-input
              v-model="selectedFile"
              accept=".pdf,.docx,.txt"
              label="Upload paper file (PDF/DOCX/TXT)"
              prepend-icon="mdi-file-document-outline"
              :disabled="isSubmitting"
              show-size
            />
            <v-text-field
              v-model="taskName"
              label="Task name"
              placeholder="Example: Course Paper AIGC Check"
              :disabled="isSubmitting"
            />
            <v-switch
              v-model="enableFactCheck"
              color="primary"
              label="Enable factual verification"
              :disabled="isSubmitting"
            />
            <v-select
              v-model="analysisGranularity"
              label="Analysis granularity"
              :items="[
                { title: 'Paragraph-level', value: 'paragraph' },
                { title: 'Sentence-level', value: 'sentence' }
              ]"
              :disabled="isSubmitting"
            />
            <div class="d-flex ga-3">
              <v-btn color="primary" :loading="isSubmitting" @click="submitDetection">
                Submit Detection
              </v-btn>
              <v-btn variant="outlined" @click="resetForm" :disabled="isSubmitting">
                Reset
              </v-btn>
            </div>
          </v-card>
        </v-col>

        <v-col cols="12" md="5">
          <v-card variant="outlined" class="pa-4 h-100">
            <div class="text-h6 mb-3">B. Task Status</div>
            <div class="text-body-2 mb-2">Task ID: {{ taskId || '-' }}</div>
            <div class="text-body-2 mb-3">Status: {{ statusText }}</div>
            <v-progress-linear :model-value="progress" color="primary" height="12" rounded />
            <div class="text-caption mt-2">Progress: {{ progress }}%</div>
            <v-alert v-if="error" type="error" variant="tonal" class="mt-3">{{ error }}</v-alert>
          </v-card>
        </v-col>
      </v-row>

      <v-card v-if="result" variant="outlined" class="mt-5 pa-4">
        <div class="text-h6 mb-3">C. Result Summary</div>
        <v-row>
          <v-col cols="12" md="4">
            <v-sheet class="pa-4 rounded border">
              <div class="text-caption">Overall risk level</div>
              <div class="text-h5 font-weight-bold">{{ result.riskLevel }}</div>
            </v-sheet>
          </v-col>
          <v-col cols="12" md="4">
            <v-sheet class="pa-4 rounded border">
              <div class="text-caption">AI contribution ratio</div>
              <div class="text-h5 font-weight-bold">{{ result.aiContribution }}%</div>
            </v-sheet>
          </v-col>
          <v-col cols="12" md="4">
            <v-sheet class="pa-4 rounded border">
              <div class="text-caption">High-risk paragraphs</div>
              <div class="text-h5 font-weight-bold">{{ result.highRiskCount }}</div>
            </v-sheet>
          </v-col>
        </v-row>
        <div class="text-body-1 mt-4">{{ result.summary }}</div>
      </v-card>

      <v-card v-if="result" variant="outlined" class="mt-5 pa-4">
        <div class="text-h6 mb-3">D. Paragraph Analysis (Demo)</div>
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
            <tr v-for="item in result.paragraphs" :key="item.index">
              <td>{{ item.index }}</td>
              <td>{{ item.score }}</td>
              <td>{{ item.level }}</td>
              <td>{{ item.excerpt }}</td>
            </tr>
          </tbody>
        </v-table>
      </v-card>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'

type ParagraphResult = {
  index: number
  score: number
  level: 'low' | 'medium' | 'high'
  excerpt: string
}

type DemoResult = {
  riskLevel: 'Low' | 'Medium' | 'High'
  aiContribution: number
  highRiskCount: number
  summary: string
  paragraphs: ParagraphResult[]
}

const selectedFile = ref<File | null>(null)
const taskName = ref('')
const enableFactCheck = ref(true)
const analysisGranularity = ref<'paragraph' | 'sentence'>('paragraph')
const isSubmitting = ref(false)
const taskId = ref('')
const progress = ref(0)
const statusText = ref('Not started')
const error = ref('')
const result = ref<DemoResult | null>(null)

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const submitDetection = async () => {
  error.value = ''
  result.value = null
  if (!selectedFile.value) {
    error.value = 'Please upload a paper file first.'
    return
  }
  if (!taskName.value.trim()) {
    error.value = 'Please enter a task name.'
    return
  }

  isSubmitting.value = true
  taskId.value = String(Date.now()).slice(-6)
  progress.value = 0
  statusText.value = 'Queued'
  await sleep(500)
  progress.value = 20
  statusText.value = 'Running'
  await sleep(700)
  progress.value = 55
  await sleep(700)
  progress.value = 85
  await sleep(600)
  progress.value = 100
  statusText.value = 'Completed'

  result.value = {
    riskLevel: 'Medium',
    aiContribution: 43,
    highRiskCount: 4,
    summary: 'This paper shows moderate AI-generation tendency. Review high-risk paragraphs first and cross-check references with factual verification.',
    paragraphs: [
      { index: 3, score: 0.82, level: 'high', excerpt: 'Template-like phrasing with high sentence-pattern repetition.' },
      { index: 6, score: 0.74, level: 'high', excerpt: 'Semantic density is unusually stable across neighboring sentences.' },
      { index: 9, score: 0.56, level: 'medium', excerpt: 'Terminology is overly concentrated with uniform tone.' },
      { index: 12, score: 0.47, level: 'medium', excerpt: 'Writing style slightly deviates from surrounding context.' },
    ],
  }
  isSubmitting.value = false
}

const resetForm = () => {
  selectedFile.value = null
  taskName.value = ''
  enableFactCheck.value = true
  analysisGranularity.value = 'paragraph'
  taskId.value = ''
  progress.value = 0
  statusText.value = 'Not started'
  error.value = ''
  result.value = null
}
</script>

<style scoped>
.border {
  border: 1px solid rgba(128, 128, 128, 0.25);
}
</style>