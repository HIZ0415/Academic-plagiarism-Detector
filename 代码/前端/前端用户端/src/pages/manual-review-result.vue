<template>
  <v-card flat>
    <v-card-title class="d-flex align-center flex-wrap ga-2">
      <div>
        <div class="text-h5 font-weight-bold">人工审核结果</div>
        <div class="text-body-2 text-medium-emphasis">
          检测任务：{{ taskId || '—' }}
          <template v-if="reviewRequestId"> · 申请单：{{ reviewRequestId }}</template>
        </div>
      </div>
      <v-spacer />
      <v-chip v-if="loadError" color="error" variant="tonal">加载失败</v-chip>
      <v-chip v-else-if="loading" color="info" variant="tonal">加载中…</v-chip>
      <v-chip v-else-if="summaryPayload" :color="statusChipColor" variant="tonal">{{ statusChipLabel }}</v-chip>
    </v-card-title>

    <v-card-text>
      <v-alert v-if="loadError" type="error" variant="tonal" class="mb-4">
        {{ loadError }}
      </v-alert>

      <v-alert
        v-else-if="!loading && summaryPayload?.admin_state === 'refused'"
        type="error"
        variant="tonal"
        class="mb-4"
      >
        组织管理员已拒绝本申请。
        <span v-if="summaryPayload.admin_reject_reason">原因：{{ summaryPayload.admin_reject_reason }}</span>
      </v-alert>

      <v-alert
        v-else-if="!loading && summaryPayload?.manual_review_status !== 'completed'"
        type="warning"
        variant="tonal"
        class="mb-4"
      >
        专家尚未完成审核或申请仍停留在管理端（当前：{{ summaryPayload?.manual_review_status || '未知' }}）。
      </v-alert>

      <v-alert
        v-if="summaryPayload?.request_reason"
        type="info"
        variant="tonal"
        density="comfortable"
        class="mb-4 text-body-2"
      >
        <strong>申请理由：</strong>{{ summaryPayload.request_reason }}
      </v-alert>

      <template v-if="summaryPayload?.summary">
        <v-row>
          <v-col cols="12" md="4">
            <v-card variant="outlined" class="pa-4">
              <div class="text-caption text-medium-emphasis">参与专家数</div>
              <div class="text-h6 font-weight-bold">{{ summaryPayload.summary.reviewerCount }}</div>
            </v-card>
          </v-col>
          <v-col cols="12" md="4">
            <v-card variant="outlined" class="pa-4">
              <div class="text-caption text-medium-emphasis">疑似问题项（图像类计数）</div>
              <div class="text-h6 font-weight-bold">{{ summaryPayload.summary.suspiciousImageCount }}</div>
            </v-card>
          </v-col>
          <v-col cols="12" md="4">
            <v-card variant="outlined" class="pa-4">
              <div class="text-caption text-medium-emphasis">最终结论（摘要）</div>
              <div class="text-h6 font-weight-bold">{{ summaryPayload.summary.finalDecision }}</div>
            </v-card>
          </v-col>
        </v-row>

        <v-card variant="outlined" class="pa-4 mt-4">
          <div class="text-subtitle-1 font-weight-bold mb-3">专家意见汇总</div>
          <v-table v-if="reviewerRows.length" density="comfortable">
            <thead>
              <tr>
                <th>专家</th>
                <th>结论</th>
                <th>置信度</th>
                <th>意见摘要</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in reviewerRows" :key="item.reviewer">
                <td>{{ item.reviewer }}</td>
                <td>{{ item.decision }}</td>
                <td>{{ item.confidence }}%</td>
                <td class="text-wrap" style="max-width: 420px">{{ item.comment }}</td>
              </tr>
            </tbody>
          </v-table>
          <div v-else class="text-body-2 text-medium-emphasis">暂无专家汇总。</div>
        </v-card>

        <v-card v-if="segmentRows.length" variant="outlined" class="pa-4 mt-4">
          <div class="text-subtitle-1 font-weight-bold mb-3">材料单元审核明细（论文 / Review）</div>
          <v-table density="comfortable">
            <thead>
              <tr>
                <th>单元</th>
                <th>专家</th>
                <th>人工结论</th>
                <th>说明 / 分项理由</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in segmentRows" :key="row.segmentId + row.label">
                <td>{{ row.label }}</td>
                <td>{{ row.reviewer || '—' }}</td>
                <td>{{ row.manualResult }}</td>
                <td class="text-wrap" style="max-width: 480px">{{ row.comment || row.contentPreview }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-card>

        <v-card variant="outlined" class="pa-4 mt-4">
          <div class="text-subtitle-1 font-weight-bold mb-3">图片级审核结果（图像检测类）</div>
          <v-table v-if="imageRows.length" density="comfortable">
            <thead>
              <tr>
                <th>图片编号</th>
                <th>机器结论</th>
                <th>人工结论</th>
                <th>风险等级</th>
                <th>说明</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in imageRows" :key="row.imageId">
                <td>{{ row.imageId }}</td>
                <td>{{ row.aiResult }}</td>
                <td>{{ row.manualResult }}</td>
                <td>{{ row.riskLevel }}</td>
                <td>{{ row.note }}</td>
              </tr>
            </tbody>
          </v-table>
          <div v-else class="text-body-2 text-medium-emphasis">非图像类任务或无逐图汇总。</div>
        </v-card>
      </template>

      <v-card variant="outlined" class="pa-4 mt-4">
        <div class="text-subtitle-1 font-weight-bold mb-3">报告下载</div>
        <p class="text-body-2 text-medium-emphasis mb-3">
          自动检测报告在 AI 完成后即可下载；人工审核报告在管理端通过且专家提交后生成。
        </p>
        <div class="d-flex flex-wrap ga-3">
          <v-btn
            color="secondary"
            variant="tonal"
            prepend-icon="mdi-file-download-outline"
            class="text-none"
            :loading="downloadingDetectionReport"
            :disabled="!taskId || taskId === '-'"
            @click="downloadDetectionReport"
          >
            下载 AI 检测报告
          </v-btn>
          <v-btn
            color="secondary"
            variant="outlined"
            prepend-icon="mdi-file-document-check-outline"
            class="text-none"
            :loading="downloadingManualReport"
            :disabled="!canDownloadManualReport"
            @click="downloadManualReviewReport"
          >
            下载人工审核报告
          </v-btn>
        </div>
      </v-card>

      <div class="d-flex flex-wrap ga-3 mt-4">
        <v-btn color="primary" variant="tonal" class="text-none" @click="goAnnual">返回人工审核申请列表</v-btn>
        <v-btn color="primary" variant="outlined" class="text-none" @click="goBack">返回检测历史</v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPublisherManualReviewSummary } from '@/api/manualReviewWorkflow'
import publisher from '@/api/publisher'
import { useSnackbarStore } from '@/stores/snackbar'
import { savePdfFromAxiosResponse } from '@/utils/downloadPdf'

const route = useRoute()
const router = useRouter()
const snackbar = useSnackbarStore()

const taskId = computed(() => String(route.query.task_id || route.query.detail_id || '-'))
const reviewRequestId = computed(() => String(route.query.review_request_id || '').trim())

type SummaryPayload = {
  summary?: {
    reviewerCount: number
    suspiciousImageCount: number
    finalDecision: string
  }
  reviewerRows?: Array<{ reviewer: string; decision: string; confidence: number; comment: string }>
  imageRows?: Array<{ imageId: string; aiResult: string; manualResult: string; riskLevel: string; note: string }>
  segmentRows?: Array<{
    segmentId: string
    label: string
    reviewer?: string
    manualResult: string
    comment?: string
    contentPreview?: string
  }>
  manual_review_status?: string
  admin_state?: string
  admin_reject_reason?: string
  request_reason?: string
}

const loading = ref(true)
const loadError = ref('')
const summaryPayload = ref<SummaryPayload | null>(null)

const reviewerRows = computed(() => summaryPayload.value?.reviewerRows ?? [])
const imageRows = computed(() => summaryPayload.value?.imageRows ?? [])
const segmentRows = computed(() => summaryPayload.value?.segmentRows ?? [])

const statusChipLabel = computed(() => {
  const p = summaryPayload.value
  if (!p) return ''
  if (p.admin_state === 'refused') return '管理端已拒绝'
  if (p.manual_review_status === 'completed') return '审核已完成'
  return '审核进行中'
})

const statusChipColor = computed(() => {
  const p = summaryPayload.value
  if (!p) return 'grey'
  if (p.admin_state === 'refused') return 'error'
  if (p.manual_review_status === 'completed') return 'success'
  return 'warning'
})

const canDownloadManualReport = computed(() => {
  const p = summaryPayload.value
  if (!p || !reviewRequestId.value) return false
  if (p.admin_state === 'refused') return false
  return p.admin_state === 'accepted'
})

const downloadingDetectionReport = ref(false)
const downloadingManualReport = ref(false)

async function downloadDetectionReport() {
  const tid = taskId.value
  if (!tid || tid === '-') return
  downloadingDetectionReport.value = true
  try {
    const res = await publisher.downloadReport(tid)
    savePdfFromAxiosResponse(res, `task_${tid}_report.pdf`)
    snackbar.showMessage('AI 检测报告已下载', 'success')
  } catch {
    snackbar.showMessage('AI 检测报告下载失败', 'error')
  } finally {
    downloadingDetectionReport.value = false
  }
}

async function downloadManualReviewReport() {
  const rid = reviewRequestId.value
  if (!rid || !canDownloadManualReport.value) return
  downloadingManualReport.value = true
  try {
    const res = await publisher.downloadReviewReport({ review_request_id: Number(rid) })
    savePdfFromAxiosResponse(res, `manual_review_${rid}_report.pdf`)
    snackbar.showMessage('人工审核报告已下载', 'success')
  } catch {
    snackbar.showMessage('人工审核报告下载失败', 'error')
  } finally {
    downloadingManualReport.value = false
  }
}

async function load() {
  loading.value = true
  loadError.value = ''
  summaryPayload.value = null
  const rid = reviewRequestId.value
  if (!rid || !/^\d+$/.test(rid)) {
    loadError.value = '缺少有效的 review_request_id 查询参数'
    loading.value = false
    return
  }
  try {
    const res = await getPublisherManualReviewSummary(Number(rid))
    summaryPayload.value = res.data as SummaryPayload
  } catch (e: unknown) {
    const ax = e as { response?: { status?: number; data?: { error?: string } } }
    if (ax.response?.status === 403) {
      loadError.value = '仅发布者（编辑）可查看人工审核结果，请切换账号后重试。'
    } else {
      loadError.value =
        typeof ax.response?.data?.error === 'string'
          ? ax.response.data.error
          : '无法拉取人工审核汇总，请确认后端已启动且专家已提交。'
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
})

function goAnnual() {
  router.push('/annual')
}

function goBack() {
  router.push({
    path: '/history',
    query: {
      detail_id: String(route.query.detail_id || route.query.task_id || ''),
      task_type: String(route.query.task_type || 'image_detection'),
      status: String(route.query.status || 'completed'),
      progress: String(route.query.progress || '100'),
      source: 'manual-review-result',
    },
  })
}
</script>
