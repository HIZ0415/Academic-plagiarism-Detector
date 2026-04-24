<template>
  <v-card flat>
    <v-card-title class="d-flex align-center">
      <div>
        <div class="text-h5 font-weight-bold">人工审核结果</div>
        <div class="text-body-2 text-medium-emphasis">任务 ID：{{ taskId }}</div>
      </div>
      <v-spacer />
      <v-chip color="success" variant="tonal">已完成</v-chip>
    </v-card-title>

    <v-card-text>
      <v-row>
        <v-col cols="12" md="4">
          <v-card variant="outlined" class="pa-4">
            <div class="text-caption text-medium-emphasis">审核员数量</div>
            <div class="text-h6 font-weight-bold">{{ summary.reviewerCount }}</div>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card variant="outlined" class="pa-4">
            <div class="text-caption text-medium-emphasis">疑似问题图片</div>
            <div class="text-h6 font-weight-bold">{{ summary.suspiciousImageCount }}</div>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card variant="outlined" class="pa-4">
            <div class="text-caption text-medium-emphasis">最终结论</div>
            <div class="text-h6 font-weight-bold">{{ summary.finalDecision }}</div>
          </v-card>
        </v-col>
      </v-row>

      <v-card variant="outlined" class="pa-4 mt-4">
        <div class="text-subtitle-1 font-weight-bold mb-3">审核员意见汇总</div>
        <v-table density="comfortable">
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
      </v-card>

      <v-card variant="outlined" class="pa-4 mt-4">
        <div class="text-subtitle-1 font-weight-bold mb-3">图片级审核结果</div>
        <v-table density="comfortable">
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
      </v-card>

      <div class="d-flex ga-3 mt-4">
        <v-btn color="primary" variant="outlined" @click="goBack">返回检测详情</v-btn>
        <v-btn color="primary" @click="goHistory">返回历史列表</v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const taskId = computed(() => String(route.query.task_id || route.query.detail_id || '-'))

const summary = {
  reviewerCount: 3,
  suspiciousImageCount: 2,
  finalDecision: '建议人工复核后判定为高风险',
}

const reviewerRows = [
  { reviewer: '审核员A', decision: '高风险', confidence: 86, comment: '纹理连续性异常，边缘区域存在拼接痕迹。' },
  { reviewer: '审核员B', decision: '中高风险', confidence: 79, comment: '多处区域与上下文光照不一致。' },
  { reviewer: '审核员C', decision: '高风险', confidence: 83, comment: '结合元数据与局部掩码，疑似后期编辑。' },
]

const imageRows = [
  { imageId: 'IMG-01', aiResult: '疑似造假', manualResult: '高风险', riskLevel: '高', note: '主体边缘存在不自然过渡。' },
  { imageId: 'IMG-02', aiResult: '正常', manualResult: '低风险', riskLevel: '低', note: '未发现明显异常。' },
  { imageId: 'IMG-03', aiResult: '疑似造假', manualResult: '中风险', riskLevel: '中', note: '局部噪声模式与背景不一致。' },
]

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
