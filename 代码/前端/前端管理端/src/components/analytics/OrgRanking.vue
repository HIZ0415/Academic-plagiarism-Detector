<template>
  <v-card class="mb-6 chart-card scrollable-card" elevation="2">
    <v-card-title class="text-h5 font-weight-bold primary--text py-4">
      <v-icon large color="primary" class="mr-2">mdi-office-building</v-icon>
      组织排行榜
    </v-card-title>
    <v-card-subtitle class="px-4 pb-2">全平台组织按任务量排序，统计各组织图像检测造假情况。</v-card-subtitle>
    <v-card-text class="pa-4">
      <v-table class="org-table">
        <thead>
          <tr>
            <th class="text-left col-rank">排名</th>
            <th class="text-left col-name">组织名称</th>
            <th class="text-right col-num">总任务数</th>
            <th class="text-right col-num">已检图片数</th>
            <th class="text-right col-num">造假数量</th>
            <th class="text-right col-num">造假比例</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(org, index) in organizations" :key="org.organization_name">
            <td>{{ index + 1 }}</td>
            <td>{{ org.organization_name }}</td>
            <td class="text-right">{{ org.total_tasks }}</td>
            <td class="text-right">{{ org.total_images }}</td>
            <td class="text-right">{{ org.fake_count }}</td>
            <td class="text-right">
              <v-chip :color="getFakeRatioColor(org.fake_ratio)" text-color="white" size="small">
                {{ formatFakeRatioPercent(org.fake_ratio) }}
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

interface RankingRow {
  organization_name: string
  total_tasks: number
  total_images: number
  fake_count: number
  fake_ratio: number
}

const organizations = ref<RankingRow[]>([])

const formatFakeRatioPercent = (ratio: number): string => {
  const pct = ratio <= 1 ? ratio * 100 : ratio
  return `${pct.toFixed(1)}%`
}

const getFakeRatioColor = (ratio: number): string => {
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
      organizations.value = res.data
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

.scrollable-card {
  overflow-y: auto;
  max-height: 600px;
}

.scrollable-card::-webkit-scrollbar {
  width: 6px;
}

.scrollable-card::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.scrollable-card::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 3px;
}

.scrollable-card::-webkit-scrollbar-thumb:hover {
  background: #555;
}

.org-table {
  width: 100%;
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
  min-width: 88px;
}

@media (max-width: 600px) {
  .scrollable-card {
    max-height: 400px;
  }
}
</style>
