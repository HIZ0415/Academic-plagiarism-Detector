<template>
  <v-container class="py-4">
    <h1 class="text-h4 font-weight-bold mb-2">多模态联合分析</h1>
    <p class="text-body-2 text-medium-emphasis mb-4">
      对同一<strong>统一检测批次</strong>内的图像、论文与 Review 子任务进行融合分析，输出综合可信度与跨模态一致性提示（FR-NRJC-0003/0004）。
    </p>

    <v-card variant="outlined" class="pa-4 mb-4">
      <v-text-field
        v-model="batchId"
        label="批次 ID（batch_session_id）"
        hint="在「统一学术检测」完成一批后，可从检测历史批次列复制"
        persistent-hint
        class="mb-3"
      />
      <v-btn color="primary" :loading="loading" prepend-icon="mdi-chart-timeline-variant" @click="analyze">
        开始融合分析
      </v-btn>
    </v-card>

    <template v-if="result">
      <v-row class="mb-4">
        <v-col cols="12" md="4">
          <v-card variant="tonal" color="primary" class="pa-4">
            <div class="text-caption">融合可信度</div>
            <div class="text-h4 font-weight-bold">{{ (result.fusion_score * 100).toFixed(1) }}%</div>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card variant="outlined" class="pa-4">
            <div class="text-caption">综合风险等级</div>
            <div class="text-h5">{{ riskLabel(result.overall_risk) }}</div>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card variant="outlined" class="pa-4">
            <div class="text-caption">子任务数</div>
            <div class="text-h5">{{ result.task_count }}</div>
          </v-card>
        </v-col>
      </v-row>

      <v-card variant="outlined" class="pa-4 mb-4">
        <div class="text-subtitle-1 font-weight-bold mb-2">跨模态一致性说明</div>
        <v-list density="compact">
          <v-list-item v-for="(n, i) in result.cross_modal_notes" :key="i" prepend-icon="mdi-link-variant">
            {{ n }}
          </v-list-item>
        </v-list>
        <p class="text-body-2 mt-3 text-medium-emphasis">{{ result.recommendation }}</p>
      </v-card>

      <v-card variant="outlined">
        <v-card-title class="text-subtitle-1">子任务分项</v-card-title>
        <v-data-table :headers="headers" :items="result.tasks" density="comfortable" />
      </v-card>
    </template>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import platform from '@/api/platform'
import { useSnackbarStore } from '@/stores/snackbar'

const route = useRoute()
const snackbar = useSnackbarStore()
const batchId = ref(String(route.query.batch_session_id || ''))
const loading = ref(false)
const result = ref<any>(null)

const headers = [
  { title: '任务 ID', key: 'task_id' },
  { title: '类型', key: 'task_type' },
  { title: '名称', key: 'task_name' },
  { title: '风险', key: 'risk' },
  { title: '得分', key: 'score' },
]

function riskLabel(r: string) {
  return { high: '高', medium: '中', low: '低' }[r] || r
}

async function analyze() {
  const id = batchId.value.trim()
  if (!id) {
    snackbar.showMessage('请填写批次 ID', 'warning')
    return
  }
  loading.value = true
  try {
    const res = await platform.getBatchFusion({ batch_session_id: id })
    result.value = res.data
  } catch (e: any) {
    snackbar.showMessage(e?.response?.data?.error || '分析失败（请确认批次内任务均已完成）', 'error')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (batchId.value) analyze()
})
</script>
