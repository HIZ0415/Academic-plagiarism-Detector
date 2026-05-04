<template>
  <v-card flat class="review-detect-page">
    <v-card-item>
      <v-card-title class="text-h5 font-weight-bold">同行评审 Review 检测</v-card-title>
      <v-card-subtitle class="text-body-2 text-wrap mt-1">
        需求 <strong>FR-PLJC-0001</strong>：对同行评审（Review）文本做自动化检测；输入为<strong>在线文本</strong>或<strong>TXT 文件</strong>，需求写明「本阶段不新增 Review PDF、DOCX 等格式」。接口
        <code>POST /api/review/submit/</code>（字段 <code>text</code> 或 <code>file</code>）与《current-project-api》§16.2 一致。
      </v-card-subtitle>
      <div class="d-flex flex-wrap align-center ga-2 mt-3">
        <v-btn color="primary" variant="tonal" prepend-icon="mdi-upload" class="text-none" to="/upload">
          新检测（统一入口）
        </v-btn>
        <v-btn color="primary" variant="tonal" prepend-icon="mdi-gavel" class="text-none" to="/annual">
          人工审核申请
        </v-btn>
        <v-btn variant="text" size="small" class="text-none" to="/history">检测历史</v-btn>
      </div>
    </v-card-item>

    <v-card-text>
      <v-alert type="warning" variant="tonal" density="comfortable" class="mb-4 text-body-2">
        请勿将 PDF/DOCX 当作 Review 上传；论文类请在<strong>统一检测入口</strong>（<code>/upload</code>）上传 PDF。
      </v-alert>

      <v-alert v-if="linkedTaskId" type="info" variant="tonal" density="compact" class="mb-4 text-body-2">
        已从检测历史关联任务 <code>{{ linkedTaskId }}</code> 跳转；可在下方重新提交或前往历史查看原任务状态。
      </v-alert>

      <v-row>
        <v-col cols="12" md="7">
          <v-card variant="outlined" class="pa-4">
            <div class="text-h6 mb-3">输入 Review 文本</div>

            <v-textarea
              v-model="reviewText"
              label="在线粘贴评审意见 / Review 全文"
              placeholder="将 Review 正文粘贴到此处…"
              variant="outlined"
              rows="10"
              auto-grow
              max-rows="24"
              :disabled="submitting"
              :readonly="!!reviewFile"
              hint="若已选择 TXT 文件，则以下方文件为准，文本框只读"
              persistent-hint
            />

            <div class="text-center text-caption text-medium-emphasis my-3">— 或 —</div>

            <v-file-input
              v-model="reviewFile"
              accept=".txt,text/plain"
              label="上传 TXT 文件（仅 .txt）"
              prepend-icon="mdi-file-document-outline"
              show-size
              :disabled="submitting"
              @update:model-value="onFilePicked"
            />

            <v-text-field
              v-model="taskName"
              class="mt-4"
              label="任务名称"
              placeholder="例如 editorial-review-2026-01"
              :disabled="submitting"
            />

            <div class="d-flex flex-wrap ga-2 mt-4">
              <v-btn color="primary" class="text-none" :loading="submitting" @click="submit">
                提交 Review 检测
              </v-btn>
              <v-btn variant="outlined" class="text-none" :disabled="submitting" @click="reset">清空</v-btn>
            </div>

            <v-alert v-if="formError" type="error" variant="tonal" class="mt-3">{{ formError }}</v-alert>
          </v-card>
        </v-col>

        <v-col cols="12" md="5">
          <v-card variant="outlined" class="pa-4 h-100">
            <div class="text-h6 mb-2">说明</div>
            <ul class="text-body-2 text-medium-emphasis pl-4">
              <li class="mb-2">与「论文 PDF」检测对象不同：Review 为评审意见类纯文本。</li>
              <li class="mb-2">文本与 TXT 二选一；若同时填写，以<strong>上传文件</strong>为准。</li>
              <li>提交成功后可到检测历史查看任务状态（与统一任务体系对齐）。</li>
            </ul>
          </v-card>
        </v-col>
      </v-row>

      <v-card v-if="lastResponse" variant="outlined" class="mt-5 pa-4">
        <div class="text-h6 mb-3">提交响应</div>
        <pre class="response-pre text-body-2">{{ formattedResponse }}</pre>
        <v-btn v-if="taskIdFromResponse" class="mt-3 text-none" color="primary" variant="tonal" @click="goHistory">
          前往检测历史（任务 {{ taskIdFromResponse }}）
        </v-btn>
      </v-card>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { submitReviewDetection } from '@/api/reviewDetection'
import { useSnackbarStore } from '@/stores/snackbar'

const route = useRoute()
const router = useRouter()
const snackbar = useSnackbarStore()
const useMock = import.meta.env.VITE_USE_MOCK_AIGC === 'true'

const linkedTaskId = computed(() => {
  const q = route.query.task_id
  const s = (Array.isArray(q) ? q[0] : q)?.toString().trim()
  return s || ''
})

const reviewText = ref('')
const reviewFile = ref<File | File[] | null>(null)
const taskName = ref('review-task')
const submitting = ref(false)
const formError = ref('')
const lastResponse = ref<Record<string, unknown> | null>(null)

const singleFile = computed((): File | null => {
  const f = reviewFile.value
  if (!f) return null
  return Array.isArray(f) ? f[0] ?? null : f
})

function onFilePicked(files: File | File[] | null) {
  const f = Array.isArray(files) ? files[0] : files
  if (f && !f.name.toLowerCase().endsWith('.txt')) {
    formError.value = 'Review 本阶段仅支持 .txt 文本文件。'
    reviewFile.value = null
    return
  }
  formError.value = ''
}

const formattedResponse = computed(() =>
  lastResponse.value ? JSON.stringify(lastResponse.value, null, 2) : ''
)

const taskIdFromResponse = computed(() => {
  const r = lastResponse.value
  if (!r) return ''
  const id = r.task_id ?? r.taskId
  return id != null ? String(id) : ''
})

function reset() {
  reviewText.value = ''
  reviewFile.value = null
  formError.value = ''
  lastResponse.value = null
  taskName.value = 'review-task'
}

function goHistory() {
  const id = taskIdFromResponse.value
  if (!id) return
  router.push({
    path: '/history',
    query: {
      detail_id: id,
      task_type: 'review_detection',
      status: 'completed',
      progress: '100',
      source: 'review-detect',
    },
  })
}

async function submit() {
  formError.value = ''
  lastResponse.value = null
  const name = taskName.value.trim()
  if (!name) {
    formError.value = '请填写任务名称。'
    return
  }

  const file = singleFile.value
  const text = reviewText.value.trim()

  if (!file && !text) {
    formError.value = '请粘贴 Review 文本，或上传一个 .txt 文件。'
    return
  }

  if (file && !file.name.toLowerCase().endsWith('.txt')) {
    formError.value = '仅支持 .txt 文件。'
    return
  }

  submitting.value = true
  try {
    if (useMock) {
      await new Promise((r) => setTimeout(r, 500))
      lastResponse.value = {
        task_id: `mock-${Date.now()}`,
        status: 'pending',
        cleaned_text_length: file ? file.size : text.length,
        message: 'Mock：未调用 /review/submit/',
      }
      snackbar.showMessage('Mock 模式：已模拟提交', 'success')
      return
    }

    const res = await submitReviewDetection({
      task_name: name,
      file: file || undefined,
      text: file ? undefined : text,
    })
    lastResponse.value = res.data as Record<string, unknown>
    snackbar.showMessage('Review 检测任务已提交', 'success')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { message?: string } }; message?: string }
    formError.value = err?.response?.data?.message || err?.message || '提交失败'
    snackbar.showMessage(formError.value, 'error')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.response-pre {
  white-space: pre-wrap;
  word-break: break-word;
  background: rgba(var(--v-theme-surface-variant), 0.35);
  padding: 12px;
  border-radius: 8px;
  max-height: 320px;
  overflow: auto;
}
</style>
