<template>
  <v-card flat>
    <v-card-title class="d-flex align-center flex-wrap ga-2">
      <div>
        <div class="text-h5 font-weight-bold">人工审核结果</div>
        <div class="text-body-2 text-medium-emphasis">
          检测任务：<code>{{ taskId }}</code>
          <template v-if="reviewRequestId"> · 申请单：<code>{{ reviewRequestId }}</code></template>
        </div>
      </div>
      <v-spacer />
      <v-chip v-if="loadError" color="error" variant="tonal">加载失败</v-chip>
      <v-chip v-else-if="loading" color="info" variant="tonal">加载中…</v-chip>
      <v-chip v-else-if="summaryPayload" color="success" variant="tonal">已加载</v-chip>
    </v-card-title>

    <v-card-text>
      <v-alert v-if="loadError" type="error" variant="tonal" class="mb-4">
        {{ loadError }}。请确认后端已实现 <code>GET /manual-review-requests/&lt;id&gt;/publisher-summary/</code> 或开启 Mock 全流程并完成专家提交。
      </v-alert>

      <v-alert v-else-if="!loading && summaryPayload?.manual_review_status !== 'completed'" type="warning" variant="tonal" class="mb-4">
        专家尚未完成审核或申请仍停留在管理端，此处仅在流程结束后展示汇总（当前：
        {{ summaryPayload?.manual_review_status || '未知' }}）。
      </v-alert>

      <template v-if="summaryPayload?.summary">
        <v-row>
          <v-col cols="12" md="4">
            <v-card variant="outlined" class="pa-4">
              <div class="text-caption text-medium-emphasis">审核员数量</div>
              <div class="text-h6 font-weight-bold">{{ summaryPayload.summary.reviewerCount }}</div>
            </v-card>
          </v-col>
          <v-col cols="12" md="4">
            <v-card variant="outlined" class="pa-4">
              <div class="text-caption text-medium-emphasis">疑似问题图片（图像类）</div>
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
          <div class="text-subtitle-1 font-weight-bold mb-3">审核员意见汇总</div>
          <v-table v-if="reviewerRows.length" density="comfortable">
            <thead>
              <tr>
                <th>审核员</th>
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
                <td>{{ item.comment }}</td>
              </tr>
            </tbody>
          </v-table>
          <div v-else class="text-body-2 text-medium-emphasis">暂无汇总行（后端可扩展多专家）。</div>
        </v-card>

        <v-card variant="outlined" class="pa-4 mt-4">
          <div class="text-subtitle-1 font-weight-bold mb-3">图片级审核结果（如有）</div>
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

      <div class="d-flex ga-3 mt-4">
        <v-btn color="primary" variant="outlined" @click="goBack">返回检测详情</v-btn>
        <v-btn color="primary" @click="goHistory">返回历史列表</v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPublisherManualReviewSummary } from '@/api/manualReviewWorkflow'

const route = useRoute()
const router = useRouter()

const taskId = computed(() => String(route.query.task_id || route.query.detail_id || '-'))
const reviewRequestId = computed(() => String(route.query.review_request_id || '').trim())

const loading = ref(true)
const loadError = ref('')
const summaryPayload = ref<{
  summary?: {
    reviewerCount: number
    suspiciousImageCount: number
    finalDecision: string
  }
  reviewerRows?: Array<{ reviewer: string; decision: string; confidence: number; comment: string }>
  imageRows?: Array<{ imageId: string; aiResult: string; manualResult: string; riskLevel: string; note: string }>
  manual_review_status?: string
} | null>(null)

const reviewerRows = computed(() => summaryPayload.value?.reviewerRows ?? [])
const imageRows = computed(() => summaryPayload.value?.imageRows ?? [])

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
    summaryPayload.value = res.data as typeof summaryPayload.value
  } catch {
    loadError.value = '无法拉取人工审核汇总'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
})

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

function goHistory() {
  router.push('/history')
}
</script>
