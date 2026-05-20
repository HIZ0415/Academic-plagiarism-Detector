<template>
  <v-container>
    <v-row class="mb-4">
      <v-col>
        <h1 class="text-h4 font-weight-bold">{{ title }}</h1>
        <p class="text-body-2 text-medium-emphasis mb-0 mt-2">{{ subtitle }}</p>
      </v-col>
      <v-col cols="auto">
        <v-btn color="primary" prepend-icon="mdi-refresh" class="text-none" :loading="loading" @click="load">刷新</v-btn>
      </v-col>
    </v-row>

    <v-row class="mb-4">
      <v-col cols="12" sm="4">
        <v-select
          v-model="filterStatus"
          :items="statusItems"
          label="任务状态"
          clearable
          hide-details
          density="compact"
          variant="outlined"
          @update:model-value="load"
        />
      </v-col>
    </v-row>

    <v-card>
      <v-data-table :headers="headers" :items="logs" :loading="loading" hide-default-footer density="comfortable">
        <template #item.task_status="{ item }">
          <v-chip size="small" :color="statusColor(item.task_status)">{{ item.task_status }}</v-chip>
        </template>
        <template #item.error_message="{ item }">
          <span class="text-caption text-error">{{ item.error_message || '—' }}</span>
        </template>
      </v-data-table>
      <div class="d-flex justify-center pa-4">
        <v-pagination v-model="page" :length="totalPages" @update:model-value="load" />
      </div>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import platform from '@/api/platform'
import { useSnackbarStore } from '@/stores/snackbar'

const props = defineProps<{
  logScope: 'paper' | 'review' | 'image'
  title: string
  subtitle: string
}>()

const snackbar = useSnackbarStore()
const logs = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const totalPages = ref(1)
const filterStatus = ref<string | null>(null)

const headers = [
  { title: '时间', key: 'operation_time' },
  { title: '用户', key: 'user' },
  { title: '任务 ID', key: 'task_id' },
  { title: '任务名', key: 'task_name' },
  { title: '类型', key: 'task_type' },
  { title: '状态', key: 'task_status' },
  { title: '失败原因', key: 'error_message' },
]

const statusItems = [
  { title: '排队', value: 'pending' },
  { title: '进行中', value: 'in_progress' },
  { title: '已完成', value: 'completed' },
  { title: '失败', value: 'failed' },
]

function statusColor(s: string) {
  if (s === 'completed') return 'success'
  if (s === 'failed') return 'error'
  if (s === 'in_progress') return 'info'
  return 'warning'
}

async function load() {
  loading.value = true
  try {
    const res = await platform.getDetectionLogs({
      log_scope: props.logScope,
      page: page.value,
      page_size: 15,
      status: filterStatus.value || undefined,
    })
    logs.value = res.data.logs || []
    totalPages.value = res.data.total_pages || 1
  } catch {
    snackbar.showMessage('加载日志失败', 'error')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
