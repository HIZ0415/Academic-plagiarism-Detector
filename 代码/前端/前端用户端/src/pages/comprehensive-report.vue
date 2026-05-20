<template>
  <v-container class="py-4">
    <div class="d-flex align-center flex-wrap ga-2 mb-4">
      <v-btn icon="mdi-arrow-left" variant="text" @click="router.back()" />
      <div>
        <h1 class="text-h4 font-weight-bold mb-0">综合鉴伪报告</h1>
        <p class="text-body-2 text-medium-emphasis mb-0">
          任务 <code>{{ taskId }}</code> · AI 占比、可疑位置、分模态结论与使用建议
        </p>
      </div>
      <v-spacer />
      <v-btn
        v-if="ready"
        color="primary"
        variant="tonal"
        prepend-icon="mdi-download"
        class="text-none"
        @click="downloadComprehensivePdf"
      >
        下载综合鉴伪 PDF
      </v-btn>
      <v-btn
        v-if="ready"
        variant="outlined"
        prepend-icon="mdi-file-code-outline"
        class="text-none"
        @click="downloadHtmlSnapshot"
      >
        导出 HTML
      </v-btn>
    </div>

    <v-alert v-if="loadError" type="error" variant="tonal">{{ loadError }}</v-alert>
    <v-progress-linear v-else-if="loading" indeterminate color="primary" class="mb-4" />

    <template v-else-if="!ready">
      <v-alert type="warning" variant="tonal">{{ notReadyMessage }}</v-alert>
    </template>

    <template v-else-if="sections">
      <v-row class="mb-4">
        <v-col cols="12" md="4">
          <v-card variant="outlined" class="pa-4">
            <div class="text-caption text-medium-emphasis">综合风险</div>
            <div class="text-h5 font-weight-bold">{{ conclusion.risk_level || '—' }}</div>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card variant="outlined" class="pa-4">
            <div class="text-caption text-medium-emphasis">AI 贡献占比（等价指标）</div>
            <div class="text-h5 font-weight-bold">
              {{ aiRatioPercent }}
            </div>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card variant="outlined" class="pa-4">
            <div class="text-caption text-medium-emphasis">检测模式</div>
            <div class="text-h6">{{ sections.models_used?.mode === 'precise' ? '精准模式' : '标准模式' }}</div>
          </v-card>
        </v-col>
      </v-row>

      <v-card variant="outlined" class="pa-4 mb-4">
        <div class="text-subtitle-1 font-weight-bold mb-2">综合结论</div>
        <p class="text-body-1">{{ conclusion.headline || '—' }}</p>
        <v-list v-if="sections.usage_advice?.length" density="compact" class="mt-2">
          <v-list-item v-for="(tip, i) in sections.usage_advice" :key="i" prepend-icon="mdi-lightbulb-outline">
            {{ tip }}
          </v-list-item>
        </v-list>
      </v-card>

      <v-expansion-panels v-if="sections.image" variant="accordion" class="mb-4">
        <v-expansion-panel title="图像 · 可疑区域">
          <v-expansion-panel-text>
            <p class="text-body-2 mb-3">{{ sections.image.summary }}</p>
            <v-row>
              <v-col v-for="(r, idx) in sections.image.suspicious_regions" :key="idx" cols="12" md="6">
                <v-card variant="tonal">
                  <v-img v-if="r.image_url" :src="mediaUrl(r.image_url)" max-height="200" />
                  <v-card-text class="text-caption">
                    图 {{ r.image_id }} · 置信度 {{ r.confidence_score }} · {{ r.masks?.length || 0 }} 处标注
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <v-expansion-panels v-if="sections.paper" variant="accordion" class="mb-4">
        <v-expansion-panel title="论文 AIGC / 资源规范性">
          <v-expansion-panel-text>
            <p class="text-body-2">{{ sections.paper.summary }}</p>
            <v-list v-if="sections.paper.factual_conclusions?.length" density="compact" class="mt-3">
              <v-list-subheader>事实性鉴伪子结论</v-list-subheader>
              <v-list-item v-for="fc in sections.paper.factual_conclusions" :key="fc.id || fc.title">
                <v-list-item-title>{{ fc.title }}</v-list-item-title>
                <v-list-item-subtitle class="text-wrap">
                  <div v-for="(r, i) in fc.reasons" :key="i">{{ r }}</div>
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
            <v-table v-if="sections.paper.paragraphs?.length" density="compact" class="mt-3">
              <thead>
                <tr><th>段落</th><th>风险</th><th>摘录</th></tr>
              </thead>
              <tbody>
                <tr v-for="p in sections.paper.paragraphs" :key="p.index">
                  <td>P{{ p.index }}</td>
                  <td>{{ p.risk_level }} ({{ p.risk_score }})</td>
                  <td class="text-truncate" style="max-width: 320px">{{ p.excerpt }}</td>
                </tr>
              </tbody>
            </v-table>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <v-expansion-panels v-if="sections.review" variant="accordion" class="mb-4">
        <v-expansion-panel title="Review 检测">
          <v-expansion-panel-text>
            <p class="text-body-2">{{ sections.review.summary }}</p>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <v-card v-if="sections.manual_review" variant="tonal" color="secondary" class="pa-4">
        <div class="text-subtitle-2 font-weight-bold">人工审核关联</div>
        <p class="text-body-2 mb-0">
          申请单 #{{ sections.manual_review.review_request_id }} · 状态 {{ sections.manual_review.status }}
        </p>
        <v-btn
          class="mt-2 text-none"
          size="small"
          variant="elevated"
          :to="{
            path: '/manual-review-result',
            query: { review_request_id: String(sections.manual_review.review_request_id), task_id: taskId },
          }"
        >
          查看人工审核汇总
        </v-btn>
      </v-card>
    </template>
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import platform from '@/api/platform'
import { useSnackbarStore } from '@/stores/snackbar'
import { savePdfFromAxiosResponse } from '@/utils/downloadPdf'
import { API_BASE_URL } from '@/api/request'

const route = useRoute()
const router = useRouter()
const snackbar = useSnackbarStore()

const taskId = computed(() => String(route.query.task_id || route.params.task_id || ''))
const loading = ref(true)
const loadError = ref('')
const ready = ref(false)
const notReadyMessage = ref('')
const sections = ref<any>(null)

const conclusion = computed(() => sections.value?.conclusion || {})
const aiRatioPercent = computed(() => {
  const r = conclusion.value.ai_contribution_ratio
  if (r == null) return '—'
  const n = Number(r)
  return n <= 1 ? `${(n * 100).toFixed(1)}%` : `${n}%`
})

function mediaUrl(path: string) {
  if (!path) return ''
  if (path.startsWith('http')) return path
  const base = API_BASE_URL.replace(/\/api$/, '')
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

async function load() {
  if (!taskId.value) {
    loadError.value = '缺少 task_id'
    loading.value = false
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    const res = await platform.getComprehensiveReport(taskId.value)
    ready.value = !!res.data.ready
    sections.value = res.data.sections
    notReadyMessage.value = res.data.message || '报告尚未就绪'
  } catch (e: any) {
    loadError.value = e?.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
}

async function downloadComprehensivePdf() {
  try {
    const res = await platform.downloadComprehensiveReport(taskId.value)
    savePdfFromAxiosResponse(res, `comprehensive_task_${taskId.value}.pdf`)
    snackbar.showMessage('综合鉴伪 PDF 已下载', 'success')
  } catch {
    snackbar.showMessage('综合鉴伪 PDF 下载失败', 'error')
  }
}

function downloadHtmlSnapshot() {
  if (!sections.value) return
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>综合鉴伪报告 ${taskId.value}</title></head><body><pre>${JSON.stringify(sections.value, null, 2)}</pre></body></html>`
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `comprehensive_task_${taskId.value}.html`
  a.click()
  URL.revokeObjectURL(a.href)
  snackbar.showMessage('已导出 HTML 快照', 'success')
}

onMounted(load)
</script>
