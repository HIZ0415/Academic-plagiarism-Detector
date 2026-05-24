<template>

  <v-card class="mb-6 chart-card ranking-card" elevation="2">

    <v-card-title class="text-h5 font-weight-bold primary--text py-4">

      <v-icon large color="primary" class="mr-2">mdi-office-building</v-icon>

      组织排行榜

    </v-card-title>

    <v-card-subtitle class="px-4 pb-2">

      近 30 日全平台组织按总任务量排序，汇总各检测类型任务数与综合高风险占比。

    </v-card-subtitle>

    <v-card-text class="pa-4">

        <v-table class="org-table" density="compact">

          <thead>

            <tr>

              <th class="text-left col-rank">排名</th>

              <th class="text-left col-name">组织名称</th>

              <th class="text-right col-num">总任务</th>

              <th class="text-right col-num">图像</th>

              <th class="text-right col-num">论文 AIGC</th>

              <th class="text-right col-num">资源规范</th>

              <th class="text-right col-num">Review</th>

              <th class="text-right col-num">已完成</th>

              <th class="text-right col-num">高风险</th>

              <th class="text-right col-num">高风险占比</th>

            </tr>

          </thead>

          <tbody>

            <tr v-for="(org, index) in organizations" :key="org.organization_name">

              <td>{{ index + 1 }}</td>

              <td>{{ org.organization_name }}</td>

              <td class="text-right">{{ org.total_tasks }}</td>

              <td class="text-right">{{ org.image_detection }}</td>

              <td class="text-right">{{ org.paper_aigc }}</td>

              <td class="text-right">{{ org.resource_check }}</td>

              <td class="text-right">{{ org.review_detection }}</td>

              <td class="text-right">{{ org.completed_tasks ?? '—' }}</td>

              <td class="text-right">{{ org.high_risk_count }}</td>

              <td class="text-right">

                <v-chip :color="getRiskRatioColor(org.high_risk_ratio)" text-color="white" size="small">

                  {{ formatRiskRatioPercent(org.high_risk_ratio) }}

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



interface OrgRankingRow {

  organization_name: string

  total_tasks: number

  completed_tasks?: number

  image_detection: number

  paper_aigc: number

  resource_check: number

  review_detection: number

  high_risk_count: number

  high_risk_ratio: number

}



const organizations = ref<OrgRankingRow[]>([])



const formatRiskRatioPercent = (ratio: number): string => {

  const pct = ratio <= 1 ? ratio * 100 : ratio

  return `${pct.toFixed(1)}%`

}



const getRiskRatioColor = (ratio: number): string => {

  const normalized = ratio <= 1 ? ratio : ratio / 100

  if (normalized >= 0.5) return 'error'

  if (normalized >= 0.3) return 'warning'

  if (normalized >= 0.1) return 'info'

  return 'success'

}



const fetchOrganizationsData = async () => {

  try {

    const res = await analyticsApi.getTopOrganizations()

    if (res.data && Array.isArray(res.data)) {

      organizations.value = res.data as OrgRankingRow[]

    }

  } catch (error) {

    console.error('获取组织排行榜数据失败:', error)

  }

}



onMounted(() => {

  fetchOrganizationsData()

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



.org-table :deep(.v-table__wrapper) {

  overflow-x: auto;

  overflow-y: hidden;

}



.org-table :deep(table) {

  width: 100%;

  min-width: 720px;

}



.org-table th {

  white-space: nowrap;

}



.org-table .col-rank {

  width: 56px;

}



.org-table .col-name {

  min-width: 120px;

}



.org-table .col-num {

  min-width: 72px;

}



</style>

