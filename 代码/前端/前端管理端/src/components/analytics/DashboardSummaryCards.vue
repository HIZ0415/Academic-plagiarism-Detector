<template>
  <v-row class="mb-2">
    <v-col cols="12" sm="6" md="4" lg="2">
      <v-card variant="tonal" color="primary">
        <v-card-text>
          <div class="text-caption text-medium-emphasis">近 30 日任务总数</div>
          <div class="text-h5 font-weight-bold">{{ stats?.total_tasks ?? '—' }}</div>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col cols="12" sm="6" md="4" lg="2">
      <v-card variant="tonal" color="success">
        <v-card-text>
          <div class="text-caption text-medium-emphasis">已完成</div>
          <div class="text-h5 font-weight-bold">{{ stats?.completed_tasks ?? '—' }}</div>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col cols="12" sm="6" md="4" lg="2">
      <v-card variant="tonal" color="warning">
        <v-card-text>
          <div class="text-caption text-medium-emphasis">进行中</div>
          <div class="text-h5 font-weight-bold">{{ stats?.in_progress_tasks ?? '—' }}</div>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col cols="12" sm="6" md="4" lg="2">
      <v-card variant="tonal" color="secondary">
        <v-card-text>
          <div class="text-caption text-medium-emphasis">待处理</div>
          <div class="text-h5 font-weight-bold">{{ stats?.pending_tasks ?? '—' }}</div>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col cols="12" sm="6" md="4" lg="2">
      <v-card variant="tonal" color="error">
        <v-card-text>
          <div class="text-caption text-medium-emphasis">失败</div>
          <div class="text-h5 font-weight-bold">{{ stats?.failed_tasks ?? '—' }}</div>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import type { AdminDashboardTaskStats } from '@/types/core'

defineProps<{
  stats: AdminDashboardTaskStats | null
}>()
</script>
