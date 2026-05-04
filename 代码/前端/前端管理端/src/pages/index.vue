<template>
  <v-container class="admin-home">
    <v-row class="mb-2">
      <v-col cols="12">
        <div class="text-h4 font-weight-bold">工作台</div>
        <p class="text-body-2 text-medium-emphasis mb-0 mt-2">
          首页汇总近期任务与活跃度；侧栏按「工作台 → 检测与资源 → 用户与组织 → 协作审核 → 审计」进入各模块。
        </p>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <v-card variant="tonal" color="primary" class="mb-4">
          <v-card-title class="text-subtitle-1">当前身份</v-card-title>
          <v-card-text class="text-body-2">
            <strong>{{ roleLabel }}</strong>：{{ roleHint }}
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <div class="text-overline text-medium-emphasis mb-2 mt-2">快捷入口</div>
    <v-row>
      <v-col cols="12" sm="6" md="4">
        <v-card border class="h-100" hover to="/tasks">
          <v-card-title class="d-flex align-center text-subtitle-1">
            <v-icon class="me-2" color="teal">mdi-clipboard-text-outline</v-icon>
            检测与资源
          </v-card-title>
          <v-card-subtitle>从检测任务或资源文件进入，两页顶部可互相切换。</v-card-subtitle>
          <v-card-actions>
            <v-btn color="primary" variant="tonal" to="/tasks" prepend-icon="mdi-arrow-right">进入</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="4">
        <v-card border class="h-100" hover to="/members">
          <v-card-title class="d-flex align-center text-subtitle-1">
            <v-icon class="me-2" color="indigo">mdi-account-group-outline</v-icon>
            用户与组织
          </v-card-title>
          <v-card-subtitle>用户账号与平台组织或本组织档案在同一页内用标签切换。</v-card-subtitle>
          <v-card-actions>
            <v-btn color="primary" variant="tonal" to="/members" prepend-icon="mdi-arrow-right">进入</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="4">
        <v-card border class="h-100" hover to="/logs">
          <v-card-title class="d-flex align-center text-subtitle-1">
            <v-icon class="me-2" color="brown">mdi-clipboard-text-clock</v-icon>
            操作与审计日志
          </v-card-title>
          <v-card-subtitle>关键操作留痕、检索与导出。</v-card-subtitle>
          <v-card-actions>
            <v-btn color="primary" variant="tonal" to="/logs" prepend-icon="mdi-arrow-right">进入</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      <v-col v-if="userStore.admin_type === 'organization_admin'" cols="12" sm="6" md="4">
        <v-card border class="h-100" hover to="/reviews">
          <v-card-title class="d-flex align-center text-subtitle-1">
            <v-icon class="me-2" color="deep-purple">mdi-gavel</v-icon>
            人工审核申请
          </v-card-title>
          <v-card-subtitle>审批用户端发起的复核申请，通过后进入专家任务池。</v-card-subtitle>
          <v-card-actions>
            <v-btn color="primary" variant="tonal" to="/reviews" prepend-icon="mdi-arrow-right">进入</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      <v-col v-else cols="12" sm="6" md="4">
        <v-card variant="tonal" class="h-100">
          <v-card-title class="text-subtitle-1">人工审核审批</v-card-title>
          <v-card-text class="text-body-2 text-medium-emphasis">
            软件管理员不审批单组织内申请；请使用组织管理员账号从侧栏进入。
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-6 mb-2">
      <v-col cols="12">
        <div class="text-h5 font-weight-bold">数据看板</div>
        <p class="text-body-2 text-medium-emphasis mb-0 mt-1">
          近 30 日任务汇总、标签分布、活跃度与趋势；图表按管理员类型切换组织或发布者维度。
        </p>
      </v-col>
    </v-row>

    <div class="analytics-section">
      <DashboardSummaryCards v-if="dashboardStats" :stats="dashboardStats" />
      <v-row>
        <v-col cols="12" md="6">
          <ImageTagStats />
        </v-col>
        <v-col cols="12" md="6">
          <PublisherRanking v-if="isOrganizationAdmin" />
          <OrgRanking v-else />
        </v-col>
      </v-row>
      <v-row class="mt-4">
        <v-col cols="12">
          <TaskTrend />
        </v-col>
      </v-row>
      <v-row class="mt-4">
        <v-col cols="12">
          <ActiveUserTrend v-if="isOrganizationAdmin" />
          <ActiveOrgTrend v-else />
        </v-col>
      </v-row>
    </div>
  </v-container>
</template>

<script lang="ts" setup>
import { computed, ref, onMounted } from 'vue'
import ImageTagStats from '@/components/analytics/ImageTagStats.vue'
import PublisherRanking from '@/components/analytics/PublisherRanking.vue'
import OrgRanking from '@/components/analytics/OrgRanking.vue'
import TaskTrend from '@/components/analytics/TaskTrend.vue'
import ActiveUserTrend from '@/components/analytics/ActiveUserTrend.vue'
import ActiveOrgTrend from '@/components/analytics/ActiveOrgTrend.vue'
import DashboardSummaryCards from '@/components/analytics/DashboardSummaryCards.vue'
import userApi from '@/api/user'
import analyticsApi from '@/api/analytics'
import type { AdminDashboardTaskStats } from '@/types/core'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const isOrganizationAdmin = ref(false)
const dashboardStats = ref<AdminDashboardTaskStats | null>(null)

const roleLabel = computed(() => {
  if (userStore.admin_type === 'software_admin') return '软件管理员'
  if (userStore.admin_type === 'organization_admin') return '组织管理员'
  return '管理员'
})

const roleHint = computed(() => {
  if (userStore.admin_type === 'software_admin') {
    return '侧重跨组织治理：组织列表、平台级统计；不直接承担单组织内人工审核申请审批（由组织管理员承担）。'
  }
  if (userStore.admin_type === 'organization_admin') {
    return '侧重本组织：成员与用户、检测任务与资源、人工审核申请审批、本组织档案与日志。'
  }
  return '请从左侧导航进入各模块。'
})

onMounted(async () => {
  try {
    const res = await userApi.getUserInfo()
    isOrganizationAdmin.value = res.data.admin_type === 'organization_admin'
  } catch (error) {
    console.error('获取用户信息失败:', error)
  }
  try {
    const dash = await analyticsApi.getAdminDashboard()
    dashboardStats.value = dash.data.task_stats ?? null
  } catch (error) {
    console.error('加载仪表盘摘要失败:', error)
  }
})
</script>

<style scoped>
.admin-home :deep(.v-card-subtitle) {
  white-space: normal;
  line-height: 1.45;
}

.analytics-section {
  max-width: 1400px;
  margin: 0 auto;
}

@media (max-width: 600px) {
  .analytics-section {
    padding-left: 0;
    padding-right: 0;
  }
}
</style>
