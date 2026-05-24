<template>

  <v-card class="mb-6 chart-card ranking-card" elevation="2">

    <v-card-title class="text-h5 font-weight-bold primary--text py-4">

      <v-icon large color="primary" class="mr-2">mdi-account-group</v-icon>

      本组织成员排行

    </v-card-title>

    <v-card-subtitle class="px-4 pb-2">

      近 30 日按总任务量排序，汇总图像（已检/造假）、论文 AIGC、资源规范性、Review 及综合高风险占比。

    </v-card-subtitle>

    <v-card-text class="pa-4">

        <v-table class="publisher-table" density="compact">

          <thead>

            <tr>

              <th class="text-left col-rank">排名</th>

              <th class="text-left col-name">用户名</th>

              <th class="text-right col-num">总任务</th>

              <th class="text-right col-num">图像(已检/造假)</th>

              <th class="text-right col-num">论文</th>

              <th class="text-right col-num">资源</th>

              <th class="text-right col-num">Review</th>

              <th class="text-right col-num">综合风险</th>

            </tr>

          </thead>

          <tbody>

            <tr v-for="(publisher, index) in publishers" :key="publisher.username">

              <td>{{ index + 1 }}</td>

              <td>{{ publisher.username }}</td>

              <td class="text-right">{{ publisher.total_tasks }}</td>

              <td class="text-right">{{ formatImageStats(publisher) }}</td>

              <td class="text-right">{{ publisher.paper_aigc }}</td>

              <td class="text-right">{{ publisher.resource_check }}</td>

              <td class="text-right">{{ publisher.review_detection }}</td>

              <td class="text-right">

                <v-chip :color="getRiskRatioColor(publisher.high_risk_ratio)" text-color="white" size="small">

                  {{ formatRiskSummary(publisher) }}

                </v-chip>

              </td>

            </tr>

          </tbody>

        </v-table>

    </v-card-text>

  </v-card>

</template>



<script setup lang="ts">

import { ref, onMounted } from 'vue'

import analyticsApi from '@/api/analytics'

import type { PublisherRankingRow } from '@/types/core'



const publishers = ref<PublisherRankingRow[]>([])



const formatRiskRatioPercent = (ratio: number): string => {

  const pct = ratio <= 1 ? ratio * 100 : ratio

  return `${pct.toFixed(1)}%`

}



const formatImageStats = (row: PublisherRankingRow): string => {

  const checked = row.total_images ?? 0

  const fake = row.fake_count ?? 0

  if (!checked && !row.image_detection) return '—'

  return `${checked}/${fake}`

}



const formatRiskSummary = (row: PublisherRankingRow): string => {

  const pct = formatRiskRatioPercent(row.high_risk_ratio ?? 0)

  const n = row.high_risk_count ?? 0

  return n > 0 ? `${pct} (${n})` : pct

}



const getRiskRatioColor = (ratio: number): string => {

  const normalized = ratio <= 1 ? ratio : ratio / 100

  if (normalized >= 0.5) return 'error'

  if (normalized >= 0.3) return 'warning'

  if (normalized >= 0.1) return 'info'

  return 'success'

}



const fetchPublishersData = async () => {

  try {

    const res = await analyticsApi.getTopPublishers()

    if (res.data && Array.isArray(res.data)) {

      publishers.value = res.data as PublisherRankingRow[]

    }

  } catch (error) {

    console.error('获取排行榜数据失败:', error)

  }

}



onMounted(() => {

  fetchPublishersData()

})

</script>



<style scoped>

.chart-card {

  border-radius: 12px;

  transition: all 0.3s ease;

  height: 100%;

  display: flex;

  flex-direction: column;

}



.chart-card:hover {

  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);

}



.ranking-card {

  overflow: hidden;

}



.ranking-card {

  overflow: hidden;

}



.ranking-card :deep(.v-card-text) {

  min-width: 0;

}



.publisher-table :deep(.v-table__wrapper) {

  overflow-x: auto;

  overflow-y: hidden;

}



.publisher-table :deep(table) {

  width: 100%;

  min-width: 720px;

}



.publisher-table th {

  white-space: nowrap;

}



.publisher-table .col-rank {

  width: 56px;

}



.publisher-table .col-name {

  min-width: 100px;

}



.publisher-table .col-num {

  min-width: 72px;

}



</style>

